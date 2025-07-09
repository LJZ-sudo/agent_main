// 科研多Agent系统前端应用
class ResearchSystemApp {
    constructor() {
        this.apiEndpoint = 'http://localhost:8000';
        this.wsEndpoint = 'ws://localhost:8000/ws';
        this.websocket = null;
        this.currentSessionId = null;
        this.isConnected = false;
        this.refreshInterval = 5000;
        this.knowledgeGraphNetwork = null;
        
        // 初始化应用
        this.init();
    }
    
    async init() {
        console.log('初始化科研多Agent系统前端...');
        
        // 绑定事件监听器
        this.bindEventListeners();
        
        // 连接WebSocket
        await this.connectWebSocket();
        
        // 初始化系统状态
        await this.initializeSystemStatus();
        
        // 初始化系统类型指示器（固定显示真实Agent系统）
        this.updateSystemTypeIndicator();
        
        // 开始定期更新
        this.startPeriodicUpdates();
        
        console.log('真实Agent系统前端初始化完成');
        this.addSystemLog('真实Agent系统前端初始化完成');
    }
    
    bindEventListeners() {
        // 研究提交按钮
        document.getElementById('submit-research-btn').addEventListener('click', () => {
            this.submitResearchRequest();
        });
        
        // 研究输入框回车键
        document.getElementById('research-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.submitResearchRequest();
            }
        });
        
        // 记录输入活动
        document.getElementById('research-input').addEventListener('input', () => {
            this.recordUserActivity();
        });
        
        // 设置按钮
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.toggleApiConfigPanel();
        });
        
        // API配置相关
        document.getElementById('api-provider').addEventListener('change', () => {
            this.updateModelOptions();
        });
        
        document.getElementById('apply-config').addEventListener('click', () => {
            this.applyApiConfig();
        });
        
        // 快速操作按钮
        document.getElementById('clear-history-btn').addEventListener('click', () => {
            this.clearChatHistory();
        });
        
        document.getElementById('export-data-btn').addEventListener('click', () => {
            this.exportData();
        });
        
        document.getElementById('system-restart-btn').addEventListener('click', () => {
            this.restartSystem();
        });
    }
    
    async connectWebSocket() {
        try {
            console.log('正在连接WebSocket:', this.wsEndpoint);
            this.websocket = new WebSocket(this.wsEndpoint);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket连接已建立');
                this.isConnected = true;
                this.updateSystemStatus('active', '系统运行正常');
                this.addSystemLog('WebSocket连接已建立');
                
                // 发送ping测试连接
                this.sendPing();
                
                // 订阅状态更新
                this.subscribeToBlackboard();
                this.subscribeToSystemStatus();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('WebSocket消息解析错误:', error);
                    this.addSystemLog('消息解析错误: ' + error.message);
                }
            };
            
            this.websocket.onclose = (event) => {
                console.log('⚠️ WebSocket连接已关闭', event);
                this.isConnected = false;
                this.updateSystemStatus('warning', '连接已断开，正在重连...');
                this.addSystemLog('WebSocket连接已关闭，尝试重连中...');
                
                // 延迟重连
                setTimeout(() => {
                    if (!this.isConnected) {
                        this.connectWebSocket();
                    }
                }, 3000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket错误:', error);
                this.updateSystemStatus('error', '连接错误');
                this.addSystemLog('WebSocket连接错误，请检查后端服务');
            };
            
        } catch (error) {
            console.error('❌ WebSocket连接初始化失败:', error);
            this.updateSystemStatus('error', '连接失败');
            this.addSystemLog('连接初始化失败: ' + error.message);
            
            // 尝试重连
            setTimeout(() => {
                this.connectWebSocket();
            }, 5000);
        }
    }
    
    sendPing() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'ping',
                timestamp: new Date().toISOString()
            }));
        }
    }
    
    subscribeToSystemStatus() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'subscribe_status'
            }));
        }
    }
    
    handleWebSocketMessage(data) {
        console.log('收到WebSocket消息:', data);
        
        switch (data.type) {
            case 'research_submitted':
                this.handleResearchSubmitted(data);
                break;
            case 'task_progress':
                this.updateTaskProgress(data);
                break;
            case 'agent_status':
                this.updateAgentStatus(data);
                this.updateBlackboardAgents(data);
                break;
            case 'chain_of_thought':
                this.updateChainOfThought(data);
                break;
            case 'knowledge_graph_update':
                this.updateKnowledgeGraph(data);
                break;
            case 'research_result':
                this.displayResearchResult(data);
                break;
            case 'system_metrics':
                this.updateSystemMetrics(data);
                break;
            case 'system_log':
                this.addSystemLog(data.message);
                break;
            case 'blackboard_update':
                this.updateBlackboard(data.data);
                break;
                
            case 'agent_progress':
                console.log('处理agent_progress消息:', data);
                this.updateAgentProgress(data);
                
                // 同时更新黑板Agent状态
                this.updateBlackboardAgentStatus({
                    agent: data.agent,
                    status: data.status,
                    task: data.task,
                    progress: data.progress,
                    details: data.details
                });
                break;
                
            case 'thought_step':
                if (data.session_id && data.data) {
                    this.addThoughtStep(data.session_id, data.data);
                }
                break;
                
            case 'research_started':
                console.log('研究开始消息:', data);
                
                // 初始化所有Agent状态为准备状态
                const agents = ['main_agent', 'information_agent', 'verification_agent', 'critique_agent', 'report_agent'];
                    
                agents.forEach(agent => {
                    this.updateBlackboardAgentStatus({
                        agent: agent,
                        status: '准备中',
                        task: '等待任务分配',
                        progress: 0
                    });
                });
                break;
                
            case 'research_completed':
                console.log('研究完成消息:', data);
                this.displayResearchResult(data);
                if (data.result) {
                    this.displayResearchResult(data.result);
                    this.addChatMessage('assistant', this.formatResearchResult(data.result));
                }
                if (data.thought_chain) {
                    this.updateThoughtChain(data.session_id, data.thought_chain);
                }
                this.addSystemLog(`✅ 研究完成 - 耗时 ${data.processing_time || 0}秒`);
                // 标记所有Agent为完成状态
                const allAgents = ['information_agent', 'modeling_agent', 'verification_agent', 'report_agent'];
                allAgents.forEach(agent => {
                    this.updateBlackboardAgentStatus({
                        agent: agent,
                        status: '已完成',
                        task: '任务完成',
                        progress: 100
                    });
                });
                break;
            case 'blackboard_status':
                this.updateBlackboard(data.data);
                break;
            case 'config_updated':
                this.updateCurrentConfig(data.data);
                break;
            case 'agent_collaboration':
                this.handleAgentCollaboration(data);
                break;
            case 'research_error':
                this.handleResearchError(data);
                break;
            case 'system_fallback':
                this.handleSystemFallback(data);
                break;
            default:
                console.log('未知消息类型:', data.type);
        }
    }
    
    async submitResearchRequest() {
        const input = document.getElementById('research-input').value.trim();
        const mode = document.getElementById('research-mode').value;
        const priority = document.getElementById('priority-level').value;
        
        if (!input) {
            alert('请输入研究问题');
            return;
        }
        
        // 记录用户活动
        this.recordUserActivity();
        
        // 显示用户消息
        this.addChatMessage('user', input);
        
        // 清空输入框
        document.getElementById('research-input').value = '';
        
        // 显示思考动画和预计时间
        this.showThinkingAnimation();
        this.addSystemLog('研究请求已提交，预计处理时间: 60-120秒');
        
        try {
            console.log('发送研究请求:', { query: input, priority, mode });
            
            const response = await fetch(`${this.apiEndpoint}/api/v1/research/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: input,
                    priority: priority,
                    collaboration_mode: mode
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status} - ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('✅ API响应:', result);
            
            if (result.success) {
                // 研究已开始，等待WebSocket消息
                this.addSystemLog('✅ 研究请求已接受，等待Agent协作处理...');
                
                // 如果有session_id，可以存储用于后续跟踪
                if (result.data && result.data.session_id) {
                    this.currentSessionId = result.data.session_id;
                    this.addSystemLog(`📋 会话ID: ${this.currentSessionId}`);
                }
                
                if (result.data && result.data.estimated_duration) {
                    this.addSystemLog(`⏱️ 预计处理时间: ${result.data.estimated_duration}`);
                }
                
            } else {
                this.addChatMessage('system', `❌ 提交失败: ${result.message || '未知错误'}`);
                this.hideThinkingAnimation();
                this.addSystemLog('❌ 研究请求提交失败');
                this.showErrorToast('研究请求提交失败: ' + (result.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('❌ 提交研究请求失败:', error);
            this.addChatMessage('system', `❌ 提交失败: ${error.message}`);
            this.hideThinkingAnimation();
            this.addSystemLog(`❌ 网络连接失败: ${error.message}`);
            this.showErrorToast('请检查网络连接或后端服务状态');
        }
    }
    
    async initializeSystemStatus() {
        try {
            const response = await fetch(`${this.apiEndpoint}/api/v1/status`);
            const result = await response.json();
            
            if (result.success) {
                this.updateSystemMetrics(result.data);
                this.updateAgentStatusList(result.data.agents_status || {});
                this.updateSystemStatus('active', '系统运行正常');
            }
            
        } catch (error) {
            console.error('获取系统状态失败:', error);
            this.updateSystemStatus('error', '无法获取系统状态');
        }
        
        // 初始化API配置
        await this.loadApiConfig();
        
        // 优化的定时检查 - 降低频率，采用智能检查策略
        this.startSmartMonitoring();
    }

    // 智能监控机制
    startSmartMonitoring() {
        // 初始化监控状态
        this.connectionHealth = 'checking';
        this.consecutiveFailures = 0;
        this.lastUserActivity = Date.now();

        // 基础状态检查 - 每60秒一次（降低频率）
        this.statusCheckInterval = setInterval(() => {
            this.checkSystemStatus();
        }, 60000);

        // 配置检查 - 每5分钟一次
        this.configCheckInterval = setInterval(() => {
            this.loadApiConfig();
        }, 300000);

        // 系统监控 - 仅在活跃时每2分钟一次
        this.monitoringInterval = setInterval(() => {
            if (this.isActiveSession()) {
                this.updateSystemMonitor();
            }
        }, 120000);

        // 连接健康检查 - 每30秒，但使用心跳机制
        this.heartbeatInterval = setInterval(() => {
            this.performHeartbeat();
        }, 30000);
    }

    // 检查是否有活跃会话
    isActiveSession() {
        // 检查是否有进行中的研究请求或用户交互
        const lastActivity = this.lastUserActivity || 0;
        const now = Date.now();
        return (now - lastActivity) < 300000; // 5分钟内有活动
    }

    // 心跳检查 - 轻量级健康检查
    async performHeartbeat() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch(`${this.apiEndpoint}/api/health`, {
                method: 'GET',
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                this.connectionHealth = 'good';
                this.consecutiveFailures = 0;
                if (this.wasDisconnected) {
                    this.updateSystemStatus('active', '连接已恢复');
                    this.wasDisconnected = false;
                }
            } else {
                this.handleConnectionIssue();
            }
        } catch (error) {
            this.handleConnectionIssue();
        }
    }

    // 处理连接问题
    handleConnectionIssue() {
        this.consecutiveFailures = (this.consecutiveFailures || 0) + 1;
        
        if (this.consecutiveFailures >= 3) {
            this.connectionHealth = 'poor';
            this.updateSystemStatus('warning', '连接不稳定，正在尝试恢复...');
            this.wasDisconnected = true;
            
            // 降级到更低频率的检查
            if (this.statusCheckInterval) {
                clearInterval(this.statusCheckInterval);
                this.statusCheckInterval = setInterval(() => {
                    this.checkSystemStatus();
                }, 180000); // 3分钟一次
            }
        }
        
        if (this.consecutiveFailures >= 5) {
            this.connectionHealth = 'failed';
            this.updateSystemStatus('error', '连接已断开，请检查服务器状态');
        }
    }

    // 记录用户活动
    recordUserActivity() {
        this.lastUserActivity = Date.now();
        
        // 如果连接状况不好，用户活动时尝试恢复正常频率
        if (this.connectionHealth !== 'good') {
            this.restoreNormalMonitoring();
        }
    }

    // 恢复正常监控频率
    restoreNormalMonitoring() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = setInterval(() => {
                this.checkSystemStatus();
            }, 60000);
        }
    }

    // 优化的状态检查
    async checkSystemStatus() {
        // 只在必要时进行完整检查
        if (this.isActiveSession() || this.consecutiveFailures > 0) {
            try {
                const response = await fetch(`${this.apiEndpoint}/api/v1/status`);
                const result = await response.json();
                
                if (result.success) {
                    this.updateSystemMetrics(result.data);
                    this.consecutiveFailures = 0;
                    this.connectionHealth = 'good';
                }
            } catch (error) {
                this.handleConnectionIssue();
            }
        }
    }
    
    updateSystemStatus(status, text) {
        const statusIndicator = document.getElementById('system-status');
        const statusText = document.getElementById('system-status-text');
        
        statusIndicator.className = `status-indicator status-${status}`;
        statusText.textContent = text;
    }
    
    updateSystemMetrics(data) {
        // 更新性能指标
        document.getElementById('cpu-usage').textContent = `${data.cpu_usage || 0}%`;
        document.getElementById('memory-usage').textContent = `${data.memory_usage || 0}%`;
        document.getElementById('active-sessions').textContent = data.active_sessions || 0;
        document.getElementById('completed-tasks').textContent = data.completed_tasks || 0;
    }
    
    updateAgentStatusList(agents) {
        const container = document.getElementById('agent-status-list');
        container.innerHTML = '';
        
        const agentList = [
            { name: 'MainAgent', displayName: '主控Agent', icon: 'fas fa-brain' },
            { name: 'InformationAgent', displayName: '信息Agent', icon: 'fas fa-search' },
            { name: 'CritiqueAgent', displayName: '批判Agent', icon: 'fas fa-balance-scale' },
            { name: 'ReportAgent', displayName: '报告Agent', icon: 'fas fa-file-alt' },
            { name: 'VerificationAgent', displayName: '验证Agent', icon: 'fas fa-check-circle' },
            { name: 'ModelingAgent', displayName: '建模Agent', icon: 'fas fa-project-diagram' },
            { name: 'ExperimentDesignAgent', displayName: '实验设计Agent', icon: 'fas fa-flask' },
            { name: 'EvaluationAgent', displayName: '评估Agent', icon: 'fas fa-chart-line' }
        ];
        
        agentList.forEach(agent => {
            const agentData = agents[agent.name] || { status: 'idle', tasks: 0 };
            const statusClass = this.getAgentStatusClass(agentData.status);
            
            const agentElement = document.createElement('div');
            agentElement.className = 'agent-card p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100';
            agentElement.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex items-center">
                        <i class="${agent.icon} text-blue-500 mr-2"></i>
                        <div>
                            <div class="font-medium text-sm">${agent.displayName}</div>
                            <div class="text-xs text-gray-500">任务: ${agentData.tasks || 0}</div>
                        </div>
                    </div>
                    <span class="status-indicator ${statusClass}"></span>
                </div>
            `;
            
            container.appendChild(agentElement);
        });
    }
    
    getAgentStatusClass(status) {
        const statusMap = {
            'active': 'status-active',
            'busy': 'status-busy',
            'idle': 'status-idle',
            'error': 'status-error'
        };
        return statusMap[status] || 'status-idle';
    }
    
    addChatMessage(sender, content) {
        const chatMessages = document.getElementById('chat-messages');
        
        // 移除欢迎消息
        const welcomeMessage = chatMessages.querySelector('.text-center');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = `message-bubble p-3 rounded-lg ${sender === 'user' ? 'user-message ml-auto' : 'agent-message'}`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        messageElement.innerHTML = `
            <div class="text-sm mb-1 ${sender === 'user' ? 'text-white text-opacity-80' : 'text-gray-500'}">
                ${sender === 'user' ? '您' : 'AI助手'} • ${timestamp}
            </div>
            <div class="whitespace-pre-wrap">${content}</div>
        `;
        
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    showThinkingAnimation() {
        const thinkingElement = document.createElement('div');
        thinkingElement.id = 'thinking-animation';
        thinkingElement.className = 'message-bubble agent-message p-3 rounded-lg thinking-animation';
        thinkingElement.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-brain mr-2 text-blue-500"></i>
                <span>AI正在思考中...</span>
                <div class="ml-2 flex space-x-1">
                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                </div>
            </div>
        `;
        
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.appendChild(thinkingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    hideThinkingAnimation() {
        const thinkingElement = document.getElementById('thinking-animation');
        if (thinkingElement) {
            thinkingElement.remove();
        }
    }
    
    updateChainOfThought(data) {
        const chainContainer = document.getElementById('chain-of-thought');
        const stepsContainer = document.getElementById('chain-steps');
        
        chainContainer.style.display = 'block';
        
        const step = document.createElement('div');
        step.className = 'chain-step';
        step.innerHTML = `
            <div class="font-medium text-sm">${data.step_type}</div>
            <div class="text-sm text-gray-600 mt-1">${data.content}</div>
            <div class="text-xs text-gray-500 mt-1">${data.reasoning}</div>
        `;
        
        stepsContainer.appendChild(step);
        stepsContainer.scrollTop = stepsContainer.scrollHeight;
    }
    
    updateTaskProgress(data) {
        const progressList = document.getElementById('task-progress-list');
        const overallProgress = document.getElementById('overall-progress');
        const progressText = document.getElementById('progress-text');
        
        // 更新任务列表
        let taskElement = document.getElementById(`task-${data.task_id}`);
        if (!taskElement) {
            taskElement = document.createElement('div');
            taskElement.id = `task-${data.task_id}`;
            taskElement.className = 'flex items-center justify-between p-2 bg-gray-50 rounded';
            progressList.appendChild(taskElement);
        }
        
        const statusIcon = this.getTaskStatusIcon(data.status);
        taskElement.innerHTML = `
            <div class="flex items-center">
                <i class="${statusIcon.icon} ${statusIcon.color} mr-2"></i>
                <span class="text-sm">${data.description || data.task_type}</span>
            </div>
            <span class="text-xs text-gray-500">${data.status}</span>
        `;
        
        // 更新总体进度
        if (data.overall_progress !== undefined) {
            overallProgress.style.width = `${data.overall_progress}%`;
            progressText.textContent = `${Math.round(data.overall_progress)}% 完成`;
        }
    }
    
    getTaskStatusIcon(status) {
        const statusMap = {
            'pending': { icon: 'fas fa-clock', color: 'text-gray-500' },
            'in_progress': { icon: 'fas fa-spinner fa-spin', color: 'text-blue-500' },
            'completed': { icon: 'fas fa-check-circle', color: 'text-green-500' },
            'failed': { icon: 'fas fa-times-circle', color: 'text-red-500' }
        };
        return statusMap[status] || statusMap['pending'];
    }
    
    updateKnowledgeGraph(data) {
        if (!data.nodes || !data.edges) return;
        
        const container = document.getElementById('knowledge-graph');
        
        // 准备vis.js数据
        const nodes = new vis.DataSet(data.nodes.map(node => ({
            id: node.id,
            label: node.name,
            group: node.type,
            title: node.description,
            size: node.importance * 5
        })));
        
        const edges = new vis.DataSet(data.edges.map(edge => ({
            from: edge.source,
            to: edge.target,
            label: edge.type,
            width: edge.strength || 1
        })));
        
        const graphData = { nodes, edges };
        
        const options = {
            groups: {
                concept: { color: { background: '#e3f2fd', border: '#1976d2' } },
                method: { color: { background: '#f3e5f5', border: '#7b1fa2' } },
                result: { color: { background: '#e8f5e8', border: '#388e3c' } },
                innovation_opportunity: { color: { background: '#fff3e0', border: '#f57c00' } }
            },
            physics: {
                enabled: true,
                stabilization: { iterations: 100 }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200
            }
        };
        
        if (this.knowledgeGraphNetwork) {
            this.knowledgeGraphNetwork.destroy();
        }
        
        this.knowledgeGraphNetwork = new vis.Network(container, graphData, options);
    }
    
    displayResearchResult(data) {
        this.hideThinkingAnimation();
        
        // 添加AI回复消息
        this.addChatMessage('ai', data.content || `研究完成！关于"${data.query || '未知主题'}"的深度分析已生成，请查看右侧详细报告。`);
        
        // 更新结果面板
        const resultsContainer = document.getElementById('research-results');
        resultsContainer.innerHTML = '';
        
        // 处理最终研究报告
        if (data.result && typeof data.result === 'object') {
            const result = data.result;
            
            // 创建报告标题
            const titleElement = document.createElement('div');
            titleElement.className = 'bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-lg mb-4';
            titleElement.innerHTML = `
                <h3 class="text-lg font-bold mb-2">${result['研究主题'] || '研究报告'}</h3>
                <p class="text-sm opacity-90">研究领域: ${result['研究领域'] || '通用研究'}</p>
                <p class="text-xs opacity-75 mt-1">处理时间: ${data.processing_time ? data.processing_time.toFixed(1) + '秒' : 'N/A'}</p>
            `;
            resultsContainer.appendChild(titleElement);
            
            // 执行概要
            if (result['执行概要']) {
                const summaryElement = document.createElement('div');
                summaryElement.className = 'bg-white border border-gray-200 rounded-lg p-4 mb-4';
                summaryElement.innerHTML = `
                    <h4 class="font-semibold text-sm mb-3 text-blue-600 flex items-center">
                        <i class="fas fa-clipboard-list mr-2"></i>执行概要
                    </h4>
                    <div class="space-y-2 text-sm">
                        <p><strong>研究目标:</strong> ${result['执行概要']['研究目标'] || 'N/A'}</p>
                        <p><strong>研究方法:</strong> ${result['执行概要']['研究方法'] || 'N/A'}</p>
                        <p><strong>可靠性评估:</strong> ${result['执行概要']['可靠性评估'] || 'N/A'}</p>
                        <div class="mt-3">
                            <strong>主要发现:</strong>
                            <ul class="list-disc list-inside mt-1 text-xs space-y-1">
                                ${(result['执行概要']['主要发现'] || []).map(finding => `<li>${finding}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                `;
                resultsContainer.appendChild(summaryElement);
            }
            
            // 信息收集成果
            if (result['信息收集成果']) {
                const infoElement = document.createElement('div');
                infoElement.className = 'bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4';
                const info = result['信息收集成果'];
                infoElement.innerHTML = `
                    <h4 class="font-semibold text-sm mb-3 text-blue-600 flex items-center">
                        <i class="fas fa-search mr-2"></i>信息收集成果
                    </h4>
                    <div class="grid grid-cols-2 gap-2 text-xs">
                        <div>文献总数: <span class="font-semibold">${info['文献总数'] || 0}</span></div>
                        <div>高质量论文: <span class="font-semibold">${info['高质量论文'] || 0}</span></div>
                        <div>关键发现: <span class="font-semibold">${info['关键发现'] || 0}</span></div>
                        <div>研究质量: <span class="font-semibold">${info['研究质量'] || 'N/A'}</span></div>
                    </div>
                    ${info['核心主题'] && info['核心主题'].length > 0 ? `
                        <div class="mt-3">
                            <strong class="text-xs">核心主题:</strong>
                            <div class="flex flex-wrap gap-1 mt-1">
                                ${info['核心主题'].map(theme => `<span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">${theme}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                `;
                resultsContainer.appendChild(infoElement);
            }
            
            // 建模分析结果
            if (result['建模分析结果']) {
                const modelElement = document.createElement('div');
                modelElement.className = 'bg-green-50 border border-green-200 rounded-lg p-4 mb-4';
                const model = result['建模分析结果'];
                modelElement.innerHTML = `
                    <h4 class="font-semibold text-sm mb-3 text-green-600 flex items-center">
                        <i class="fas fa-brain mr-2"></i>建模分析结果
                    </h4>
                    <div class="grid grid-cols-2 gap-2 text-xs mb-3">
                        <div>框架质量: <span class="font-semibold">${model['框架质量'] || 'N/A'}</span></div>
                        <div>创新评分: <span class="font-semibold">${model['创新评分'] || 'N/A'}</span></div>
                        <div>模型特征: <span class="font-semibold">${model['模型特征'] || 'N/A'}</span></div>
                        <div>技术创新: <span class="font-semibold">${model['技术创新'] || 'N/A'}</span></div>
                    </div>
                    ${model['核心发现'] && model['核心发现'].length > 0 ? `
                        <div>
                            <strong class="text-xs">核心发现:</strong>
                            <ul class="list-disc list-inside mt-1 text-xs space-y-1">
                                ${model['核心发现'].map(finding => `<li>${finding}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                `;
                resultsContainer.appendChild(modelElement);
            }
            
            // 验证评估报告
            if (result['验证评估报告']) {
                const verifyElement = document.createElement('div');
                verifyElement.className = 'bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4';
                const verify = result['验证评估报告'];
                verifyElement.innerHTML = `
                    <h4 class="font-semibold text-sm mb-3 text-purple-600 flex items-center">
                        <i class="fas fa-check-double mr-2"></i>验证评估报告
                    </h4>
                    <div class="grid grid-cols-2 gap-2 text-xs mb-3">
                        <div>可靠性等级: <span class="font-semibold">${verify['可靠性等级'] || 'N/A'}</span></div>
                        <div>验证状态: <span class="font-semibold">${verify['验证状态'] || 'N/A'}</span></div>
                    </div>
                    ${verify['改进建议'] && verify['改进建议'].length > 0 ? `
                        <div>
                            <strong class="text-xs">改进建议:</strong>
                            <ul class="list-disc list-inside mt-1 text-xs space-y-1">
                                ${verify['改进建议'].slice(0, 3).map(suggestion => `<li>${suggestion}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                `;
                resultsContainer.appendChild(verifyElement);
            }
            
            // 专业研究建议
            if (result['专业研究建议'] && result['专业研究建议'].length > 0) {
                const recommendElement = document.createElement('div');
                recommendElement.className = 'bg-orange-50 border border-orange-200 rounded-lg p-4 mb-4';
                recommendElement.innerHTML = `
                    <h4 class="font-semibold text-sm mb-3 text-orange-600 flex items-center">
                        <i class="fas fa-lightbulb mr-2"></i>专业研究建议
                    </h4>
                    <ul class="list-disc list-inside text-xs space-y-1">
                        ${result['专业研究建议'].map(suggestion => `<li>${suggestion}</li>`).join('')}
                    </ul>
                `;
                resultsContainer.appendChild(recommendElement);
            }
            
            // 协作统计
            if (result['协作统计']) {
                const statsElement = document.createElement('div');
                statsElement.className = 'bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4';
                const stats = result['协作统计'];
                statsElement.innerHTML = `
                    <h4 class="font-semibold text-sm mb-3 text-gray-600 flex items-center">
                        <i class="fas fa-chart-bar mr-2"></i>协作统计
                    </h4>
                    <div class="grid grid-cols-3 gap-2 text-xs">
                        <div>参与Agent: <span class="font-semibold">${stats['参与Agent数量'] || 0}</span></div>
                        <div>协作事件: <span class="font-semibold">${stats['协作事件总数'] || 0}</span></div>
                        <div>思考步骤: <span class="font-semibold">${stats['思考步骤数量'] || 0}</span></div>
                        <div>任务完成率: <span class="font-semibold">${stats['任务完成率'] || 'N/A'}</span></div>
                        <div>协作效率: <span class="font-semibold">${stats['协作效率'] || 'N/A'}</span></div>
                        <div>数据交换: <span class="font-semibold">${stats['数据交换次数'] || 0}</span></div>
                    </div>
                `;
                resultsContainer.appendChild(statsElement);
            }
            
        } else if (data.results && Array.isArray(data.results)) {
            // 兼容旧格式
            data.results.forEach((result, index) => {
                const resultElement = document.createElement('div');
                resultElement.className = 'p-3 bg-gray-50 rounded-lg mb-3';
                resultElement.innerHTML = `
                    <div class="font-medium text-sm mb-2">${result.title || `结果 ${index + 1}`}</div>
                    <div class="text-sm text-gray-600">${result.summary || result.content}</div>
                    <div class="text-xs text-gray-500 mt-2">
                        评分: ${result.score || 'N/A'} | 置信度: ${result.confidence || 'N/A'}
                    </div>
                `;
                resultsContainer.appendChild(resultElement);
            });
        } else {
            // 无结果的情况
            const noResultElement = document.createElement('div');
            noResultElement.className = 'text-center text-gray-500 py-8';
            noResultElement.innerHTML = `
                <i class="fas fa-exclamation-triangle text-3xl mb-4"></i>
                <p>暂无研究结果显示</p>
                <p class="text-sm mt-2">请检查研究任务是否正常完成</p>
            `;
            resultsContainer.appendChild(noResultElement);
        }
        
        // 滚动到顶部
        resultsContainer.scrollTop = 0;
    }
    
    startProgressPolling() {
        if (this.progressPollingInterval) {
            clearInterval(this.progressPollingInterval);
        }
        
        this.progressPollingInterval = setInterval(async () => {
            if (this.currentSessionId) {
                try {
                    const response = await fetch(`${this.apiEndpoint}/api/v1/session/${this.currentSessionId}/status`);
                    const result = await response.json();
                    
                    if (result.success && result.data.status === 'completed') {
                        clearInterval(this.progressPollingInterval);
                        this.displayResearchResult(result.data);
                    }
                    
                } catch (error) {
                    console.error('轮询状态失败:', error);
                }
            }
        }, 2000);
    }
    
    startPeriodicUpdates() {
        setInterval(async () => {
            await this.initializeSystemStatus();
        }, this.refreshInterval);
    }
    
    addSystemLog(message) {
        const logsContainer = document.getElementById('system-logs');
        const timestamp = new Date().toLocaleTimeString();
        
        const logElement = document.createElement('div');
        logElement.textContent = `[${timestamp}] ${message}`;
        
        logsContainer.appendChild(logElement);
        logsContainer.scrollTop = logsContainer.scrollHeight;
        
        // 限制日志数量
        const logs = logsContainer.children;
        if (logs.length > 100) {
            logsContainer.removeChild(logs[0]);
        }
    }
    
    showSettingsModal() {
        document.getElementById('settings-modal').classList.remove('hidden');
    }
    
    hideSettingsModal() {
        document.getElementById('settings-modal').classList.add('hidden');
    }
    
    saveSettings() {
        this.apiEndpoint = document.getElementById('api-endpoint').value;
        this.wsEndpoint = document.getElementById('ws-endpoint').value;
        this.refreshInterval = parseInt(document.getElementById('refresh-interval').value) * 1000;
        
        // 保存到localStorage
        localStorage.setItem('research-system-settings', JSON.stringify({
            apiEndpoint: this.apiEndpoint,
            wsEndpoint: this.wsEndpoint,
            refreshInterval: this.refreshInterval
        }));
        
        this.hideSettingsModal();
        this.addSystemLog('设置已保存');
        
        // 重新连接WebSocket
        if (this.websocket) {
            this.websocket.close();
        }
        this.connectWebSocket();
    }
    
    clearChatHistory() {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = `
            <div class="text-center text-gray-500 py-8">
                <i class="fas fa-robot text-4xl mb-4"></i>
                <p>欢迎使用科研多Agent系统！请输入您的研究问题开始对话。</p>
            </div>
        `;
        this.addSystemLog('聊天历史已清除');
    }
    
    async exportData() {
        try {
            const data = {
                session_id: this.currentSessionId,
                chat_history: document.getElementById('chat-messages').innerHTML,
                system_logs: Array.from(document.getElementById('system-logs').children).map(el => el.textContent),
                timestamp: new Date().toISOString()
            };
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `research-session-${this.currentSessionId || 'unknown'}-${Date.now()}.json`;
            a.click();
            
            URL.revokeObjectURL(url);
            this.addSystemLog('数据导出完成');
            
        } catch (error) {
            console.error('导出数据失败:', error);
            this.addSystemLog('数据导出失败');
        }
    }
    
    async restartSystem() {
        if (confirm('确定要重启系统吗？这将中断当前所有任务。')) {
            try {
                await fetch(`${this.apiEndpoint}/api/v1/system/restart`, { method: 'POST' });
                this.addSystemLog('系统重启请求已发送');
                
                // 重置前端状态
                this.currentSessionId = null;
                this.clearChatHistory();
                document.getElementById('research-progress').style.display = 'none';
                document.getElementById('chain-of-thought').style.display = 'none';
                
            } catch (error) {
                console.error('重启系统失败:', error);
                this.addSystemLog('系统重启失败');
            }
        }
    }
    
    // 处理WebSocket特定消息
    handleResearchSubmitted(data) {
        this.addSystemLog(`研究请求已提交: ${data.session_id}`);
    }
    
    updateAgentStatus(data) {
        this.updateAgentStatusList({ [data.agent_name]: data });
    }
    
    // 处理Agent协作消息
    handleAgentCollaboration(data) {
        console.log('处理Agent协作消息:', data);
        
        // 显示协作消息
        this.addSystemLog(`🤝 ${data.from_agent} → ${data.to_agent}: ${data.message}`);
        
        // 更新协作流程视觉效果
        this.updateCollaborationArrow(data.from_agent, data.to_agent);
        
        // 添加协作事件到黑板
        if (data.data_summary) {
            const eventElement = document.createElement('div');
            eventElement.className = 'p-2 bg-blue-50 border border-blue-200 rounded mb-2';
            eventElement.innerHTML = `
                <div class="flex items-center mb-1">
                    <i class="fas fa-exchange-alt text-blue-500 mr-2"></i>
                    <span class="text-xs font-semibold">${data.from_agent} → ${data.to_agent}</span>
                    <span class="text-xs text-gray-500 ml-auto">${new Date().toLocaleTimeString()}</span>
                </div>
                <div class="text-xs text-gray-700 mb-1">${data.message}</div>
                <div class="text-xs text-gray-500">
                    ${Object.entries(data.data_summary).map(([key, value]) => 
                        `${key}: ${value}`
                    ).join(' | ')}
                </div>
            `;
            
            const eventsContainer = document.getElementById('blackboard-events');
            if (eventsContainer) {
                eventsContainer.insertBefore(eventElement, eventsContainer.firstChild);
                
                // 限制事件数量
                const events = eventsContainer.children;
                if (events.length > 20) {
                    eventsContainer.removeChild(events[events.length - 1]);
                }
            }
        }
    }
    
    // 处理研究错误
    handleResearchError(data) {
        console.error('研究过程错误:', data);
        this.hideThinkingAnimation();
        this.addSystemLog(`❌ 研究过程错误: ${data.error}`);
        this.addChatMessage('system', `❌ 研究过程中发生错误: ${data.error}`);
        
        // 如果有回退选项，显示相关信息
        if (data.fallback) {
            this.addSystemLog(`🔄 ${data.fallback}`);
        }
        
        // 重置Agent状态
        this.resetAgentStates();
        
        // 显示错误通知
        this.showErrorToast(`研究过程遇到错误: ${data.error || '未知错误'}`);
    }
    
    // 新增：处理系统回退
    handleSystemFallback(data) {
        console.log('系统回退:', data);
        
        this.addSystemLog(`⚠️ 系统回退: ${data.reason || '未知原因'}`);
        this.addSystemLog(`🔄 切换到: ${data.fallback_system || '备用系统'}`);
        
        // 显示回退通知
        this.showWarningToast(`系统已自动切换到${data.fallback_system || '备用系统'}`);
    }
    
    // 新增：显示警告通知
    showWarningToast(message) {
        // 创建警告通知
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-yellow-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-exclamation-triangle mr-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // 3秒后自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }
    
    // 新增：显示错误通知
    showErrorToast(message, type = 'error') {
        const bgColor = type === 'warning' ? 'bg-yellow-500' : 'bg-red-500';
        const icon = type === 'warning' ? 'fa-exclamation-triangle' : 'fa-times-circle';
        
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 ${bgColor} text-white px-4 py-2 rounded-lg shadow-lg z-50`;
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${icon} mr-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // 5秒后自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    // 重置Agent状态
    resetAgentStates() {
        const container = document.getElementById('blackboard-agents');
        if (container) {
            container.innerHTML = '<div class="text-xs text-gray-500 text-center py-2">等待Agent启动...</div>';
        }
        
        // 重置进度信息
        const agents = ['information_agent', 'modeling_agent', 'verification_agent', 'report_agent', 'main_agent', 'critique_agent'];
        agents.forEach(agent => {
            this.updateBlackboardAgentStatus({
                agent: agent,
                status: '错误',
                task: '任务中断',
                progress: 0
            });
        });
    }
    
    // 更新协作箭头动画
    updateCollaborationArrow(fromAgent, toAgent) {
        const agentMap = {
            'information_agent': 'information',
            'modeling_agent': 'modeling', 
            'verification_agent': 'verification',
            'report_agent': 'report'
        };
        
        const from = agentMap[fromAgent];
        const to = agentMap[toAgent];
        
        if (from && to) {
            // 激活协作流程视觉效果
            this.updateCollaborationFlow(from, 'completed');
            setTimeout(() => {
                this.updateCollaborationFlow(to, 'working');
            }, 500);
        }
    }
    
    displayAgentLogs(logs) {
        // 显示Agent执行日志
        const progressDiv = document.getElementById('research-progress');
        const progressList = document.getElementById('task-progress-list');
        
        if (progressDiv && progressList) {
            progressDiv.style.display = 'block';
            progressList.innerHTML = '';
            
            logs.forEach((log, index) => {
                const logElement = document.createElement('div');
                logElement.className = 'flex items-center space-x-3 p-3 bg-gray-50 rounded-lg mb-2';
                logElement.innerHTML = `
                    <div class="flex-shrink-0">
                        <div class="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                            <i class="fas fa-check text-white text-sm"></i>
                        </div>
                    </div>
                    <div class="flex-1">
                        <div class="text-sm font-medium text-gray-900">${log.agent_name} - ${log.stage}</div>
                        <div class="text-sm text-gray-500">${log.content}</div>
                        <div class="text-xs text-gray-400">${log.timestamp}</div>
                    </div>
                `;
                progressList.appendChild(logElement);
            });
            
            // 更新进度条
            const progressBar = document.getElementById('overall-progress');
            const progressText = document.getElementById('progress-text');
            if (progressBar && progressText) {
                progressBar.style.width = '100%';
                progressText.textContent = '分析完成';
            }
        }
    }
    
    // API配置相关方法
    async loadApiConfig() {
        try {
            const response = await fetch(`${this.apiEndpoint}/api/config`);
            const result = await response.json();
            
            if (result.success) {
                const data = result.data;
                
                // 更新当前配置显示
                document.getElementById('current-config').textContent = 
                    `${data.current_provider} - ${data.current_model}`;
                
                // 更新提供商下拉框
                this.updateProviderOptions(data.available_providers);
                
                // 设置提供商选择器
                document.getElementById('api-provider').value = data.current_provider;
                
                // 更新模型选项
                this.updateModelOptions(data.available_providers);
                
                // 设置当前模型
                document.getElementById('api-model').value = data.current_model;
                
                this.addSystemLog('API配置加载成功');
            } else {
                throw new Error(result.error || 'API配置加载失败');
            }
        } catch (error) {
            console.error('加载API配置失败:', error);
            document.getElementById('current-config').textContent = '加载失败';
            this.addSystemLog(`API配置加载失败: ${error.message}`);
        }
    }
    
    updateProviderOptions(providersData) {
        const providerSelect = document.getElementById('api-provider');
        providerSelect.innerHTML = '';
        
        if (Array.isArray(providersData)) {
            providersData.forEach(provider => {
                const option = document.createElement('option');
                option.value = provider.name;
                option.textContent = provider.display_name || provider.name;
                providerSelect.appendChild(option);
            });
        } else {
            // 兼容旧格式
            Object.keys(providersData).forEach(providerName => {
                const option = document.createElement('option');
                option.value = providerName;
                option.textContent = providerName;
                providerSelect.appendChild(option);
            });
        }
    }

    updateModelOptions(providersData = null) {
        const providerSelect = document.getElementById('api-provider');
        const modelSelect = document.getElementById('api-model');
        const selectedProvider = providerSelect.value;
        
        if (!providersData) {
            // 如果没有提供数据，使用存储的数据或重新加载配置
            if (this.cachedProvidersData) {
                providersData = this.cachedProvidersData;
            } else {
                this.loadApiConfig();
                return;
            }
        } else {
            // 缓存数据供后续使用
            this.cachedProvidersData = providersData;
        }
        
        // 清空模型选项
        modelSelect.innerHTML = '';
        
        let models = [];
        if (Array.isArray(providersData)) {
            // 新格式：数组
            const providerData = providersData.find(p => p.name === selectedProvider);
            models = providerData?.models || [];
        } else {
            // 旧格式：对象
            models = providersData[selectedProvider]?.models || [];
        }
        
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelSelect.appendChild(option);
        });
        
        // 如果只有一个模型，自动选择
        if (models.length === 1) {
            modelSelect.value = models[0];
        }
        
        console.log(`已为 ${selectedProvider} 加载 ${models.length} 个模型:`, models);
    }
    
    async applyApiConfig() {
        const provider = document.getElementById('api-provider').value;
        const model = document.getElementById('api-model').value;
        
        try {
            const response = await fetch(`${this.apiEndpoint}/api/config/switch_provider`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    provider: provider,
                    model: model
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 更新当前配置显示
                document.getElementById('current-config').textContent = 
                    `${result.data.provider} - ${result.data.model}`;
                
                this.addSystemLog(`API配置已更新: ${result.message}`);
                this.addChatMessage('system', `✅ ${result.message}`);
                
                // 显示成功提示
                const applyBtn = document.getElementById('apply-config');
                const originalText = applyBtn.innerHTML;
                applyBtn.innerHTML = '<i class="fas fa-check mr-1"></i>已应用';
                applyBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                applyBtn.classList.add('bg-green-600');
                
                setTimeout(() => {
                    applyBtn.innerHTML = originalText;
                    applyBtn.classList.remove('bg-green-600');
                    applyBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
                }, 2000);
                
            } else {
                this.addSystemLog(`API配置更新失败: ${result.message}`);
                this.addChatMessage('system', `❌ 配置更新失败: ${result.message}`);
            }
            
        } catch (error) {
            console.error('应用API配置失败:', error);
            this.addSystemLog('API配置更新失败');
            this.addChatMessage('system', '❌ 配置更新失败，请检查网络连接');
        }
    }
    
    toggleApiConfigPanel() {
        const panel = document.getElementById('api-config-panel');
        if (panel.style.display === 'none') {
            panel.style.display = 'block';
            this.loadApiConfig(); // 重新加载配置
        } else {
            panel.style.display = 'none';
        }
    }

    // 增强的黑板相关方法
    updateBlackboard(blackboardData) {
        this.updateBlackboardData(blackboardData.data || {}, blackboardData.data_with_metadata || {});
        this.updateBlackboardLogs(blackboardData.logs || []);
        this.updateBlackboardAgentStatus(blackboardData.agent_status || {});
        this.updatePerformanceMetrics(blackboardData.performance_metrics || {});
        this.updateCollaborationStats(blackboardData);
        this.updateBlackboardEvents(blackboardData.events || []);
    }

    updateBlackboardData(data, metadata = {}) {
        const container = document.getElementById('blackboard-data');
        container.innerHTML = '';

        if (Object.keys(data).length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-4">
                    <i class="fas fa-database text-xl mb-2"></i>
                    <p>暂无共享数据</p>
                </div>
            `;
            return;
        }

        Object.entries(data).forEach(([key, value]) => {
            const metaInfo = metadata[key] || {};
            const timestamp = metaInfo.timestamp ? new Date(metaInfo.timestamp).toLocaleTimeString() : '';
            const agent = metaInfo.agent || 'unknown';
            
            const dataItem = document.createElement('div');
            dataItem.className = 'mb-2 p-2 bg-white rounded border-l-4 border-blue-500 hover:shadow-sm transition-shadow';
            dataItem.innerHTML = `
                <div class="flex justify-between items-start mb-1">
                    <div class="font-medium text-xs text-blue-700">${key}</div>
                    <div class="text-xs text-gray-400">${timestamp}</div>
                </div>
                <div class="text-xs text-gray-600 break-words">${this.formatValue(value)}</div>
                <div class="text-xs text-gray-400 mt-1">
                    <i class="fas fa-user-circle mr-1"></i>${agent}
                </div>
            `;
            container.appendChild(dataItem);
        });
    }

    updateBlackboardLogs(logs) {
        const container = document.getElementById('blackboard-logs');
        container.innerHTML = '';

        if (logs.length === 0) {
            container.innerHTML = '<div class="text-gray-500">暂无操作日志</div>';
            return;
        }

        logs.slice(-10).forEach(log => { // 只显示最近10条
            const logItem = document.createElement('div');
            logItem.className = 'mb-1';
            const time = new Date(log.timestamp).toLocaleTimeString();
            const actionColor = log.action === 'write' ? 'text-yellow-400' : 'text-blue-400';
            
            logItem.innerHTML = `
                <span class="text-gray-500">[${time}]</span>
                <span class="text-green-400">${log.agent}</span>
                <span class="${actionColor}">${log.action}</span>
                <span class="text-white">${log.key}</span>
            `;
            container.appendChild(logItem);
        });

        container.scrollTop = container.scrollHeight;
    }

    updateBlackboardAgents(agentData) {
        if (!agentData || !agentData.data) return;
        
        const agent = agentData.data.agent;
        const status = agentData.data.status;
        const task = agentData.data.task || '';

        this.updateSingleBlackboardAgent(agent, status, task);
    }

    updateBlackboardAgentStatus(agentStatus) {
        const container = document.getElementById('blackboard-agents');
        container.innerHTML = '';

        if (Object.keys(agentStatus).length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-4">
                    <i class="fas fa-users text-2xl mb-2"></i>
                    <p class="text-xs">等待Agent启动...</p>
                </div>
            `;
            return;
        }

        Object.entries(agentStatus).forEach(([agentName, info]) => {
            const agentItem = document.createElement('div');
            agentItem.className = 'flex items-center justify-between p-2 bg-gray-50 rounded';
            
            const statusColor = this.getAgentStatusColor(info.status);
            agentItem.innerHTML = `
                <div class="flex items-center">
                    <span class="w-2 h-2 rounded-full ${statusColor} mr-2"></span>
                    <span class="text-xs font-medium">${agentName}</span>
                </div>
                <div class="text-right">
                    <div class="text-xs text-gray-600">${info.status}</div>
                    ${info.task ? `<div class="text-xs text-gray-500 truncate max-w-20" title="${info.task}">${info.task}</div>` : ''}
                </div>
            `;
            container.appendChild(agentItem);
        });
    }

    updateSingleBlackboardAgent(agentName, status, task) {
        const container = document.getElementById('blackboard-agents');
        let agentItem = document.getElementById(`blackboard-agent-${agentName}`);
        
        if (!agentItem) {
            // 如果是第一次显示，清空初始状态
            if (container.children.length === 1 && container.children[0].innerHTML.includes('等待Agent启动')) {
                container.innerHTML = '';
            }
            
            agentItem = document.createElement('div');
            agentItem.id = `blackboard-agent-${agentName}`;
            agentItem.className = 'flex items-center justify-between p-2 bg-gray-50 rounded mb-1';
            container.appendChild(agentItem);
        }

        const statusColor = this.getAgentStatusColor(status);
        const agentSystem = agentStatus.agent_system || '';
        const systemIcon = agentSystem === '真正系统' ? '🤖' : '🔄';
        const progress = agentStatus.progress || 0;
        
        agentItem.innerHTML = `
            <div class="flex items-center">
                <span class="w-2 h-2 rounded-full ${statusColor} mr-2"></span>
                <span class="text-xs font-medium">${agentName}</span>
                ${agentSystem ? `<span class="ml-1 text-xs" title="${agentSystem}">${systemIcon}</span>` : ''}
            </div>
            <div class="text-right">
                <div class="text-xs text-gray-600">${status}</div>
                ${task ? `<div class="text-xs text-gray-500 truncate max-w-20" title="${task}">${task}</div>` : ''}
                ${progress > 0 && progress < 100 ? `<div class="text-xs text-blue-600">${progress.toFixed(0)}%</div>` : ''}
            </div>
        `;
    }

    getAgentStatusColor(status) {
        const statusColors = {
            'ready': 'bg-gray-400',
            'working': 'bg-yellow-400',
            'completed': 'bg-green-400',
            'error': 'bg-red-400',
            'waiting': 'bg-blue-400'
        };
        return statusColors[status] || 'bg-gray-400';
    }

    formatValue(value) {
        if (typeof value === 'string' && value.length > 50) {
            return value.substring(0, 50) + '...';
        }
        return String(value);
    }

    updateCurrentConfig(config) {
        const configElement = document.getElementById('current-config');
        if (configElement) {
            configElement.textContent = `${config.provider} - ${config.model}`;
        }
        this.addSystemLog(`配置已更新: ${config.provider} - ${config.model}`);
    }
    
    formatResearchResult(result) {
        if (!result) return '研究结果为空';
        
        // 动态获取研究主题
        let researchTopic = result.研究主题 || result.research_topic || result.query || '科研分析';
        let formatted = `# 🔬 深度研究报告：${researchTopic}\n\n`;
        
        // 执行概要
        if (result.执行概要) {
            formatted += `## 📊 执行概要\n`;
            formatted += `- **研究目标**: ${result.执行概要.研究目标 || '深度科研分析'}\n`;
            formatted += `- **研究方法**: ${result.执行概要.研究方法 || '多Agent协作分析'}\n`;
            formatted += `- **可靠性评估**: ${result.执行概要.可靠性评估 || '高'}\n`;
            formatted += `- **总处理时间**: ${result.执行概要.总处理时间 || result.processing_time || '60-120秒'}\n`;
            formatted += `- **研究深度**: ${result.执行概要.研究深度 || '深度专业分析'}\n\n`;
            
            if (result.执行概要.主要发现 && result.执行概要.主要发现.length > 0) {
                formatted += `### 🎯 主要发现\n`;
                result.执行概要.主要发现.forEach((finding, index) => {
                    formatted += `${index + 1}. ${finding}\n`;
                });
                formatted += `\n`;
            }
        }
        
        // 信息收集成果
        if (result.信息收集成果) {
            formatted += `## 📚 信息收集成果\n`;
            formatted += `- **文献数量**: ${result.信息收集成果.文献数量 || '30+篇'}\n`;
            formatted += `- **高质量论文**: ${result.信息收集成果.高质量论文 || '15+篇'}\n`;
            formatted += `- **研究质量**: ${result.信息收集成果.研究质量 || '高质量'}\n`;
            formatted += `- **领域专业度**: ${result.信息收集成果.领域专业度 || '专业深度研究'}\n`;
            
            if (result.信息收集成果.核心主题 && result.信息收集成果.核心主题.length > 0) {
                formatted += `- **核心主题**: ${result.信息收集成果.核心主题.join(', ')}\n`;
            } else if (result.信息收集成果.主要主题 && result.信息收集成果.主要主题.length > 0) {
                formatted += `- **主要主题**: ${result.信息收集成果.主要主题.join(', ')}\n`;
            }
            
            if (result.信息收集成果.研究空白 && result.信息收集成果.研究空白.length > 0) {
                formatted += `- **研究空白**: ${result.信息收集成果.研究空白.join(', ')}\n`;
            }
            
            if (result.信息收集成果.覆盖领域 && result.信息收集成果.覆盖领域.length > 0) {
                formatted += `- **覆盖领域**: ${result.信息收集成果.覆盖领域.join(', ')}\n`;
            }
            
            formatted += `\n`;
        }
        
        // 建模分析结果
        if (result.建模分析结果) {
            formatted += `## 🔧 建模分析结果\n`;
            formatted += `- **框架质量**: ${result.建模分析结果.框架质量 || '85%+'}\n`;
            formatted += `- **模型特征**: ${result.建模分析结果.模型特征 || '复杂'}\n`;
            formatted += `- **创新评分**: ${result.建模分析结果.创新评分 || '90%+'}\n`;
            formatted += `- **技术创新**: ${result.建模分析结果.技术创新 || '显著创新'}\n`;
            
            if (result.建模分析结果.核心发现 && result.建模分析结果.核心发现.length > 0) {
                formatted += `- **核心发现**: ${result.建模分析结果.核心发现.join(', ')}\n`;
            }
            
            if (result.建模分析结果.专业洞察) {
                formatted += `- **专业洞察**: ${result.建模分析结果.专业洞察}\n`;
            }
            
            formatted += `\n`;
        }
        
        // 验证评估报告
        if (result.验证评估报告) {
            formatted += `## ✅ 验证评估报告\n`;
            formatted += `- **可靠性等级**: ${result.验证评估报告.可靠性等级 || '高'}\n`;
            formatted += `- **验证状态**: ${result.验证评估报告.验证状态 || '验证通过'}\n`;
            formatted += `- **验证完整性**: ${result.验证评估报告.验证完整性 || '全面验证'}\n`;
            formatted += `- **专业领域**: ${result.验证评估报告.专业领域 || researchTopic}\n`;
            
            if (result.验证评估报告.主要风险 && result.验证评估报告.主要风险.length > 0) {
                formatted += `- **主要风险**: ${result.验证评估报告.主要风险.join(', ')}\n`;
            }
            
            if (result.验证评估报告.改进建议 && result.验证评估报告.改进建议.length > 0) {
                formatted += `\n### 📋 改进建议\n`;
                result.验证评估报告.改进建议.forEach((suggestion, index) => {
                    formatted += `${index + 1}. ${suggestion}\n`;
                });
            }
            
            formatted += `\n`;
        }
        
        // 协作统计
        if (result.协作统计) {
            formatted += `## 🤝 多Agent协作统计\n`;
            formatted += `- **参与Agent数量**: ${result.协作统计.参与Agent数量 || 4}\n`;
            formatted += `- **协作事件总数**: ${result.协作统计.协作事件总数 || '多次'}\n`;
            formatted += `- **思考步骤数量**: ${result.协作统计.思考步骤数量 || '30+'}\n`;
            formatted += `- **数据交换次数**: ${result.协作统计.数据交换次数 || '50+'}\n`;
            formatted += `- **任务完成率**: ${result.协作统计.任务完成率 || '100%'}\n`;
            formatted += `- **协作效率**: ${result.协作统计.协作效率 || '高效协作'}\n\n`;
                 }
         
         // 专业研究建议
         if (result.专业研究建议 && result.专业研究建议.length > 0) {
             formatted += `## 💡 专业研究建议\n`;
             result.专业研究建议.forEach((suggestion, index) => {
                 formatted += `${index + 1}. ${suggestion}\n`;
             });
             formatted += `\n`;
         }
         
         // 后续研究方向
         if (result.后续研究方向 && result.后续研究方向.length > 0) {
             formatted += `## 🚀 后续研究方向\n`;
             result.后续研究方向.forEach((direction, index) => {
                 formatted += `${index + 1}. ${direction}\n`;
             });
             formatted += `\n`;
         }
         
         // 研究建议（兼容性支持）
         if (result.研究建议 && result.研究建议.length > 0) {
             formatted += `## 💡 研究建议\n`;
             result.研究建议.forEach((suggestion, index) => {
                 formatted += `${index + 1}. ${suggestion}\n`;
             });
             formatted += `\n`;
         }
         
         return formatted;
    }

    // 新增的增强功能方法
    updatePerformanceMetrics(metrics) {
        // 更新性能指标显示
        const metricsContainer = document.getElementById('performance-metrics');
        if (metricsContainer) {
            metricsContainer.innerHTML = `
                <div class="text-xs text-gray-500 mb-2">黑板性能指标</div>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div>操作次数: ${metrics.operations_count || 0}</div>
                    <div>响应时间: ${(metrics.average_response_time || 0).toFixed(2)}s</div>
                    <div>并发Agent: ${metrics.peak_concurrent_agents || 0}</div>
                    <div>数据同步: 实时</div>
                </div>
            `;
        }
    }
    
    updateCollaborationStats(blackboardData) {
        // 更新协作统计
        const statsContainer = document.getElementById('collaboration-stats');
        if (statsContainer) {
            const activeAgents = Object.keys(blackboardData.agent_status || {}).length;
            const activeSessions = blackboardData.active_sessions || 0;
            const collaborationCount = blackboardData.collaboration_count || 0;
            
            statsContainer.innerHTML = `
                <div class="text-xs text-gray-500 mb-2">协作统计</div>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div>活跃Agent: ${activeAgents}</div>
                    <div>会话数: ${activeSessions}</div>
                    <div>协作事件: ${collaborationCount}</div>
                    <div>数据交换: ${(blackboardData.performance_metrics?.operations_count || 0)}次</div>
                </div>
            `;
        }
    }
    
    updateBlackboardEvents(events) {
        // 更新事件流显示
        const eventsContainer = document.getElementById('blackboard-events');
        if (!eventsContainer) return;
        
        eventsContainer.innerHTML = '';
        
        if (events.length === 0) {
            eventsContainer.innerHTML = '<div class="text-xs text-gray-500">暂无事件</div>';
            return;
        }
        
        events.slice(-10).forEach(event => {
            const eventItem = document.createElement('div');
            eventItem.className = 'mb-1 p-1 bg-gray-50 rounded text-xs';
            
            const time = new Date(event.timestamp).toLocaleTimeString();
            const typeColor = this.getEventTypeColor(event.type);
            
            eventItem.innerHTML = `
                <div class="flex justify-between">
                    <span class="${typeColor}">${event.type}</span>
                    <span class="text-gray-400">${time}</span>
                </div>
                <div class="text-gray-600">${event.agent || 'system'}: ${this.formatEventData(event.data)}</div>
            `;
            
            eventsContainer.appendChild(eventItem);
        });
        
        eventsContainer.scrollTop = eventsContainer.scrollHeight;
    }
    
    getEventTypeColor(type) {
        const colors = {
            'agent_status_change': 'text-blue-500',
            'thought_step': 'text-purple-500',
            'agent_collaboration': 'text-green-500',
            'data_updated': 'text-yellow-500',
            'task_progress': 'text-orange-500'
        };
        return colors[type] || 'text-gray-500';
    }
    
    formatEventData(data) {
        if (typeof data === 'string') {
            return data.length > 30 ? data.substring(0, 30) + '...' : data;
        }
        if (typeof data === 'object') {
            if (data.step) return data.step;
            if (data.message) return data.message;
            if (data.status) return `状态: ${data.status}`;
            return JSON.stringify(data).substring(0, 30) + '...';
        }
        return String(data);
    }
    
    // 思考链可视化
    updateThoughtChain(sessionId, thoughts) {
        const chainContainer = document.getElementById('thought-chain');
        if (!chainContainer) return;
        
        chainContainer.innerHTML = `
            <div class="text-xs text-gray-500 mb-2">思考链 (会话: ${sessionId.substring(0, 8)}...)</div>
        `;
        
        thoughts.forEach((thought, index) => {
            const thoughtItem = document.createElement('div');
            thoughtItem.className = 'mb-2 p-2 bg-gray-50 rounded border-l-2 border-purple-400';
            
            const time = new Date(thought.timestamp).toLocaleTimeString();
            const typeIcon = this.getThoughtTypeIcon(thought.type);
            
            thoughtItem.innerHTML = `
                <div class="flex justify-between items-start mb-1">
                    <div class="flex items-center">
                        <i class="${typeIcon} text-purple-500 mr-1"></i>
                        <span class="font-medium text-xs">${thought.agent}</span>
                    </div>
                    <span class="text-xs text-gray-400">${time}</span>
                </div>
                <div class="text-xs text-gray-700">${thought.step}</div>
                <div class="text-xs text-gray-500 mt-1">类型: ${thought.type}</div>
            `;
            
            chainContainer.appendChild(thoughtItem);
        });
        
        chainContainer.scrollTop = chainContainer.scrollHeight;
    }
    
    getThoughtTypeIcon(type) {
        const icons = {
            'thinking': 'fas fa-brain',
            'processing': 'fas fa-cog',
            'collaboration': 'fas fa-handshake',
            'completed': 'fas fa-check',
            'error': 'fas fa-exclamation-triangle'
        };
        return icons[type] || 'fas fa-circle';
    }
    
    // Agent进度更新方法
    updateAgentProgress(data) {
        const { agent, task, progress, session_id } = data;
        
        // 映射Agent名称到HTML ID
        const agentMapping = {
            'information_agent': 'information',
            'modeling_agent': 'modeling', 
            'verification_agent': 'verification',
            'report_agent': 'report'
        };
        
        const agentId = agentMapping[agent] || agent.replace('_', '-');
        
        // 更新进度条
        const progressBar = document.getElementById(`progress-${agentId}`);
        if (progressBar) {
            progressBar.style.width = `${Math.min(progress, 100)}%`;
        }
        
        // 更新任务描述
        const taskElement = document.getElementById(`task-${agentId}`);
        if (taskElement) {
            taskElement.textContent = `${task} (${Math.round(progress)}%)`;
        }
        
        // 更新状态标签
        const statusElement = document.getElementById(`status-${agentId}`);
        if (statusElement) {
            if (progress >= 100) {
                statusElement.textContent = '已完成';
                statusElement.className = 'text-xs px-2 py-1 bg-green-200 text-green-700 rounded';
            } else if (progress > 0) {
                statusElement.textContent = '工作中';
                statusElement.className = 'text-xs px-2 py-1 bg-blue-200 text-blue-700 rounded';
            } else {
                statusElement.textContent = '待机';
                statusElement.className = 'text-xs px-2 py-1 bg-gray-200 text-gray-600 rounded';
            }
        }
        
        // 添加到系统日志
        this.addSystemLog(`${agent}: ${task} (${progress.toFixed(1)}%)`);
        
        // 更新协作流程可视化
        let flowStatus = 'idle';
        if (progress >= 100) {
            flowStatus = 'completed';
        } else if (progress > 0) {
            flowStatus = 'working';
        }
        this.updateCollaborationFlow(agent, flowStatus);
        
        // 如果进度完成，添加完成动画效果
        if (progress >= 100) {
            const agentContainer = document.getElementById(`agent-${agentId}`);
            if (agentContainer) {
                agentContainer.classList.add('animate-pulse');
                setTimeout(() => {
                    agentContainer.classList.remove('animate-pulse');
                }, 2000);
            }
        }
        
        // 更新协作流程可视化
        this.updateCollaborationFlow(agent, status);
    }
    
    // 更新协作流程可视化
    updateCollaborationFlow(agent, status) {
        const agentMapping = {
            'information_agent': 'information',
            'modeling_agent': 'modeling', 
            'verification_agent': 'verification',
            'report_agent': 'report'
        };
        
        const agentId = agentMapping[agent] || agent.replace('_', '-');
        const flowElement = document.getElementById(`flow-${agentId}`);
        
        if (flowElement) {
            // 移除所有状态类
            flowElement.classList.remove('bg-blue-200', 'bg-green-200', 'bg-purple-200', 'bg-orange-200');
            flowElement.classList.remove('bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500');
            flowElement.classList.remove('animate-pulse', 'ring-2', 'ring-offset-1');
            
            // 根据状态添加相应的样式
            if (status === 'working' || status === 'processing') {
                // 工作中 - 高亮显示
                const colorMap = {
                    'information': 'bg-blue-500 ring-blue-300',
                    'modeling': 'bg-green-500 ring-green-300',
                    'verification': 'bg-purple-500 ring-purple-300',
                    'report': 'bg-orange-500 ring-orange-300'
                };
                flowElement.className = `w-8 h-8 ${colorMap[agentId] || 'bg-gray-500'} rounded-full flex items-center justify-center mb-1 transition-all duration-300 animate-pulse ring-2 ring-offset-1`;
            } else if (status === 'completed') {
                // 已完成 - 绿色检查标记
                flowElement.className = 'w-8 h-8 bg-green-500 rounded-full flex items-center justify-center mb-1 transition-all duration-300';
                flowElement.innerHTML = '<i class="fas fa-check text-white text-xs"></i>';
            } else {
                // 待机状态 - 默认颜色
                const colorMap = {
                    'information': 'bg-blue-200',
                    'modeling': 'bg-green-200',
                    'verification': 'bg-purple-200',
                    'report': 'bg-orange-200'
                };
                flowElement.className = `w-8 h-8 ${colorMap[agentId] || 'bg-gray-200'} rounded-full flex items-center justify-center mb-1 transition-all duration-300`;
                
                // 恢复原始图标
                const iconMap = {
                    'information': 'fas fa-search text-blue-600',
                    'modeling': 'fas fa-brain text-green-600',
                    'verification': 'fas fa-check-double text-purple-600',
                    'report': 'fas fa-file-alt text-orange-600'
                };
                flowElement.innerHTML = `<i class="${iconMap[agentId] || 'fas fa-circle'} text-xs"></i>`;
            }
        }
        
        // 更新连接箭头
        this.updateFlowArrows(agentId, status);
    }
    
    // 更新流程箭头
    updateFlowArrows(currentAgent, status) {
        const agentOrder = ['information', 'modeling', 'verification', 'report'];
        const currentIndex = agentOrder.indexOf(currentAgent);
        
        if (currentIndex === -1) return;
        
        // 如果当前Agent正在工作或已完成，激活到当前Agent的所有箭头
        if (status === 'working' || status === 'completed') {
            for (let i = 1; i <= currentIndex + 1; i++) {
                const arrow = document.getElementById(`arrow-${i}`);
                if (arrow) {
                    arrow.classList.remove('bg-gray-300');
                    arrow.classList.add('bg-indigo-500');
                }
            }
        }
        
        // 如果当前Agent已完成，激活下一个箭头
        if (status === 'completed' && currentIndex < agentOrder.length - 1) {
            const nextArrow = document.getElementById(`arrow-${currentIndex + 2}`);
            if (nextArrow) {
                nextArrow.classList.add('animate-pulse');
                setTimeout(() => {
                    nextArrow.classList.remove('animate-pulse');
                }, 3000);
            }
        }
    }
    
    // 添加思考步骤
    addThoughtStep(sessionId, thoughtData) {
        const chainContainer = document.getElementById('thought-chain');
        if (!chainContainer) return;
        
        // 如果是第一个思考步骤，清空初始状态
        const emptyState = chainContainer.querySelector('.text-center');
        if (emptyState) {
            chainContainer.innerHTML = `
                <div class="text-xs text-gray-500 mb-2">思考链 (会话: ${sessionId.substring(0, 8)}...)</div>
            `;
        }
        
        const thoughtItem = document.createElement('div');
        thoughtItem.className = 'mb-1 p-2 bg-white rounded border-l-2 border-purple-400';
        
        const time = new Date().toLocaleTimeString();
        const typeIcon = this.getThoughtTypeIcon(thoughtData.type || 'thinking');
        
        thoughtItem.innerHTML = `
            <div class="flex justify-between items-start mb-1">
                <div class="flex items-center">
                    <i class="${typeIcon} text-purple-500 mr-1"></i>
                    <span class="font-medium text-xs">${thoughtData.agent}</span>
                </div>
                <span class="text-xs text-gray-400">${time}</span>
            </div>
            <div class="text-xs text-gray-700">${thoughtData.step}</div>
            <div class="text-xs text-gray-500 mt-1">类型: ${thoughtData.type || 'thinking'}</div>
        `;
        
        chainContainer.appendChild(thoughtItem);
        chainContainer.scrollTop = chainContainer.scrollHeight;
    }

    // 启动时订阅黑板状态
    subscribeToBlackboard() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'subscribe_blackboard'
            }));
        }
    }
    
    // 系统类型指示器 - 纯真实Agent系统版本
    updateSystemTypeIndicator() {
        const indicator = document.getElementById('system-type-indicator');
        if (indicator) {
            indicator.className = 'badge badge-success';
            indicator.textContent = '真实Agent系统';
            indicator.title = '当前使用真实的多Agent协作系统，具备完整的智能协作能力';
        }
        
        // 更新状态面板中的系统类型
        const systemTypeElement = document.getElementById('current-system-type');
        if (systemTypeElement) {
            systemTypeElement.textContent = '真实Agent系统';
            systemTypeElement.className = 'text-green-600 font-semibold';
        }
    }

    // 系统监控相关方法
    async updateSystemMonitor() {
        // 仅在需要时更新监控数据
        if (!this.isActiveSession() && this.connectionHealth === 'good') {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiEndpoint}/api/v1/system/monitor`);
            const result = await response.json();
            
            if (result.success) {
                const data = result.data;
                
                // 更新系统健康状态
                this.updateHealthStatus(data.system_health);
                
                // 更新系统资源
                if (data.system_resources && !data.system_resources.note) {
                    this.updateSystemResources(data.system_resources);
                }
                
                // 更新统计信息
                this.updateSystemStats(data);
                
                // 更新时间戳
                const timestamp = new Date(data.timestamp).toLocaleTimeString();
                const timestampElement = document.getElementById('monitor-timestamp');
                if (timestampElement) {
                    timestampElement.textContent = timestamp;
                }
            }
        } catch (error) {
            console.error('系统监控更新失败:', error);
            // 监控失败不影响主要功能，只记录错误
        }
    }
    
    updateHealthStatus(healthData) {
        const indicator = document.getElementById('health-indicator');
        const status = document.getElementById('health-status');
        const score = document.getElementById('health-score');
        
        if (indicator && status && score) {
            score.textContent = `(${healthData.score}%)`;
            
            // 根据健康分数设置颜色和状态
            if (healthData.status === 'excellent') {
                indicator.className = 'w-2 h-2 bg-green-500 rounded-full mr-1';
                status.textContent = '优秀';
                status.className = 'text-xs font-medium text-green-600';
            } else if (healthData.status === 'good') {
                indicator.className = 'w-2 h-2 bg-blue-500 rounded-full mr-1';
                status.textContent = '良好';
                status.className = 'text-xs font-medium text-blue-600';
            } else if (healthData.status === 'warning') {
                indicator.className = 'w-2 h-2 bg-yellow-500 rounded-full mr-1';
                status.textContent = '警告';
                status.className = 'text-xs font-medium text-yellow-600';
            } else if (healthData.status === 'critical') {
                indicator.className = 'w-2 h-2 bg-red-500 rounded-full mr-1';
                status.textContent = '严重';
                status.className = 'text-xs font-medium text-red-600';
            }
        }
    }
    
    updateSystemResources(resources) {
        // 更新CPU使用率
        const cpuPercent = document.getElementById('cpu-percent');
        const cpuBar = document.getElementById('cpu-bar');
        if (cpuPercent && cpuBar) {
            cpuPercent.textContent = `${resources.cpu_percent}%`;
            cpuBar.style.width = `${Math.min(resources.cpu_percent, 100)}%`;
            
            // 根据CPU使用率调整颜色
            if (resources.cpu_percent > 80) {
                cpuBar.className = 'bg-red-500 h-1 rounded-full transition-all duration-300';
            } else if (resources.cpu_percent > 60) {
                cpuBar.className = 'bg-yellow-500 h-1 rounded-full transition-all duration-300';
            } else {
                cpuBar.className = 'bg-blue-500 h-1 rounded-full transition-all duration-300';
            }
        }
        
        // 更新内存使用率
        const memoryPercent = document.getElementById('memory-percent');
        const memoryBar = document.getElementById('memory-bar');
        if (memoryPercent && memoryBar) {
            memoryPercent.textContent = `${resources.memory_percent}%`;
            memoryBar.style.width = `${Math.min(resources.memory_percent, 100)}%`;
            
            // 根据内存使用率调整颜色
            if (resources.memory_percent > 85) {
                memoryBar.className = 'bg-red-500 h-1 rounded-full transition-all duration-300';
            } else if (resources.memory_percent > 70) {
                memoryBar.className = 'bg-yellow-500 h-1 rounded-full transition-all duration-300';
            } else {
                memoryBar.className = 'bg-orange-500 h-1 rounded-full transition-all duration-300';
            }
        }
    }
    
    updateSystemStats(data) {
        // 更新WebSocket连接数
        const websocketConnections = document.getElementById('websocket-connections');
        if (websocketConnections && data.websocket_statistics) {
            websocketConnections.textContent = data.websocket_statistics.active_connections;
        }
        
        // 更新活跃会话数
        const activeSessions = document.getElementById('active-sessions');
        if (activeSessions && data.blackboard_statistics) {
            activeSessions.textContent = data.blackboard_statistics.active_sessions;
        }
    }
    
    // 启动系统监控定时器
    startSystemMonitoring() {
        // 立即执行一次
        this.updateSystemMonitor();
        
        // 每5秒更新一次
        setInterval(() => {
            this.updateSystemMonitor();
        }, 5000);
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    // 加载保存的设置
    const savedSettings = localStorage.getItem('research-system-settings');
    if (savedSettings) {
        const settings = JSON.parse(savedSettings);
        document.getElementById('api-endpoint').value = settings.apiEndpoint || 'http://localhost:8000';
        document.getElementById('ws-endpoint').value = settings.wsEndpoint || 'ws://localhost:8000/ws';
        document.getElementById('refresh-interval').value = (settings.refreshInterval || 5000) / 1000;
    }
    
    // 初始化应用
    window.researchApp = new ResearchSystemApp();
    
    // 初始化会话管理（延迟执行以确保DOM完全加载）
    setTimeout(() => {
        initSessionManager();
        modifySubmitResearchForSession();
    }, 500);
    
    // 启动系统监控
    window.researchApp.startSystemMonitoring();
    
    // 启动连接健康检查
    window.researchApp.startConnectionHealthCheck();
});

// 在ResearchSystemApp类中添加错误提示方法
ResearchSystemApp.prototype.showErrorToast = function(message) {
    // 创建错误提示
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-sm';
    toast.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-exclamation-triangle mr-2"></i>
            <span>${message}</span>
            <button class="ml-2 text-white hover:text-gray-200" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // 5秒后自动移除
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
};

ResearchSystemApp.prototype.showSuccessToast = function(message) {
    // 创建成功提示
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-sm';
    toast.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-check-circle mr-2"></i>
            <span>${message}</span>
            <button class="ml-2 text-white hover:text-gray-200" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
};

// 增强的连接健康检查
ResearchSystemApp.prototype.startConnectionHealthCheck = function() {
    setInterval(() => {
        if (this.isConnected && this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.sendPing();
        } else if (this.websocket && this.websocket.readyState === WebSocket.CLOSED) {
            console.log('🔄 检测到WebSocket已关闭，尝试重连...');
            this.addSystemLog('🔄 连接已断开，正在重连...');
            this.connectWebSocket();
        }
    }, 30000); // 每30秒检查一次
};

// 导出全局函数供调试使用
window.ResearchSystemApp = ResearchSystemApp; 

// === 会话管理功能 ===
let currentSessionId = null;
const sessions = new Map();

// 初始化会话管理界面
function initSessionManager() {
    const sessionPanel = document.createElement('div');
    sessionPanel.className = 'session-panel';
    sessionPanel.innerHTML = `
        <div class="session-header">
            <h3>📋 研究会话</h3>
            <button id="newSessionBtn" class="btn btn-primary">新建会话</button>
        </div>
        <div class="session-controls">
            <select id="sessionSelect" class="form-control">
                <option value="">选择会话...</option>
            </select>
            <button id="refreshSessionsBtn" class="btn btn-secondary">刷新</button>
        </div>
        <div id="sessionInfo" class="session-info"></div>
    `;
    
    document.querySelector('.container').insertBefore(sessionPanel, document.querySelector('#systemStatus'));
    
    // 绑定事件
    document.getElementById('newSessionBtn').addEventListener('click', showNewSessionDialog);
    document.getElementById('refreshSessionsBtn').addEventListener('click', loadSessions);
    document.getElementById('sessionSelect').addEventListener('change', handleSessionSelect);
    
    // 初始加载会话列表
    loadSessions();
}

// 创建新会话对话框
function showNewSessionDialog() {
    const dialog = document.createElement('div');
    dialog.className = 'modal-overlay';
    dialog.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h4>创建新研究会话</h4>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <form id="newSessionForm">
                    <div class="form-group">
                        <label for="sessionTitle">会话标题：</label>
                        <input type="text" id="sessionTitle" class="form-control" 
                               placeholder="例如：质子导体材料研究" required>
                    </div>
                    <div class="form-group">
                        <label for="sessionDesc">会话描述：</label>
                        <textarea id="sessionDesc" class="form-control" rows="3"
                                  placeholder="简要描述这个研究会话的目标和内容..."></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="createNewSession()">创建</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(dialog);
    
    // 绑定关闭事件
    dialog.querySelector('.modal-close').addEventListener('click', () => {
        document.body.removeChild(dialog);
    });
    
    // 点击遮罩关闭
    dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
            document.body.removeChild(dialog);
        }
    });
}

// 创建新会话
async function createNewSession() {
    const title = document.getElementById('sessionTitle').value.trim();
    const description = document.getElementById('sessionDesc').value.trim();
    
    if (!title) {
        alert('请输入会话标题');
        return;
    }
    
    try {
        const response = await fetch('/api/v1/sessions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                title: title,
                description: description
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            const sessionInfo = result.session;
            
            // 添加到会话列表
            sessions.set(sessionInfo.id, sessionInfo);
            
            // 更新下拉列表
            const sessionSelect = document.getElementById('sessionSelect');
            const option = document.createElement('option');
            option.value = sessionInfo.id;
            option.textContent = `${sessionInfo.title} (${new Date(sessionInfo.created_at).toLocaleDateString()})`;
            sessionSelect.appendChild(option);
            
            // 设置为当前会话
            sessionSelect.value = sessionInfo.id;
            currentSessionId = sessionInfo.id;
            updateSessionInfo(sessionInfo);
            
            // 关闭对话框
            closeModal();
            
            showNotification('成功创建新研究会话', 'success');
        } else {
            const error = await response.json();
            alert(`创建会话失败: ${error.detail}`);
        }
    } catch (error) {
        console.error('创建会话失败:', error);
        alert('创建会话失败，请检查网络连接');
    }
}

// 加载会话列表
async function loadSessions() {
    try {
        const response = await fetch('/api/v1/sessions');
        if (response.ok) {
            const result = await response.json();
            const sessionList = result.sessions;
            
            // 清空并重新填充会话列表
            sessions.clear();
            const sessionSelect = document.getElementById('sessionSelect');
            sessionSelect.innerHTML = '<option value="">选择会话...</option>';
            
            sessionList.forEach(session => {
                sessions.set(session.id, session);
                
                const option = document.createElement('option');
                option.value = session.id;
                option.textContent = `${session.title} (${new Date(session.created_at).toLocaleDateString()})`;
                sessionSelect.appendChild(option);
            });
            
            if (sessionList.length > 0) {
                showNotification(`加载了 ${sessionList.length} 个研究会话`, 'info');
            }
        } else {
            console.error('加载会话列表失败');
        }
    } catch (error) {
        console.error('加载会话列表失败:', error);
    }
}

// 处理会话选择
async function handleSessionSelect(event) {
    const sessionId = event.target.value;
    
    if (!sessionId) {
        currentSessionId = null;
        document.getElementById('sessionInfo').innerHTML = '';
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/sessions/${sessionId}`);
        if (response.ok) {
            const result = await response.json();
            const sessionInfo = result.session;
            const tasks = result.tasks;
            
            currentSessionId = sessionId;
            updateSessionInfo(sessionInfo, tasks);
            
            showNotification(`切换到会话: ${sessionInfo.title}`, 'info');
        } else {
            console.error('获取会话详情失败');
        }
    } catch (error) {
        console.error('获取会话详情失败:', error);
    }
}

// 更新会话信息显示
function updateSessionInfo(sessionInfo, tasks = []) {
    const sessionInfoDiv = document.getElementById('sessionInfo');
    const createdAt = new Date(sessionInfo.created_at).toLocaleString();
    
    let tasksHtml = '';
    if (tasks.length > 0) {
        tasksHtml = `
            <div class="session-tasks">
                <h5>历史任务 (${tasks.length})</h5>
                <div class="task-list">
                    ${tasks.slice(-3).map(task => `
                        <div class="task-item">
                            <span class="task-type">${task.agent_type}</span>
                            <span class="task-time">${new Date(task.created_at).toLocaleString()}</span>
                            <div class="task-query">${task.task_data.query || '未知任务'}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    sessionInfoDiv.innerHTML = `
        <div class="session-details">
            <h4>${sessionInfo.title}</h4>
            <p class="session-desc">${sessionInfo.description || '无描述'}</p>
            <div class="session-meta">
                <span class="session-status status-${sessionInfo.status}">${sessionInfo.status}</span>
                <span class="session-created">创建于: ${createdAt}</span>
            </div>
            ${tasksHtml}
        </div>
    `;
}

// 关闭模态框
function closeModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
        document.body.removeChild(modal);
    }
}

// 修改现有的提交研究函数以支持会话
function modifySubmitResearchForSession() {
    const originalSubmitResearch = window.submitResearch;
    
    window.submitResearch = async function() {
        const query = document.getElementById('researchQuery').value.trim();
        if (!query) {
            alert('请输入研究问题');
            return;
        }
        
        // 如果有活跃会话，使用会话API
        if (currentSessionId) {
            try {
                const response = await fetch(`/api/v1/sessions/${currentSessionId}/research`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        query: query,
                        priority: 'normal',
                        collaboration_mode: 'balanced'
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    showNotification(`研究任务已提交到会话: ${sessions.get(currentSessionId).title}`, 'success');
                    
                    // 刷新会话信息
                    handleSessionSelect({ target: { value: currentSessionId } });
                } else {
                    const error = await response.json();
                    alert(`提交失败: ${error.detail}`);
                }
            } catch (error) {
                console.error('提交研究失败:', error);
                alert('提交失败，请检查网络连接');
            }
        } else {
            // 没有活跃会话，使用原有的提交方法
            await originalSubmitResearch();
        }
    };
}