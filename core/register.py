import requests
import re
import traceback
from urllib.parse import quote
from database.logger import ErrorLogger
from utils.generators import (generate_random_name, generate_random_email, 
                               generate_random_phone, generate_random_password)


class CpolarRegister:
    def __init__(self):
        self.session = requests.Session()
        self.error_logger = ErrorLogger()
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9",
            "priority": "u=0, i",
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
        }

    def get_csrf_token(self, invite_code):
        """获取CSRF Token"""
        url = f"https://dashboard.cpolar.com/signup?channel=0&inviteCode={invite_code}"
        
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            pattern = r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"'
            match = re.search(pattern, response.text)
            
            if match:
                csrf_token = match.group(1)
                return csrf_token, None
            else:
                error_msg = "未找到CSRF Token"
                self.error_logger.log_error(
                    error_type="CSRFTokenNotFound",
                    error_message=error_msg,
                    module_name=__name__,
                    function_name="get_csrf_token"
                )
                return None, error_msg
        except Exception as e:
            error_msg = f"获取CSRF Token出错: {str(e)}"
            self.error_logger.log_error(
                error_type="UnexpectedError",
                error_message=error_msg,
                module_name=__name__,
                function_name="get_csrf_token",
                error_traceback=traceback.format_exc()
            )
            return None, error_msg

    def register(self, invite_code):
        """执行注册"""
        self.session = requests.Session()
        
        csrf_token, error = self.get_csrf_token(invite_code)
        if error:
            return None, error

        name = generate_random_name()
        email = generate_random_email()
        phone = generate_random_phone()
        password = generate_random_password()

        register_url = "https://dashboard.cpolar.com/signup"
        post_headers = self.headers.copy()
        post_headers.update({
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "sec-fetch-site": "same-origin",
            "Referer": "https://dashboard.cpolar.com/signup"
        })

        post_data = f"name={name}&email={quote(email)}&phone={phone}&password={quote(password)}&inviteNumber=&csrf_token={quote(csrf_token)}&agreeTerms=1"

        try:
            response = self.session.post(
                register_url,
                headers=post_headers,
                data=post_data,
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code in [200, 302, 301]:
                response_text_lower = response.text.lower()
                email_lower = email.lower()
                
                if (email_lower in response_text_lower or 
                    "dashboard" in response_text_lower or 
                    "登录" in response_text_lower or
                    "login" in response_text_lower or
                    response.url != register_url):
                    account_info = {
                        'name': name,
                        'email': email,
                        'phone': phone,
                        'password': password,
                        'invite_code': invite_code
                    }
                    return account_info, None
            
            error_patterns = [
                r'<div[^>]*class="[^"]*error[^"]*"[^>]*>([^<]+)</div>',
                r'<span[^>]*class="[^"]*error[^"]*"[^>]*>([^<]+)</span>',
                r'错误[：:]\s*([^<\n]+)',
            ]
            
            error_msg = "注册失败，未知原因"
            for pattern in error_patterns:
                error_match = re.search(pattern, response.text, re.IGNORECASE)
                if error_match:
                    error_msg = error_match.group(1).strip()
                    break
            
            self.error_logger.log_error(
                error_type="RegistrationFailed",
                error_message=error_msg,
                module_name=__name__,
                function_name="register"
            )
            return None, error_msg
                
        except Exception as e:
            error_msg = f"注册请求失败: {str(e)}"
            self.error_logger.log_error(
                error_type="RegistrationException",
                error_message=error_msg,
                module_name=__name__,
                function_name="register",
                error_traceback=traceback.format_exc()
            )
            return None, error_msg
