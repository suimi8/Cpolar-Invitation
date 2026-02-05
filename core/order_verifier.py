
import requests
import json
import time
import os
import base64
from datetime import datetime

class OrderVerifier:
    def __init__(self, db_path):
        self.base_url = "https://ed.weeeg.com/adminapi"
        # 优先从环境变量获取，如果没有则使用默认留空的配置（需要用户自己配）
        self.account = os.environ.get("YUDIAN_ACCOUNT")
        self.password = os.environ.get("YUDIAN_PASSWORD")
        self.db_path = db_path
        # 代理获取API
        self.proxy_api = "http://bapi.51daili.com/getapi2?linePoolIndex=-1&packid=2&time=2&qty=1&port=1&format=txt&ct=1&usertype=17&uid=35391&accessName=suimi&accessPassword=4e384629a0857cf252120a0cef284190&skey=autoaddwhiteip"
        self.proxies = None
        
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
        }
        
    def _refresh_proxy(self):
        """刷新代理IP"""
        try:
            print("正在从51daili获取新代理IP...")
            # 获取代理本身不用代理
            resp = requests.get(self.proxy_api, timeout=10)
            if resp.status_code == 200:
                proxy_str = resp.text.strip()
                # 简单校验格式 (xxx.xxx.xxx.xxx:xxxx)
                if '.' in proxy_str and ':' in proxy_str and 'div' not in proxy_str:
                    self.proxies = {
                        "http": f"http://{proxy_str}",
                        "https": f"http://{proxy_str}"
                    }
                    print(f"代理IP已更新: {proxy_str}")
                    return True
                else:
                    print(f"代理API返回格式异常: {proxy_str}")
            else:
                print(f"获取代理失败, 状态码: {resp.status_code}")
        except Exception as e:
            print(f"获取代理IP出错: {e}")
        return False

    def _read_token(self):
        """从本地文件读取Token"""
        token_file = os.path.join(os.path.dirname(self.db_path), 'yudian_token.json')
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    data = json.load(f)
                    # 检查是否过期
                    if data.get('expires_time', 0) > time.time():
                        return data.get('token')
            except:
                pass
        return None

    def _save_token(self, token_data):
        """保存Token到本地"""
        token_file = os.path.join(os.path.dirname(self.db_path), 'yudian_token.json')
        try:
            with open(token_file, 'w') as f:
                json.dump(token_data, f)
        except Exception as e:
            print(f"保存Token失败: {e}")

    def _get_captcha(self):
        """获取验证码"""
        # 如果当前没有代理，先获取一个
        if not self.proxies:
            self._refresh_proxy()
            
        try:
            t = int(time.time() * 1000)
            url = f"{self.base_url}/captcha_custom"
            params = {
                "t": t,
                "instanceId": "17702568836005t089xdq8",
                "pageTransition": t
            }
            
            # 使用代理请求
            resp = requests.get(url, params=params, headers=self.headers, timeout=10, proxies=self.proxies)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"获取验证码请求失败 (尝试刷新代理): {e}")
            # 失败后尝试刷新代理重试一次
            if self._refresh_proxy():
                try:
                    resp = requests.get(url, params=params, headers=self.headers, timeout=10, proxies=self.proxies)
                    if resp.status_code == 200:
                        return resp.json()
                except Exception as retry_e:
                    print(f"重试获取验证码失败: {retry_e}")
                    
        return None

    def _solve_captcha(self, captcha_data):
        """识别验证码 - 使用 jfbym 接口"""
        try:
            img_base64_str = captcha_data.get('image', '')
            if img_base64_str.startswith('data:image'):
                img_base64_str = img_base64_str.split(',')[1]
                
            url = "http://api.jfbym.com/api/YmServer/customApi"
            # 这里的Token是打码平台的token，不是易店的
            token = os.environ.get("JFBYM_TOKEN", "uY4IggQrYvMpObnzBSN2R7cVk1dKCThoRemlmJUA7eY")
            
            data = {
                "token": token,
                "type": "10110",
                "image": img_base64_str,
            }
            _headers = {
                "Content-Type": "application/json"
            }
            # 打码平台一般直连即可，不需要走代理，且为了稳定建议不走
            resp = requests.post(url, headers=_headers, json=data, timeout=15)
            response = resp.json()
            print(f"打码平台响应: {response}")
            
            if str(response.get('code')) == '10000':
                verify_code = response.get('data', {}).get('data')
                return verify_code
            else:
                 print(f"打码失败: {response.get('msg')}")
                 return None
                 
        except Exception as e:
            print(f"验证码识别出错: {e}")
            return None

    def login(self):
        """模拟登录获取Token"""
        if not self.account or not self.password:
            # 尝试使用环境变量配置
            self.account = os.environ.get("YUDIAN_ACCOUNT")
            self.password = os.environ.get("YUDIAN_PASSWORD")
            
            if not self.account or not self.password:
                 print("未配置易店账号密码，无法自动登录")
                 return None

        # 1. 获取验证码参数
        captcha_info = self._get_captcha()
        if not captcha_info:
            print("获取验证码失败")
            return None
        
        # 2. 识别验证码 - 现在使用打码平台
        captcha_code = self._solve_captcha(captcha_info)
        if not captcha_code:
            print("验证码识别失败")
            return None

        login_url = f"{self.base_url}/yudian"
        payload = {
            "account": self.account,
            "pwd": self.password,
            "key": "6983f9f373f8b",
            "captchaType": "blockPuzzle",
            "captcha": captcha_code,
            "captchaKey": captcha_info.get("key")
        }
        
        try:
            # 登录也需要走代理
            resp = requests.post(login_url, json=payload, headers=self.headers, timeout=15, proxies=self.proxies)
            data = resp.json()
            
            if data.get('status') == 200:
                token_data = data.get('data', {})
                # 获取Token
                token = token_data.get('token')
                if token:
                    # 保存到本地文件，下次复用
                    self._save_token({
                        'token': token,
                        'expires_time': token_data.get('expires_time', time.time() + 3600)
                    })
                    return token
            else:
                print(f"登录失败: {data.get('msg')}")
        except Exception as e:
            print(f"登录请求异常: {e}")
            
        return None

    def check_order(self, order_id):
        """
        检查订单状态
        返回: (bool 是否通过, str 消息, dict 订单详情)
        """
        token = self._read_token()
        # 如果没有本地 Token，尝试从环境变量读取
        if not token:
             token = os.environ.get("YUDIAN_TOKEN")
        
        # 如果还是没有，尝试自动登录获取
        if not token:
            print("无可用Token，尝试自动登录...")
            token = self.login()
             
        if not token:
            return False, "系统未配置第三方授权Token且自动登录失败", None

        search_url = f"{self.base_url}/home/xianyu_list"
        
        # 确保有代理
        if not self.proxies:
            self._refresh_proxy()
        
        def do_request(curr_token):
            headers = self.headers.copy()
            headers["authori-zation"] = f"Bearer {curr_token}"
            headers["cookie"] = f"token={curr_token}" 
            
            params = {
                "page": 1,
                "limit": 10,
                "real_name": order_id, 
                "field_key": "all"
            }
            # 查询订单也需要走代理
            try:
                return requests.get(search_url, params=params, headers=headers, timeout=15, proxies=self.proxies)
            except Exception as req_e:
                print(f"查询请求异常 (尝试刷新代理): {req_e}")
                self._refresh_proxy()
                return requests.get(search_url, params=params, headers=headers, timeout=15, proxies=self.proxies)

        try:
            resp = do_request(token)
            data = resp.json()
            
            # 如果 Token 失效 (假设 status 401 或特定 msg)，尝试重新登录
            if resp.status_code == 401 or data.get('status') in [401, 4001, -1] or "token" in str(data.get('msg', '')).lower():
                print("Token可能已失效，尝试重新登录刷新...")
                new_token = self.login()
                if new_token:
                    resp = do_request(new_token)
                    data = resp.json()
                else:
                    return False, "自动刷新授权失败，请联系管理员", None

            if data.get('status') != 200:
                 return False, f"查询失败: {data.get('msg')}", None
                 
            lists = data.get('data', {}).get('lists', [])
            if not lists:
                return False, "未找到该订单", None
            
            # 找到匹配的订单
            target_order = None
            for order in lists:
                if str(order.get('order_id')) == str(order_id): 
                    target_order = order
                    break
            
            if not target_order:
                return False, "订单号不匹配", None

            # 检查状态
            # 10：交易完成，2：待收货
            status = str(target_order.get('order_status'))
            if status not in ['2', '10']:
                return False, f"订单状态不满足要求 (当前状态: {status})，请确认已发货或已完成", None
                
            # 检查是否已使用
            if self._is_order_used(order_id):
                return False, "该订单已使用过，无法再次使用", None
                
            return True, "验证通过", target_order

        except Exception as e:
            return False, f"验证过程出错: {str(e)}", None

    def _is_order_used(self, order_id):
        """检查订单是否在本地数据库中已存在"""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 确保表存在
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS used_orders (
                    order_id TEXT PRIMARY KEY,
                    used_at TEXT,
                    client_ip TEXT
                )
            ''')
            cursor.execute("SELECT 1 FROM used_orders WHERE order_id = ?", (str(order_id),))
            exists = cursor.fetchone()
            conn.close()
            return exists is not None
        except Exception:
            return False

    def mark_order_used(self, order_id, client_ip=""):
        """标记订单为已使用"""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO used_orders (order_id, used_at, client_ip)
                VALUES (?, ?, ?)
            ''', (str(order_id), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_ip))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"标记订单使用失败: {e}")
