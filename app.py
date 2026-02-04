from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import sys
import os
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

# 导入核心功能
from core.register import CpolarRegister
from core.login import CpolarLogin
from database.manager import Database

app = Flask(__name__)

# 配置数据库路径（当前文件夹下）
DB_PATH = os.path.join(os.path.dirname(__file__), "cpolar_accounts.db")

def register_single_task(index, invite_code):
    """执行单个注册任务"""
    try:
        register = CpolarRegister()
        login = CpolarLogin()

        # 1. 注册
        account_info, error = register.register(invite_code)
        
        if account_info:
            # 2. 登录获取推广码
            promo_code, promo_error = login.login_and_get_promo(
                account_info['email'],
                account_info['password']
            )

            if promo_code:
                account_info['promo_code'] = promo_code
            
            # 不保存到数据库，直接返回成功
            return {
                "status": "success",
                "index": index + 1,
                "email": account_info['email'],
                "password": account_info['password'],
                "promo_code": account_info.get('promo_code', '获取失败'),
                "message": "注册成功"
            }
        else:
            return {
                "status": "error",
                "index": index + 1,
                "message": f"注册失败: {error}"
            }
    except Exception as e:
        return {
            "status": "error",
            "index": index + 1,
            "message": f"异常: {str(e)}"
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/batch_register', methods=['POST'])
def batch_register():
    data = request.json
    invite_code = data.get('invite_code', '')
    count = int(data.get('count', 1))
    max_workers = int(data.get('threads', 3))

    if not invite_code:
        return jsonify({"error": "请输入邀请码"}), 400

    def generate():
        yield 'data: ' + json.dumps({"type": "info", "message": f"开始批量注册，目标数量: {count}, 并发数: {max_workers}"}) + '\n\n'
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(register_single_task, i, invite_code) for i in range(count)]
            
            completed = 0
            success_count = 0
            for future in futures:
                result = future.result()
                completed += 1
                if result['status'] == 'success':
                    success_count += 1
                
                yield 'data: ' + json.dumps({
                    "type": "progress", 
                    "completed": completed, 
                    "total": count,
                    "success": success_count,
                    "last_result": result
                }) + '\n\n'
        
        yield 'data: ' + json.dumps({"type": "finished", "total": count, "success": success_count}) + '\n\n'

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    # 确保数据库文件所在目录存在
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
