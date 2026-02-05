#!/bin/bash
# 打印调试信息
echo "Current PORT environment variable is: $PORT"
echo "Starting Gunicorn..."

# 如果 PORT 变量没设置，或者是占位符，就默认 3000
if [[ -z "$PORT" ]] || [[ "$PORT" == "\${WEB_PORT}" ]]; then
    echo "PORT is not set or invalid ($PORT), using default 3000"
    TARGET_PORT=3000
else
    # 尝试检查是否为纯数字
    if [[ "$PORT" =~ ^[0-9]+$ ]]; then
        TARGET_PORT=$PORT
    else
        echo "PORT ($PORT) is not a number, defaulting to 3000"
        TARGET_PORT=3000
    fi
fi

# 启动 Gunicorn
# 使用 gevent 模式以支持高并发
# 绑定到 0.0.0.0:$TARGET_PORT
exec gunicorn app:app \
    -w 1 \
    --timeout 120 \
    --bind 0.0.0.0:$TARGET_PORT \
    --access-logfile - \
    --error-logfile -
