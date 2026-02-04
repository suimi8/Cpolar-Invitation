import random
import string

def generate_random_name(length=8):
    """生成随机字母名称（大小写混合）"""
    return ''.join(random.choices(string.ascii_letters, k=length))

def generate_random_email():
    """生成随机 Email"""
    username_length = random.randint(8, 15)
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))
    domains = ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com', '163.com', 'qq.com', '2925.com', 'temp-mail.org']
    domain = random.choice(domains)
    return f"{username}@{domain}"

def generate_random_phone():
    """生成中国随机手机号"""
    prefixes = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
               '150', '151', '152', '153', '155', '156', '157', '158', '159',
               '180', '181', '182', '183', '184', '185', '186', '187', '188', '189',
               '170', '171', '172', '173', '175', '176', '177', '178']
    prefix = random.choice(prefixes)
    suffix = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    return prefix + suffix

def generate_random_password(length=12):
    """生成强随机密码"""
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*()_+-=[]{}|;:,.<>?")
    ]
    password.extend(random.choices(all_chars, k=length-4))
    random.shuffle(password)
    return ''.join(password)
