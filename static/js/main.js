document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');
    const inviteCodeInput = document.getElementById('inviteCode');
    const countInput = document.getElementById('count');
    const threadsInput = document.getElementById('threads');
    const statusPanel = document.getElementById('statusPanel');
    const logContent = document.getElementById('logContent');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const percentageText = document.getElementById('percentage');
    const completedNum = document.getElementById('completedNum');
    const successNum = document.getElementById('successNum');
    const clearLogsBtn = document.getElementById('clearLogs');

    const addLog = (message, type = 'info') => {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        const time = new Date().toLocaleTimeString();
        entry.innerText = `[${time}] ${message}`;
        logContent.appendChild(entry);
        logContent.scrollTop = logContent.scrollHeight;
    };

    clearLogsBtn.addEventListener('click', () => {
        logContent.innerHTML = '';
        addLog('日志已清空', 'system');
    });

    startBtn.addEventListener('click', async () => {
        const inviteCode = inviteCodeInput.value.trim();
        const count = parseInt(countInput.value);
        const threads = parseInt(threadsInput.value);

        if (!inviteCode) {
            addLog('错误: 请提供邀请码', 'error');
            return;
        }

        // Reset UI
        statusPanel.style.display = 'block';
        startBtn.disabled = true;
        startBtn.innerText = '正在注册...';
        progressFill.style.width = '0%';
        progressText.innerText = '准备中...';
        percentageText.innerText = '0%';
        completedNum.innerText = '0';
        successNum.innerText = '0';
        logContent.innerHTML = '';
        addLog('开始执行批量注册任务...', 'system');

        try {
            const response = await fetch('/api/batch_register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ invite_code: inviteCode, count, threads })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || '服务器响应错误');
            }

            // Read stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.substring(6));
                        handleEvent(data);
                    }
                }
            }

        } catch (error) {
            addLog(`请求失败: ${error.message}`, 'error');
        } finally {
            startBtn.disabled = false;
            startBtn.innerText = '开始批量注册';
        }
    });

    function handleEvent(data) {
        switch (data.type) {
            case 'info':
                addLog(data.message, 'info');
                break;
            case 'progress':
                const perc = Math.round((data.completed / data.total) * 100);
                progressFill.style.width = `${perc}%`;
                percentageText.innerText = `${perc}%`;
                progressText.innerText = `进度: ${data.completed} / ${data.total}`;
                completedNum.innerText = data.completed;
                successNum.innerText = data.success;

                const res = data.last_result;
                if (res.status === 'success') {
                    addLog(`[√] #${res.index} ${res.email} - 注册并获取推广码成功`, 'success');
                } else if (res.status === 'partial_success') {
                    addLog(`[!] #${res.index} ${res.email} - ${res.message}`, 'info');
                } else {
                    addLog(`[X] #${res.index} 失败: ${res.message}`, 'error');
                }
                break;
            case 'finished':
                addLog(`任务完成! 总计: ${data.total}, 成功: ${data.success}`, 'system');
                progressText.innerText = '任务已完成';
                break;
        }
    }
});
