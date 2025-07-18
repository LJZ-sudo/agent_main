# 科研创意多Agent智能协同系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20API-orange.svg)](https://platform.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 系统概述

基于多Agent协作的科研创意系统，采用**事件驱动黑板架构**和**链式思维推理**，为科研工作者提供智能化的创新方案设计和实验规划支持。系统整合了8个专业Agent，支持**慢思考**、**黑板机制**、**推理链记录**和**协同反馈**，产出带有评分排序的高质量科研创意方案。

### ✨ 核心特性

- **🧠 事件驱动黑板系统**：完整的发布/订阅机制，支持Agent间异步协作
- **🔗 推理链记录**：Chain-of-Thought思维过程全程记录和回溯
- **🔬 实验设计与评估**：10步骤实验设计流程，包含可行性和安全性分析
- **🎯 智能RAG功能**：增强检索生成，支持知识图谱构建和语义理解
- **📊 AI评估与优化**：多维度Agent性能评估和自我改进机制
- **🤖 8个专业Agent**：分工明确的智能体协同工作
- **🌐 真实API集成**：DeepSeek LLM + 学术数据库连接
- **⚡ 高性能架构**：异步处理、并发任务管理、容错机制

## 📁 项目结构

```
agent_main/
├── 📂 backend/                 # 后端服务核心
│   ├── 📂 agents/             # 8个专业Agent系统
│   │   ├── main_agent.py      # 主协调Agent（任务分解、推理链管理）
│   │   ├── information_agent.py  # 信息获取Agent（RAG、知识图谱）
│   │   ├── experiment_design_agent.py # 实验设计Agent（10步设计流程）
│   │   ├── evaluation_agent.py # 评估Agent（多维评估、性能监控）
│   │   ├── critique_agent.py   # 批判Agent（质量评估、改进建议）
│   │   ├── verification_agent.py # 验证Agent（事实核查、一致性）
│   │   ├── modeling_agent.py   # 建模Agent（科学计算、模拟）
│   │   └── report_agent.py     # 报告Agent（结构化输出）
│   ├── 📂 core/               # 核心系统组件
│   │   ├── blackboard.py      # 事件驱动黑板系统
│   │   ├── scheduler.py       # 智能任务调度器
│   │   ├── collaboration_manager.py # 协作管理器
│   │   ├── base_agent.py      # Agent基类和接口
│   │   ├── llm_client.py      # DeepSeek LLM客户端
│   │   └── agent_manager.py   # Agent生命周期管理
│   ├── 📂 utils/              # 专业工具模块
│   │   └── literature_search.py # 智能文献搜索
│   └── config_clean.py        # 系统配置管理
├── 📂 frontend/               # 现代Web界面
│   ├── 📂 js/                 # JavaScript交互逻辑
│   ├── 📂 css/                # 响应式样式设计
│   └── index.html             # 主用户界面
├── 📂 docs/                   # 完整技术文档
│   ├── 科研创意系统技术架构与模块设计.txt        # 核心架构设计文档
│   ├── 科研创意多Agent系统技术架构与模块设计白皮书 V1.0.pdf # 技术白皮书
│   ├── 科研创意多Agent系统核心模块技术方案.txt     # 核心模块方案
│   ├── 文献调研分析Agent技术方案 V1.0.pdf        # 文献调研方案
│   ├── 批判Agent与报告生成Agent实现方案（面向Cursor开发）.txt # 批判Agent方案
│   ├── 科研多Agent系统开发指导方案.txt           # 开发指导手册
│   ├── 科研多Agent系统"主Agent"和"验证Agent"实现方案.txt # 主Agent方案
│   ├── 科研多Agent系统代码实现分析与改进建议.txt    # 代码分析报告
│   ├── 项目全面分析与最终优化报告.md             # 项目优化报告
│   └── requirements.txt                      # 项目依赖说明
├── 📂 utils/                  # 高级工具函数
│   ├── academic_database_connector.py # 学术数据库集成
│   └── literature_quality_evaluator.py # 文献质量智能评估
├── orchestrator.py            # 系统编排调度器
├── 真实Agent智能服务器.py       # 主服务器入口
├── 启动完整系统.ps1           # 一键启动脚本
└── requirements.txt           # Python环境依赖
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **内存**: 建议4GB+（支持并发Agent处理）
- **存储**: 建议2GB+（推理链记录和知识缓存）
- **网络**: 稳定网络连接（LLM API + 学术数据库）

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository_url>
   cd agent_main
   ```

