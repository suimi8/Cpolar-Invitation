import sqlite3
import os
import traceback
from datetime import datetime
from typing import List, Dict, Optional


class ErrorLogger:
    """错误日志管理器"""
    
    def __init__(self, db_path="cpolar_errors.db"):
        # 获取当前文件所在目录下级或者同级的数据库路径，确保在模块化后依然能找到
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化错误日志数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                error_traceback TEXT,
                module_name TEXT,
                function_name TEXT,
                timestamp TEXT NOT NULL,
                is_resolved INTEGER DEFAULT 0,
                resolution_notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_error(self, error_type: str, error_message: str, 
                  module_name: str = "Unknown", function_name: str = "Unknown",
                  error_traceback: str = None) -> int:
        """
        记录错误 (包含敏感信息脱敏)
        """
        import re
        
        # 脱敏处理：屏蔽常见的密码、卡密、邮箱格式
        def mask_sensitive(text):
            if not text: return text
            # 屏蔽密码字段的值 (如果 message 中包含 password=... 或 "password": "...")
            text = re.sub(r'([Pp]assword[\'"]?\s*[:=]\s*[\'"]?)[^\'",\s&]+([\'"]?)', r'\1********\2', text)
            # 屏蔽邮箱地址
            text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r'***@***.com', text)
            # 屏蔽看起来像卡密的 12-24 位大写字母数字组合
            text = re.sub(r'\b[A-Z0-9]{12,24}\b', r'CDKEY-*******', text)
            return text

        error_message = mask_sensitive(error_message)
        error_traceback = mask_sensitive(error_traceback)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO error_logs 
                (error_type, error_message, error_traceback, module_name, function_name, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (error_type, error_message, error_traceback, module_name, function_name, timestamp))
            
            conn.commit()
            error_id = cursor.lastrowid
            return error_id
        except Exception as e:
            print(f"保存错误日志失败: {str(e)}")
            return -1
        finally:
            conn.close()
    
    def get_error_logs(self, limit: int = 100, only_unresolved: bool = False) -> List[Dict]:
        """获取错误日志列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if only_unresolved:
                cursor.execute('''
                    SELECT id, error_type, error_message, module_name, function_name, timestamp, is_resolved
                    FROM error_logs
                    WHERE is_resolved = 0
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT id, error_type, error_message, module_name, function_name, timestamp, is_resolved
                    FROM error_logs
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            errors = []
            for row in rows:
                errors.append({
                    'id': row[0],
                    'error_type': row[1],
                    'error_message': row[2],
                    'module_name': row[3],
                    'function_name': row[4],
                    'timestamp': row[5],
                    'is_resolved': row[6] == 1
                })
            
            return errors
        finally:
            conn.close()
    
    def get_error_detail(self, error_id: int) -> Optional[Dict]:
        """获取错误详细信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, error_type, error_message, error_traceback, module_name, function_name, 
                       timestamp, is_resolved, resolution_notes
                FROM error_logs
                WHERE id = ?
            ''', (error_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'error_type': row[1],
                    'error_message': row[2],
                    'error_traceback': row[3],
                    'module_name': row[4],
                    'function_name': row[5],
                    'timestamp': row[6],
                    'is_resolved': row[7] == 1,
                    'resolution_notes': row[8]
                }
            return None
        finally:
            conn.close()
    
    def search_errors(self, keyword: str, limit: int = 100) -> List[Dict]:
        """搜索错误日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            search_pattern = f"%{keyword}%"
            cursor.execute('''
                SELECT id, error_type, error_message, module_name, function_name, timestamp, is_resolved
                FROM error_logs
                WHERE error_type LIKE ? OR error_message LIKE ? OR module_name LIKE ? OR function_name LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (search_pattern, search_pattern, search_pattern, search_pattern, limit))
            
            rows = cursor.fetchall()
            errors = []
            for row in rows:
                errors.append({
                    'id': row[0],
                    'error_type': row[1],
                    'error_message': row[2],
                    'module_name': row[3],
                    'function_name': row[4],
                    'timestamp': row[5],
                    'is_resolved': row[6] == 1
                })
            
            return errors
        finally:
            conn.close()
    
    def mark_as_resolved(self, error_id: int, notes: str = "") -> bool:
        """标记错误为已解决"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE error_logs
                SET is_resolved = 1, resolution_notes = ?
                WHERE id = ?
            ''', (notes, error_id))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_error(self, error_id: int) -> bool:
        """删除错误记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM error_logs WHERE id = ?', (error_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def clear_all_errors(self) -> bool:
        """清除所有错误记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM error_logs')
            conn.commit()
            return True
        except Exception as e:
            print(f"清除错误日志失败: {str(e)}")
            return False
        finally:
            conn.close()

    def clear_old_errors(self, days: int = 30) -> int:
        """清除指定天数以前的错误记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 计算截断日期
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            cursor.execute('DELETE FROM error_logs WHERE timestamp < ?', (cutoff_date,))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
    
    def get_error_statistics(self) -> Dict:
        """获取错误统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM error_logs')
            total = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM error_logs WHERE is_resolved = 0')
            unresolved = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT error_type, COUNT(*) as count
                FROM error_logs
                GROUP BY error_type
                ORDER BY count DESC
            ''')
            errors_by_type = cursor.fetchall()
            
            cursor.execute('''
                SELECT module_name, COUNT(*) as count
                FROM error_logs
                GROUP BY module_name
                ORDER BY count DESC
            ''')
            errors_by_module = cursor.fetchall()
            
            return {
                'total': total,
                'unresolved': unresolved,
                'resolved': total - unresolved,
                'by_type': [{'type': t[0], 'count': t[1]} for t in errors_by_type],
                'by_module': [{'module': m[0], 'count': m[1]} for m in errors_by_module]
            }
        finally:
            conn.close()


def safe_call(func, *args, error_logger: ErrorLogger = None, **kwargs):
    """
    安全调用函数包装器 - 自动捕获异常
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        
        if error_logger:
            error_logger.log_error(
                error_type=type(e).__name__,
                error_message=error_msg,
                module_name=func.__module__,
                function_name=func.__name__,
                error_traceback=traceback_str
            )
        
        return None, error_msg
