
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, session, redirect, url_for
import sys
import os
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

print("=== Flask 应用初始化开始 ===")
print(f"=== 环境变量 PORT = {os.environ.get('PORT', '未设置')} ===")
print(f"=== 环境变量 WEB_PORT = {os.environ.get('WEB_PORT', '未设置')} ===")

# 导入核心功能
from core.register import CpolarRegister
from core.login import CpolarLogin
from database.manager import Database

print("=== 核心模块导入完成 ===")

app = Flask(__name__)

# 安全配置
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise ValueError("严重错误：未配置 SECRET_KEY 环境变量！")

SITE_PASSWORD = os.environ.get("SITE_PASSWORD")
if not SITE_PASSWORD:
    raise ValueError("严重错误：未配置 SITE_PASSWORD 环境变量！")

# 管理员密码（后台管理专用）：必须独立配置
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise ValueError("严重错误：未配置 ADMIN_PASSWORD 环境变量！请设置独立的后台管理密码。")

# 确保管理员密码和普通密码不同
if ADMIN_PASSWORD == SITE_PASSWORD:
    print("警告：建议将 ADMIN_PASSWORD 设置为与 SITE_PASSWORD 不同的密码，以提高安全性。", file=sys.stderr)
app.config['SESSION_COOKIE_HTTPONLY'] = True
# 在 Zeabur 等云环境中，HTTP 请求可能会经过反向代理，需要信任头
# 如果是生产环境 (FLASK_ENV=production 或类似变量)，可以设置为 Secure
app.config['SESSION_COOKIE_SECURE'] = False  # 兼容 HTTP 访问，若全站 HTTPS 可设为 True

# 配置数据库路径
# 优先使用环境变量 DATA_DIR (Zeabur 等平台常用挂载路径)，如果没有则默认为当前目录
DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(DATA_DIR, "cpolar_accounts.db")

print(f"=== Flask 应用配置完成, DB_PATH={DB_PATH} ===")

# 健康检查端点 - 用于 Zeabur 等平台验证服务是否存活
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Service is running"}), 200

@app.route('/ping')
def ping():
    return "pong", 200

print("=== 健康检查端点已注册 ===")



# 启动心跳日志线程，证明服务活着
def heartbeat_logger():
    while True:
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 服务运行正常 - Heartbeat - 内存/CPU状态良好", flush=True)
        time.sleep(10)

# 在非 Reload 模式下启动心跳 (简单防止 worker 重启导致多重打印，但在 Gunicorn worker 里每个 worker 都会启动一个)
import threading
try:
    threading.Thread(target=heartbeat_logger, daemon=True).start()
except Exception as e:
    print(f"心跳线程启动失败: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({"error": "未授权访问"}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限验证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            # 如果是普通用户尝试访问后台 API，返回 JSON 错误；页面访问则返回 403 文本
            if request.path.startswith('/api/'):
                return jsonify({"error": "无权访问: 需要管理员权限"}), 403
            return "无权访问: 需要管理员权限", 403
        return f(*args, **kwargs)
    return decorated_function

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
            
            # 保存到数据库
            try:
                db = Database(DB_PATH)
                db.add_account(account_info)
            except Exception as e:
                print(f"数据库保存失败: {e}")

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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        
        # 验证密码
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['is_admin'] = True  # 管理员权限
            return redirect(url_for('index'))
            
        elif password == SITE_PASSWORD:
            session['logged_in'] = True
            session['is_admin'] = False # 普通用户
            return redirect(url_for('index'))
            
        return render_template('login.html', error="密码错误，请重试")
        
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', is_admin=session.get('is_admin', False))

# ========== 卡密管理 (Admin Only) ==========

@app.route('/admin')
@admin_required
def admin_page():
    """后台管理页面"""
    return render_template('admin.html')

@app.route('/api/cdkeys', methods=['GET'])
@admin_required
def get_cdkeys():
    """获取所有卡密"""
    db = Database(DB_PATH)
    cdkeys = db.get_all_cdkeys()
    stats = db.get_cdkey_stats()
    
    return jsonify({
        "cdkeys": [
            {
                "id": row[0],
                "code": row[1],
                "is_used": bool(row[2]),
                "used_at": row[3],
                "used_by_ip": row[4],
                "created_at": row[5]
            }
            for row in cdkeys
        ],
        "stats": stats
    })

@app.route('/api/cdkeys/generate', methods=['POST'])
@admin_required
def generate_cdkeys():
    """生成卡密"""
    data = request.json or {}
    count = min(int(data.get('count', 1)), 100)  # 最多一次生成100个
    length = int(data.get('length', 16))
    
    db = Database(DB_PATH)
    generated = db.generate_cdkeys(count=count, length=length)
    
    return jsonify({
        "success": True,
        "generated": generated,
        "count": len(generated)
    })

@app.route('/api/cdkeys/<int:cdkey_id>', methods=['DELETE'])
@admin_required
def delete_cdkey(cdkey_id):
    """删除卡密"""
    db = Database(DB_PATH)
    deleted = db.delete_cdkey(cdkey_id)
    
    return jsonify({"success": deleted})

@app.route('/api/cdkeys/validate', methods=['POST'])
def validate_cdkey():
    """验证卡密（公开接口）"""
    data = request.json or {}
    code = data.get('code', '').strip().upper()
    
    if not code:
        return jsonify({"valid": False, "message": "请输入卡密"})
    
    db = Database(DB_PATH)
    valid, message = db.validate_cdkey(code)
    
    return jsonify({"valid": valid, "message": message})


@app.route('/api/batch_register', methods=['POST'])
@login_required
def batch_register():
    data = request.json
    invite_code = data.get('invite_code', '')
    cdkey = data.get('cdkey', '').strip().upper()
    
    # 强制内置参数
    count = 15
    max_workers = 3

    if not invite_code:
        return jsonify({"error": "请输入邀请码"}), 400
        
    if not cdkey:
        return jsonify({"error": "请输入验证卡密"}), 400

    # 验证并消耗卡密
    db = Database(DB_PATH)
    valid, msg = db.validate_cdkey(cdkey)
    if not valid:
        return jsonify({"error": msg}), 403
        
    # 标记卡密为已使用
    used = db.use_cdkey(cdkey, request.remote_addr)
    if not used:
        return jsonify({"error": "卡密使用失败或已被他人抢先使用"}), 403

    def generate():
        yield 'data: ' + json.dumps({"type": "info", "message": f"卡密验证成功！开始批量注册，目标数量: {count} (系统内置), 并发数: {max_workers}"}) + '\n\n'
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_index = {executor.submit(register_single_task, i, invite_code): i for i in range(count)}
            
            completed = 0
            success_count = 0
            
            # 使用 as_completed 实时获取完成的任务，避免阻塞
            for future in as_completed(future_to_index):
                try:
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
                except Exception as exc:
                    # 捕获任务产生的异常
                    index = future_to_index[future]
                    yield 'data: ' + json.dumps({
                        "type": "progress",
                        "completed": completed + 1,
                        "total": count,
                        "success": success_count,
                        "last_result": {
                            "status": "error",
                            "index": index + 1,
                            "message": f"任务执行出错: {str(exc)}"
                        }
                    }) + '\n\n'
        
        yield 'data: ' + json.dumps({"type": "finished", "total": count, "success": success_count}) + '\n\n'

    headers = {
        'X-Accel-Buffering': 'no',  # 告诉 Nginx 不要缓冲
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers=headers)

if __name__ == '__main__':
    # 确保数据库文件所在目录存在
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    port = int(os.environ.get("PORT", 8080))
    # 生产部署时，默认关闭 debug
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