2. **安装Python依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置API密钥**
   ```python
   # 编辑 backend/config_clean.py
   DEEPSEEK_API_KEY = "your_deepseek_api_key"
   DEFAULT_MODEL = "deepseek-chat"
   ```

4. **启动系统**
   ```powershell
   # Windows PowerShell（推荐）
   .\启动完整系统.ps1
   
   # 或直接运行
   python "真实Agent智能服务器.py"
   ```

### 系统访问

- **🌐 Web界面**: http://localhost:8000
- **📖 API文档**: http://localhost:8000/docs  
- **📊 系统状态**: http://localhost:8000/api/v1/status
- **🔍 实时监控**: WebSocket连接实时Agent状态

## 🎮 使用指南

### Web界面操作

1. **提交科研问题**：在主界面输入研究问题或创意需求
2. **实时监控**：观察8个Agent的协作过程和推理链
3. **查看结果**：获取评分排序的创意方案列表
4. **系统监控**：实时Agent状态、性能指标、推理步骤

### API接口使用

```python
import requests
import asyncio

# 提交科研创意请求
response = requests.post("http://localhost:8000/api/v1/research/submit", 
    json={
        "query": "设计一种提高锂电池能量密度的创新方案",
        "priority": "high",
        "require_experiment_design": True,
        "enable_critique": True
    }
)

# 获取推理链记录
reasoning_chain = requests.get(f"http://localhost:8000/api/v1/research/{session_id}/reasoning")

# 实时系统状态
status = requests.get("http://localhost:8000/api/v1/status")
```

## 🏗️ 系统架构详解

### 🧠 事件驱动黑板系统

**核心机制**：
- **事件类型**：TASK_CREATED、INFORMATION_UPDATE、EXPERIMENT_DESIGNED、CRITIQUE_PUBLISHED等
- **发布/订阅**：Agent按兴趣订阅事件，异步响应处理
- **推理链记录**：每个推理步骤自动记录，包含step_id、agent_id、reasoning_text、confidence等
- **会话管理**：支持多用户并发，独立session管理

### 🤖 8个专业Agent详解

1. **主Agent (MainAgent)**
   - **核心职责**：任务分解、Agent协调、推理链管理
   - **增强功能**：
     - 深度LLM任务分析（复杂度评估、需求解析）
     - 动态执行策略调整
     - 质量控制检查点
     - 智能Agent选择和调度

2. **信息获取Agent (InformationAgent)**
   - **核心职责**：智能文献调研、知识图谱构建
   - **RAG增强**：
     - 3种调研方法：关键词驱动、主题建模、混合模式
     - 语义相关性计算和查询优化
     - 知识图谱节点关系挖掘
     - 智能问答系统构建

3. **实验设计Agent (ExperimentDesignAgent)**
   - **核心职责**：完整实验方案设计
   - **10步设计流程**：
     - 需求分析 → 假设构建 → 变量设计 → 实验流程
     - 材料设备 → 数据采集 → 统计分析 → 可行性评估
     - 安全评估 → 方案优化
   - **增强功能**：安全性分析、资源评估、风险识别

4. **评估Agent (EvaluationAgent)**
   - **核心职责**：全方位系统评估和优化建议
   - **评估维度**：
     - Agent个体性能（响应时间、准确性、创新度）
     - 系统协作质量（协调效率、信息流转）
     - 输出质量评估（方案可行性、创新性、完整性）
   - **自优化机制**：动态Prompt调整、策略优化建议

5. **批判Agent (CritiqueAgent)**
   - **核心职责**：质量审查、改进建议、风险识别
   - **增强功能**：
     - 多角度批判分析（可行性、安全性、创新性）
     - 冲突检测和解决建议
     - 方案优化指导

6. **验证Agent (VerificationAgent)**
   - **核心职责**：事实核查、逻辑一致性验证
   - **验证策略**：交叉验证、权威性检查、逻辑推理验证

7. **建模Agent (ModelingAgent)**
   - **核心职责**：科学计算、数据分析、模型构建
   - **支持功能**：统计分析、趋势预测、相关性分析

8. **报告Agent (ReportAgent)**
   - **核心职责**：结构化报告生成、可视化展示
   - **输出格式**：评分排序方案列表、详细分析报告、图表可视化

### ⚡ 技术架构特性

