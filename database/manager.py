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
            conn = sqlite3.connect(self.db_path)
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
        conn = sqlite3.connect(self.db_path)
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
