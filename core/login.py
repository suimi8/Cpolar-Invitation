import requests
import re
import traceback
from bs4 import BeautifulSoup
from database.logger import ErrorLogger


class CpolarLogin:
    """Cpolar登录和推广码获取"""

    def __init__(self):
        self.session = requests.Session()
        self.error_logger = ErrorLogger()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

    def get_csrf_token(self):
        """获取CSRF Token"""
        try:
            response = self.session.get("https://dashboard.cpolar.com/login", timeout=30)
            if response.status_code == 200:
                match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.text)
                if match:
                    return match.group(1)

                soup = BeautifulSoup(response.text, 'html.parser')
                csrf_input = soup.find('input', {'name': 'csrf_token'})
                if csrf_input and csrf_input.get('value'):
                    return csrf_input.get('value')
        except requests.exceptions.Timeout:
            error_msg = "获取CSRF Token超时"
            self.error_logger.log_error(
                error_type="CSRFTokenTimeout",
                error_message=error_msg,
                module_name=__name__,
                function_name="get_csrf_token",
                error_traceback=traceback.format_exc()
            )
        except Exception as e:
            error_msg = f"获取CSRF Token失败: {str(e)}"
            self.error_logger.log_error(
                error_type="CSRFTokenError",
                error_message=error_msg,
                module_name=__name__,
                function_name="get_csrf_token",
                error_traceback=traceback.format_exc()
            )
        return None

    def login(self, email, password):
        """
        登录账号
        返回: (是否成功, 错误信息/Cookie)
        """
        try:
            csrf_token = self.get_csrf_token()
            if not csrf_token:
                error_msg = "无法获取CSRF Token"
                self.error_logger.log_error(
                    error_type="LoginError",
                    error_message=error_msg,
                    module_name=__name__,
                    function_name="login"
                )
                return False, error_msg

            login_url = "https://dashboard.cpolar.com/login"
            data = {
                "login": email,
                "password": password,
                "csrf_token": csrf_token
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://dashboard.cpolar.com/login",
                "Origin": "https://dashboard.cpolar.com"
            }

            response = self.session.post(login_url, data=data, headers=headers, allow_redirects=True, timeout=30)

            if response.status_code == 200:
                if "login" not in response.url or "dashboard" in response.text:
                    return True, None
                else:
                    if "密码错误" in response.text or "账号不存在" in response.text:
                        error_msg = "账号或密码错误"
                    elif "验证码" in response.text:
                        error_msg = "需要验证码"
                    else:
                        error_msg = "登录失败,未知错误"
                    
                    self.error_logger.log_error(
                        error_type="LoginFailed",
                        error_message=error_msg,
                        module_name=__name__,
                        function_name="login"
                    )
                    return False, error_msg
            else:
                error_msg = f"登录请求失败: HTTP {response.status_code}"
                self.error_logger.log_error(
                    error_type="LoginHTTPError",
                    error_message=error_msg,
                    module_name=__name__,
                    function_name="login"
                )
                return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = "登录请求超时"
            self.error_logger.log_error(
                error_type="LoginTimeout",
                error_message=error_msg,
                module_name=__name__,
                function_name="login",
                error_traceback=traceback.format_exc()
            )
            return False, error_msg
        except requests.exceptions.ConnectionError:
            error_msg = "网络连接失败"
            self.error_logger.log_error(
                error_type="LoginConnectionError",
                error_message=error_msg,
                module_name=__name__,
                function_name="login",
                error_traceback=traceback.format_exc()
            )
            return False, error_msg
        except Exception as e:
            error_msg = f"登录异常: {str(e)}"
            self.error_logger.log_error(
                error_type="LoginException",
                error_message=error_msg,
                module_name=__name__,
                function_name="login",
                error_traceback=traceback.format_exc()
            )
            return False, error_msg

    def get_promotion_code(self):
        """
        获取推广码
        返回: (推广码, 错误信息)
        """
        try:
            # 访问推广页面
            response = self.session.get("https://dashboard.cpolar.com/envoy")

            if response.status_code == 200:
                # 使用正则表达式提取推广码
                pattern = r'推广链接[:：]\s*https?://i\.cpolar\.com/m/([A-Za-z0-9]+)'
                match = re.search(pattern, response.text)

                if match:
                    promo_code = match.group(1)
                    return promo_code, None

                # 如果没找到，尝试其他模式
                pattern2 = r'https?://i\.cpolar\.com/m/([A-Za-z0-9]+)'
                match2 = re.search(pattern2, response.text)
                if match2:
                    promo_code = match2.group(1)
                    return promo_code, None

                # 使用BeautifulSoup提取
                soup = BeautifulSoup(response.text, 'html.parser')
                link_p = soup.find('p', class_='link')
                if link_p:
                    link_text = link_p.get_text()
                    match3 = re.search(r'/m/([A-Za-z0-9]+)', link_text)
                    if match3:
                        return match3.group(1), None

                return None, "未找到推广码"
            else:
                return None, f"获取推广页面失败: HTTP {response.status_code}"

        except Exception as e:
            return None, f"获取推广码异常: {str(e)}"

    def get_plan_info(self):
        """
        获取套餐信息
        返回: (套餐信息字典, 错误信息)
        """
        try:
            response = self.session.get("https://dashboard.cpolar.com/billing")

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 查找套餐名称
                plan_name = None
                plan_match = re.search(r'<strong[^>]*>([^<]+)</strong>\s*套餐', response.text)
                if plan_match:
                    plan_name = plan_match.group(1).strip()

                # 查找套餐时间表格
                plan_start_time = None
                plan_end_time = None

                table = soup.find('table', class_='table')
                if table:
                    tbody = table.find('tbody')
                    if tbody:
                        tr = tbody.find('tr')
                        if tr:
                            tds = tr.find_all('td')
                            if len(tds) >= 2:
                                plan_start_time = tds[0].get_text(strip=True)
                                plan_end_time = tds[1].get_text(strip=True)

                if plan_name or plan_start_time or plan_end_time:
                    return {
                        'plan_name': plan_name,
                        'plan_start_time': plan_start_time,
                        'plan_end_time': plan_end_time
                    }, None
                else:
                    return None, "未找到套餐信息"
            else:
                return None, f"获取套餐页面失败: HTTP {response.status_code}"

        except Exception as e:
            return None, f"获取套餐信息异常: {str(e)}"

    def get_promotion_stats(self):
        """
        获取推广统计信息
        返回: (统计信息字典, 错误信息)
        """
        try:
            response = self.session.get("https://dashboard.cpolar.com/envoy")

            if response.status_code == 200:
                # 查找推广客户数
                promotion_count = 0
                promo_match = re.search(r'当前推广客户数.*?<span>(\d+)</span>', response.text, re.DOTALL)
                if promo_match:
                    promotion_count = int(promo_match.group(1))

                # 查找已购买人数
                purchased_count = 0
                purchased_match = re.search(r'当前已购买人数.*?<span>(\d+)</span>', response.text, re.DOTALL)
                if purchased_match:
                    purchased_count = int(purchased_match.group(1))

                return {
                    'promotion_count': promotion_count,
                    'purchased_count': purchased_count
                }, None
            else:
                return None, f"获取推广页面失败: HTTP {response.status_code}"

        except Exception as e:
            return None, f"获取推广统计异常: {str(e)}"

    def login_and_get_promo(self, email, password):
        """
        登录并获取推广码
        返回: (推广码, 错误信息)
        """
        # 登录
        success, error = self.login(email, password)
        if not success:
            return None, f"登录失败: {error}"

        # 获取推广码
        promo_code, error = self.get_promotion_code()
        if promo_code:
            return promo_code, None
        else:
            return None, f"获取推广码失败: {error}"

    def login_and_get_all_info(self, email, password):
        """
        登录并获取所有信息（推广码、套餐信息、推广统计）
        返回: (信息字典, 错误信息)
        """
        # 登录
        success, error = self.login(email, password)
        if not success:
            return None, f"登录失败: {error}"

        result = {}

        # 获取推广码
        promo_code, _ = self.get_promotion_code()
        if promo_code:
            result['promo_code'] = promo_code

        # 获取套餐信息
        plan_info, _ = self.get_plan_info()
        if plan_info:
            result.update(plan_info)

        # 获取推广统计
        promo_stats, _ = self.get_promotion_stats()
        if promo_stats:
            result.update(promo_stats)

        return result, None
