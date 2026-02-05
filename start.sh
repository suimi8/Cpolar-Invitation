#!/bin/bash
# 打印调试信息
echo "Current PORT environment variable is: $PORT"
echo "Starting Gunicorn..."

# 如果 PORT 变量没设置，就默认 3000
TARGET_PORT=${PORT:-3000}

# 启动 Gunicorn
# 使用 gevent 模式以支持高并发
# 绑定到 0.0.0.0:$TARGET_PORT
exec gunicorn app:app \
    -k gevent \
    -w 1 \
    --timeout 120 \
    --bind 0.0.0.0:$TARGET_PORT \
    --access-logfile - \
    --error-logfile -
