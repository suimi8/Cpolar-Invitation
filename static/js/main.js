document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');
    const inviteCodeInput = document.getElementById('inviteCode');
    const cdkeyInput = document.getElementById('cdkey');
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
        const cdkey = cdkeyInput.value.trim();

        if (!inviteCode) {
            addLog('错误: 请提供邀请码', 'error');
            return;
        }

        if (!cdkey) {
            addLog('错误: 请输入验证卡密', 'error');
            return;
        }

        // Reset UI
        statusPanel.style.display = 'block';
        startBtn.disabled = true;
        startBtn.innerText = '正在验证卡密并运行...';
        progressFill.style.width = '0%';
        progressText.innerText = '准备中...';
        percentageText.innerText = '0%';
        completedNum.innerText = '0';
        successNum.innerText = '0';
        logContent.innerHTML = '';
        addLog('正在提交卡密验证...', 'system');

        try {
            const response = await fetch('/api/batch_register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ invite_code: inviteCode, cdkey: cdkey })
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
            startBtn.innerText = '验证卡密并开始注册';
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
                    let logMsg = `[√] #${res.index} ${res.email} - 注册并获取推广码成功`;
                    if (res.plan_name && res.plan_name !== '未知') {
                        logMsg += ` | 套餐: ${res.plan_name}`;
                    }
                    addLog(logMsg, 'success');
                } else if (res.status === 'partial_success') {
                    addLog(`[!] #${res.index} ${res.email} - ${res.message}`, 'info');
                } else {
                    addLog(`[X] #${res.index} 失败: ${res.message}`, 'error');
                }
                break;
            case 'finished':
                addLog('任务完成!', 'system');
                progressText.innerText = '任务已完成';
                break;
        }
    }

    // --- Cpolar Promo Code Fetch Logic ---
    const openFetchModal = document.getElementById('openFetchModal');
    const fetchModal = document.getElementById('fetchModal');
    const closeFetchModal = document.getElementById('closeFetchModal');
    const doFetchCode = document.getElementById('doFetchCode');
    const cpolarEmail = document.getElementById('cpolarEmail');
    const cpolarPassword = document.getElementById('cpolarPassword');
    const planInfoBox = document.getElementById('planInfoBox');
    const planName = document.getElementById('planName');
    const planStart = document.getElementById('planStart');
    const planEnd = document.getElementById('planEnd');

    openFetchModal.addEventListener('click', () => {
        fetchModal.style.display = 'flex';
        // 重置套餐信息显示
        planInfoBox.style.display = 'none';
    });

    closeFetchModal.addEventListener('click', () => {
        fetchModal.style.display = 'none';
    });

    doFetchCode.addEventListener('click', async () => {
        const email = cpolarEmail.value.trim();
        const password = cpolarPassword.value.trim();

        if (!email || !password) {
            alert('请输入 Cpolar 账号和密码');
            return;
        }

        const originalText = doFetchCode.innerText;
        doFetchCode.innerText = '正在获取...';
        doFetchCode.disabled = true;
        planInfoBox.style.display = 'none';

        try {
            const res = await fetch('/api/get_cpolar_promo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();

            if (data.success) {
                // 显示推广码
                if (data.promo_code) {
                    inviteCodeInput.value = data.promo_code;
                    addLog(`成功自动获取推广码: ${data.promo_code}`, 'success');
                } else {
                    addLog(data.promo_message || '未找到推广码', 'info');
                }

                // 显示套餐信息
                if (data.plan && data.plan.name) {
                    planName.innerText = data.plan.name.toUpperCase();
                    planStart.innerText = data.plan.start_time || '-';
                    planEnd.innerText = data.plan.end_time || '-';
                    planInfoBox.style.display = 'block';
                    addLog(`套餐: ${data.plan.name} (${data.plan.start_time} ~ ${data.plan.end_time})`, 'success');
                }

                // 如果有推广码才自动关闭
                if (data.promo_code) {
                    setTimeout(() => {
                        fetchModal.style.display = 'none';
                    }, 2000);
                }
            } else {
                alert(data.message || '获取失败，请重试');
            }
        } catch (e) {
            alert('网络错误，请稍后再试');
        } finally {
            doFetchCode.innerText = originalText;
            doFetchCode.disabled = false;
        }
    });
});