- **异步事件处理**：基于asyncio的高并发事件处理
- **推理链管理**：完整的思维过程记录和回溯
- **智能调度**：动态负载均衡、优先级队列管理
- **容错机制**：异常恢复、超时处理、错误隔离
- **性能监控**：实时性能指标、Agent健康检查

## 🔬 支持的功能特性

### 学术数据库集成
- **PubMed**: 生物医学文献检索
- **arXiv**: 预印本论文获取  
- **IEEE Xplore**: 工程技术文献
- **Semantic Scholar**: 计算机科学文献
- **CrossRef**: 跨领域学术资源

### RAG增强功能
- **语义搜索**：基于向量的语义相似度匹配
- **知识图谱**：实体关系挖掘和图谱构建
- **智能问答**：基于检索的问答系统
- **上下文增强**：动态上下文窗口管理

## 📊 系统监控与评估

### 实时监控面板
- **Agent状态监控**：实时任务状态、响应时间、成功率
- **推理链可视化**：思维过程步骤展示、置信度跟踪
- **系统性能指标**：CPU、内存、API调用统计
- **错误监控**：异常追踪、错误恢复状态

### 评估机制
- **多维度评估**：准确性、效率、创新性、协作度
- **质量评分**：0-10分量化评估，置信度标注
- **自优化反馈**：基于评估结果的系统改进建议

## 🔧 配置与定制

### 主要配置文件

**backend/config_clean.py**
```python
# LLM配置
DEEPSEEK_API_KEY = "your_api_key_here"
DEFAULT_MODEL = "deepseek-chat"
MAX_TOKENS = 4000
TEMPERATURE = 0.7

# 系统设置
MAX_CONCURRENT_TASKS = 10
AGENT_TIMEOUT = 300
REASONING_CHAIN_MAX_STEPS = 50

# 评估设置
EVALUATION_ENABLED = True
AUTO_OPTIMIZATION = True
PERFORMANCE_THRESHOLD = 0.8
```

### Agent定制化
- **模块化设计**：支持新Agent类型扩展
- **配置驱动**：通过配置文件调整Agent行为
- **接口标准化**：统一的Agent接口协议
- **插件机制**：热插拔Agent模块

## 🔄 开发与部署

### 开发环境搭建
```bash
# 开发模式启动
python "真实Agent智能服务器.py" --debug --reload

# 测试Agent协作
python -m pytest tests/ -v

# 代码质量检查
pylint backend/ --rcfile=.pylintrc
```

### 生产部署
```bash
# Docker容器化部署
docker build -t agent-system .
docker run -p 8000:8000 agent-system

# 集群模式部署
kubectl apply -f k8s-deployment.yaml
```

## 🤝 贡献指南

### 开发流程
1. **Fork项目** → 创建特性分支
2. **开发测试** → 确保测试覆盖率 > 80%
3. **提交PR** → 遵循代码规范和文档要求
4. **代码审查** → 通过CI/CD检查
5. **合并部署** → 更新CHANGELOG

### 代码规范
- **PEP8兼容**：使用black自动格式化
- **类型注解**：完整的typing支持
- **文档字符串**：详细的API文档
- **单元测试**：高覆盖率测试用例

## 📚 技术文档

- **[系统架构设计](docs/科研创意系统技术架构与模块设计.txt)**
- **[项目分析报告](docs/项目全面分析与最终优化报告.md)**
- **[API接口文档](http://localhost:8000/docs)**
- **[部署运维指南](docs/deployment_guide.md)**

## 📈 系统性能

- **并发处理能力**：支持10+并发研究请求
- **响应时间**：平均30-60秒完成复杂科研分析
- **准确性**：基于LLM的高质量推理，置信度 > 0.8
- **可扩展性**：模块化架构，支持水平扩展

## 🎖️ 系统亮点

✅ **完整的事件驱动架构** - 真正的异步Agent协作  
✅ **推理链全程记录** - 可追溯的思维过程  
✅ **10步实验设计流程** - 专业的实验规划  
✅ **智能RAG系统** - 增强的检索生成能力  
✅ **多维度评估机制** - 系统自我优化  
✅ **8个专业Agent** - 分工明确的智能协作  
✅ **真实API集成** - DeepSeek + 学术数据库  
✅ **现代Web界面** - 直观的可视化展示  

---

**系统版本**: v2.0.0 | **最后更新**: 2024年 | **技术栈**: Python + FastAPI + DeepSeek API + HTML5/JS
