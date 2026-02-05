import sqlite3
import os
import traceback
from datetime import datetime
from database.logger import ErrorLogger


class Database:
    def __init__(self, db_path="cpolar_accounts.db"):
        self.db_path = db_path
        self.error_logger = ErrorLogger()
        self.init_database()

    def init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT NOT NULL,
                    password TEXT NOT NULL,
                    invite_code TEXT NOT NULL,
                    promo_code TEXT,
                    plan_name TEXT,
                    plan_start_time TEXT,
                    plan_end_time TEXT,
                    promotion_count INTEGER DEFAULT 0,
                    purchased_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # 卡密表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cdkeys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    is_used INTEGER DEFAULT 0,
                    used_at TEXT,
                    used_by_ip TEXT,
                    created_at TEXT NOT NULL
                )
            ''')

            cursor.execute("PRAGMA table_info(accounts)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'promo_code' not in columns:
                cursor.execute('ALTER TABLE accounts ADD COLUMN promo_code TEXT')
            if 'plan_name' not in columns:
                cursor.execute('ALTER TABLE accounts ADD COLUMN plan_name TEXT')
            if 'plan_start_time' not in columns:
                cursor.execute('ALTER TABLE accounts ADD COLUMN plan_start_time TEXT')
            if 'plan_end_time' not in columns:
                cursor.execute('ALTER TABLE accounts ADD COLUMN plan_end_time TEXT')
            if 'promotion_count' not in columns:
                cursor.execute('ALTER TABLE accounts ADD COLUMN promotion_count INTEGER DEFAULT 0')
            if 'purchased_count' not in columns:
                cursor.execute('ALTER TABLE accounts ADD COLUMN purchased_count INTEGER DEFAULT 0')

            conn.commit()
            conn.close()
        except Exception as e:
            error_msg = f"数据库初始化失败: {str(e)}"
            self.error_logger.log_error(
                error_type="DatabaseInitError",
                error_message=error_msg,
                module_name=__name__,
                function_name="init_database",
                error_traceback=traceback.format_exc()
            )

    def add_account(self, account_info):
        """添加账号到数据库"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO accounts (name, email, phone, password, invite_code, promo_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                account_info['name'],
                account_info['email'],
                account_info['phone'],
                account_info['password'],
                account_info['invite_code'],
                account_info.get('promo_code', None),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()
            return True, None
        except sqlite3.IntegrityError as e:
            error_msg = "邮箱已存在"
            self.error_logger.log_error(
                error_type="DuplicateEmail",
                error_message=error_msg,
                module_name=__name__,
                function_name="add_account"
            )
            return False, error_msg
        except Exception as e:
            error_msg = f"添加账号失败: {str(e)}"
            self.error_logger.log_error(
                error_type="AddAccountError",
                error_message=error_msg,
                module_name=__name__,
                function_name="add_account",
                error_traceback=traceback.format_exc()
            )
            return False, error_msg
        finally:
            conn.close()

    def get_all_accounts(self):
        """获取所有账号"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, email, phone, password, invite_code, promo_code,
                   plan_name, plan_start_time, plan_end_time, promotion_count, purchased_count, created_at
            FROM accounts
            ORDER BY created_at ASC
        ''')

        accounts = cursor.fetchall()
        conn.close()
        return accounts

    def search_accounts(self, keyword):
        """搜索账号（按邮箱、手机号或邀请码）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, email, phone, password, invite_code, promo_code,
                   plan_name, plan_start_time, plan_end_time, promotion_count, purchased_count, created_at
            FROM accounts
            WHERE email LIKE ? OR phone LIKE ? OR invite_code LIKE ? OR name LIKE ? OR promo_code LIKE ?
            ORDER BY created_at ASC
        ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))

        accounts = cursor.fetchall()
        conn.close()
        return accounts

    def delete_account(self, account_id):
        """删除账号"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_statistics(self):
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM accounts')
        total = cursor.fetchone()[0]

        # 按邀请码统计
        cursor.execute('SELECT invite_code, COUNT(*) FROM accounts GROUP BY invite_code')
        invite_stats = cursor.fetchall()

        conn.close()
        return {
            'total': total,
            'invite_stats': invite_stats
        }

    def update_promo_code(self, account_id, promo_code):
        """更新账号的推广码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE accounts SET promo_code = ? WHERE id = ?
            ''', (promo_code, account_id))
            conn.commit()
            return True, None
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def get_account_by_id(self, account_id):
        """根据ID获取账号信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, email, phone, password, invite_code, promo_code,
                   plan_name, plan_start_time, plan_end_time, promotion_count, purchased_count, created_at
            FROM accounts
            WHERE id = ?
        ''', (account_id,))

        account = cursor.fetchone()
        conn.close()
        return account

    def update_account_info(self, account_id, plan_name=None, plan_start_time=None,
                           plan_end_time=None, promotion_count=None, purchased_count=None):
        """更新账号的套餐和推广信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            update_fields = []
            params = []

            if plan_name is not None:
                update_fields.append("plan_name = ?")
                params.append(plan_name)
            if plan_start_time is not None:
                update_fields.append("plan_start_time = ?")
                params.append(plan_start_time)
            if plan_end_time is not None:
                update_fields.append("plan_end_time = ?")
                params.append(plan_end_time)
            if promotion_count is not None:
                update_fields.append("promotion_count = ?")
                params.append(promotion_count)
            if purchased_count is not None:
                update_fields.append("purchased_count = ?")
                params.append(purchased_count)

            if update_fields:
                params.append(account_id)
                sql = f"UPDATE accounts SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(sql, params)
                conn.commit()
                return True, None
            else:
                return False, "没有需要更新的字段"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    # ========== 卡密管理功能 ==========
    
    def generate_cdkeys(self, count=1, length=16):
        """批量生成卡密"""
        import secrets
        import string
        
        generated = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for _ in range(count):
                # 生成随机卡密 (大写字母+数字)
                chars = string.ascii_uppercase + string.digits
                code = ''.join(secrets.choice(chars) for _ in range(length))
                
                try:
                    cursor.execute('''
                        INSERT INTO cdkeys (code, created_at)
                        VALUES (?, ?)
                    ''', (code, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    generated.append(code)
                except sqlite3.IntegrityError:
                    # 如果卡密重复，跳过
                    continue
            
            conn.commit()
            return generated
        except Exception as e:
            self.error_logger.log_error(
                error_type="GenerateCdkeyError",
                error_message=str(e),
                module_name=__name__,
                function_name="generate_cdkeys",
                error_traceback=traceback.format_exc()
            )
            return []
        finally:
            conn.close()
    
    def get_all_cdkeys(self):
        """获取所有卡密"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, code, is_used, used_at, used_by_ip, created_at
            FROM cdkeys
            ORDER BY created_at DESC
        ''')
        
        cdkeys = cursor.fetchall()
        conn.close()
        return cdkeys
    
    def validate_cdkey(self, code):
        """验证卡密是否有效（存在且未使用）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, code, is_used FROM cdkeys WHERE code = ?
        ''', (code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False, "卡密不存在"
        if result[2] == 1:
            return False, "卡密已被使用"
        return True, "卡密有效"
    
    def use_cdkey(self, code, ip_address=None):
        """使用卡密（标记为已使用）"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE cdkeys 
                SET is_used = 1, used_at = ?, used_by_ip = ?
                WHERE code = ? AND is_used = 0
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip_address, code))
            
            conn.commit()
            success = cursor.rowcount > 0
            return success
        except Exception as e:
            return False
        finally:
            conn.close()
    
    def delete_cdkey(self, cdkey_id):
        """删除卡密"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM cdkeys WHERE id = ?', (cdkey_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def get_cdkey_stats(self):
        """获取卡密统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM cdkeys')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cdkeys WHERE is_used = 1')
        used = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cdkeys WHERE is_used = 0')
        unused = cursor.fetchone()[0]
        
        conn.close()
        return {
            'total': total,
            'used': used,
            'unused': unused
        }

    def cleanup_used_cdkeys(self):
        """清理所有已使用的卡密"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM cdkeys WHERE is_used = 1')
            conn.commit()
            count = cursor.rowcount
            return count
        except Exception:
            return 0
        finally:
            conn.close()
