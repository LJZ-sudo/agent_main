        socket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocket 消息:', data);
                
                switch(data.type) {
                    case 'agent_status':
                        updateAgentStatus(data.data);
                        break;
                    case 'chain_of_thought':
                        updateChainOfThought(data.data);
                        break;
                    case 'blackboard_update':
                        updateBlackboard(data.data);
                        break;
                    case 'research_result':
                        displayResearchResult(data);
                        break;
                    case 'research_submitted':
                        displayMessage('研究请求已提交，Agent团队开始协作...', 'success');
                        showSection('monitoring-section');
                        break;
                    case 'research_started':
                        displayMessage(data.message || '多Agent协作研究已开始', 'info');
                        break;
                    case 'agent_progress':
                        updateAgentProgress(data);
                        break;
                    case 'thought_step':
                        updateThoughtChain(data);
                        break;
                    case 'research_completed':
                        handleResearchCompleted(data);
                        break;
                    case 'research_error':
                        displayMessage(`研究过程遇到错误: ${data.error}`, 'error');
                        break;
                    default:
                        console.log('未处理的消息类型:', data.type);
                }
            } catch (error) {
                console.error('WebSocket 消息解析错误:', error);
            }
        };
        
        // 更新Agent进度
        function updateAgentProgress(data) {
            const progressBar = document.querySelector(`#progress-${data.agent.replace('_', '-')}`);
            if (progressBar) {
                progressBar.style.width = `${data.progress}%`;
                progressBar.setAttribute('aria-valuenow', data.progress);
                
                const progressText = progressBar.parentElement.querySelector('.progress-text');
                if (progressText) {
                    progressText.textContent = `${data.task} (${Math.round(data.progress)}%)`;
                }
            }
            
            // 更新状态显示
            const statusElement = document.querySelector(`#status-${data.agent.replace('_', '-')}`);
            if (statusElement) {
                statusElement.textContent = data.task;
                statusElement.className = 'badge badge-primary';
            }
        }
        
        // 处理研究完成
        function handleResearchCompleted(data) {
            displayMessage('🎉 多Agent协作研究已完成！', 'success');
            
            // 显示最终报告
            displayResearchResult({
                type: 'research_result',
                session_id: data.session_id,
                data: {
                    final_report: JSON.stringify(data.result, null, 2),
                    processing_time: data.processing_time,
                    blackboard_summary: data.blackboard_status
                }
            });
            
            // 更新所有Agent状态为完成
            const agents = ['information-agent', 'modeling-agent', 'verification-agent', 'report-agent'];
            agents.forEach(agent => {
                const progressBar = document.querySelector(`#progress-${agent}`);
                if (progressBar) {
                    progressBar.style.width = '100%';
                    progressBar.className = 'progress-bar bg-success';
                }
                
                const statusElement = document.querySelector(`#status-${agent}`);
                if (statusElement) {
                    statusElement.textContent = '已完成';
                    statusElement.className = 'badge badge-success';
                }
            });
            
            // 显示思考链和协作事件
            if (data.thought_chain && data.thought_chain.length > 0) {
                updateThoughtChainDisplay(data.thought_chain);
            }
            
            // 更新性能指标
            if (data.blackboard_status) {
                updatePerformanceMetrics(data.blackboard_status.performance_metrics);
                updateCollaborationStats(data.blackboard_status);
            }
        }
        
        // 更新思考链显示
        function updateThoughtChainDisplay(thoughts) {
            const thoughtChainContainer = document.getElementById('thought-chain-container');
            if (!thoughtChainContainer) return;
            
            thoughts.forEach(thought => {
                const thoughtElement = document.createElement('div');
                thoughtElement.className = `thought-step ${thought.step_type}`;
                
                const icon = getThoughtIcon(thought.step_type);
                const timestamp = new Date(thought.timestamp).toLocaleTimeString();
                
                thoughtElement.innerHTML = `
                    <div class="thought-header">
                        <span class="thought-icon">${icon}</span>
                        <span class="thought-agent">${thought.agent}</span>
                        <span class="thought-timestamp">${timestamp}</span>
                    </div>
                    <div class="thought-content">${thought.step}</div>
                `;
                
                thoughtChainContainer.appendChild(thoughtElement);
            });
            
            // 滚动到底部
            thoughtChainContainer.scrollTop = thoughtChainContainer.scrollHeight;
        }
        
        // 获取思考步骤图标
        function getThoughtIcon(stepType) {
            const icons = {
                'task_received': '📝',
                'processing': '⚙️',
                'completed': '✅',
                'collaboration_start': '🤝',
                'data_analysis': '📊',
                'modeling': '🔬',
                'verification': '🔍',
                'reporting': '📄',
                'integration_start': '🔧',
                'data_integration': '🔄',
                'task_completed': '🎯',
                'error': '❌',
                'thinking': '💭'
            };
            return icons[stepType] || '💭';
        } 