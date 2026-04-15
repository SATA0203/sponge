# Sponge Frontend - 多智能体协作系统前端界面

[English](#english) | [中文](#中文)

## 📋 概述

`frontend/` 目录包含 Sponge 多智能体协作系统的用户界面，基于 **Streamlit** 构建，提供直观的任务管理、智能体监控和工作流可视化功能。

## ✨ 主要功能

- 🎯 **任务创建与管理**: 创建新任务、查看进度、管理历史记录
- 🤖 **智能体监控**: 实时查看智能体状态和活动日志
- 🔄 **工作流可视化**: 图形化展示工作流执行过程
- 📊 **结果展示**: 代码生成结果、审查报告、执行统计
- ⚙️ **配置管理**: 系统设置、API 密钥配置、模型选择

## 🏗️ 文件结构

```
frontend/
├── app.py                 # Streamlit 主应用
└── requirements.txt       # Python 依赖
```

## 🛠️ 技术栈

- **UI 框架**: Streamlit 1.28+
- **HTTP 客户端**: requests / httpx
- **状态管理**: Streamlit Session State
- **图表库**: Plotly / Altair (可选)
- **代码高亮**: Streamlit Code Component

## 📦 安装与运行

### 前置要求

- Python 3.10+
- 后端服务已启动 (FastAPI)
- 虚拟环境 (推荐)

### 安装步骤

```bash
# 进入 frontend 目录
cd sponge/frontend

# 创建虚拟环境 (如果尚未创建)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动前端应用
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### 访问界面

启动后，在浏览器中访问：
- 本地：`http://localhost:8501`
- 远程：`http://<your-server-ip>:8501`

## 🎨 界面模块

### 1. 侧边栏 (Sidebar)

```
┌─────────────────────┐
│  🧽 Sponge Agent   │
├─────────────────────┤
│  📝 新建任务        │
│  📋 任务列表        │
│  🤖 智能体状态      │
│  ⚙️  设置           │
│  ℹ️  关于           │
└─────────────────────┘
```

### 2. 主界面区域

#### 任务创建页面
- 任务描述输入框
- 智能体选择器
- 参数配置选项
- 提交按钮

#### 任务详情页面
- 任务基本信息
- 执行进度条
- 实时日志输出
- 结果展示区

#### 智能体监控页面
- 智能体列表
- 状态指示器
- 活动日志
- 性能指标

#### 设置页面
- API 密钥配置
- 模型选择
- 系统参数
- 主题设置

## 🔧 核心组件

### 任务创建组件

```python
import streamlit as st

def create_task_form():
    with st.form("new_task"):
        description = st.text_area("任务描述", height=150)
        agent_type = st.selectbox(
            "选择智能体",
            ["Coder", "Reviewer", "Manager"]
        )
        priority = st.slider("优先级", 1, 5, 3)
        
        submitted = st.form_submit_button("提交任务")
        
        if submitted:
            response = submit_task(description, agent_type, priority)
            st.success(f"任务已提交！ID: {response['id']}")
```

### 实时监控组件

```python
def monitor_task(task_id):
    placeholder = st.empty()
    
    while True:
        status = get_task_status(task_id)
        
        with placeholder.container():
            st.metric("状态", status['state'])
            st.progress(status['progress'] / 100)
            
            if status.get('logs'):
                with st.expander("查看日志", expanded=True):
                    for log in status['logs'][-10:]:
                        st.text(log)
        
        if status['state'] in ['completed', 'failed']:
            break
        
        time.sleep(2)
```

### 结果展示组件

```python
def display_result(result):
    if result.get('code'):
        st.code(result['code'], language='python')
    
    if result.get('explanation'):
        st.markdown(result['explanation'])
    
    if result.get('metrics'):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("代码行数", result['metrics']['lines'])
        with col2:
            st.metric("复杂度", result['metrics']['complexity'])
        with col3:
            st.metric("测试覆盖", f"{result['metrics']['coverage']}%")
```

## 🔌 API 集成

前端通过 REST API 与后端通信：

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

def submit_task(description, agent_type, priority):
    response = requests.post(
        f"{BASE_URL}/tasks",
        json={
            "description": description,
            "agent_type": agent_type,
            "priority": priority
        }
    )
    return response.json()

def get_task_status(task_id):
    response = requests.get(f"{BASE_URL}/tasks/{task_id}")
    return response.json()

def list_agents():
    response = requests.get(f"{BASE_URL}/agents")
    return response.json()
```

## 🎯 使用场景

### 场景 1: 快速代码生成

1. 在任务创建页面输入需求
2. 选择 Coder 智能体
3. 点击提交
4. 实时查看生成进度
5. 获取生成的代码并复制

### 场景 2: 代码审查

1. 粘贴待审查代码
2. 选择 Reviewer 智能体
3. 配置审查规则
4. 查看审查报告
5. 根据建议修改代码

### 场景 3: 复杂任务编排

1. 创建多步骤任务
2. 配置工作流节点
3. 设置条件分支
4. 监控执行流程
5. 查看最终结果

## 🎨 自定义主题

在 `.streamlit/config.toml` 中配置主题：

```toml
[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

## 🧪 测试

```bash
# 运行 Streamlit 检查
streamlit config show

# 测试 API 连接
curl http://localhost:8000/api/v1/health
```

## 🐛 常见问题

### 问题 1: 无法连接到后端

**解决方案**:
- 确认后端服务已启动
- 检查 BASE_URL 配置
- 验证网络连接

### 问题 2: 会话状态丢失

**解决方案**:
- 避免频繁刷新页面
- 使用 st.session_state 持久化数据
- 实现数据自动保存

### 问题 3: 长任务超时

**解决方案**:
- 增加后端超时配置
- 实现异步轮询机制
- 显示进度提示

## 🚀 性能优化

- 使用缓存减少 API 调用
- 实现增量更新
- 优化大数据集渲染
- 使用分页加载历史任务

## 🔒 安全考虑

- API 密钥不硬编码
- 使用 HTTPS (生产环境)
- 输入验证和清理
- 防止 XSS 攻击

## 📱 响应式设计

界面适配不同设备：

- **桌面端**: 完整功能布局
- **平板端**: 优化触控操作
- **移动端**: 简化视图，核心功能优先

## 🤝 扩展开发

### 添加新页面

```python
# 在 app.py 中添加
def new_feature_page():
    st.title("新功能")
    # 实现逻辑

# 在侧边栏添加导航
if st.sidebar.button("新功能"):
    new_feature_page()
```

### 集成新组件

```python
# 导入自定义组件
from custom_components import AdvancedChart

# 使用组件
chart = AdvancedChart(data)
st.pyplot(chart.render())
```

## 📄 许可证

本项目采用 MIT 许可证

---

## English

### Overview

The `frontend/` directory contains the user interface for the Sponge Multi-Agent Collaboration System, built with **Streamlit**, providing intuitive task management, agent monitoring, and workflow visualization.

### Quick Start

```bash
cd sponge/frontend
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

Then open `http://localhost:8501` in your browser.

### Key Features

- ✅ Task creation and management
- ✅ Real-time agent monitoring
- ✅ Workflow visualization
- ✅ Results display with code highlighting
- ✅ Configuration management

For more details, see the sections above.
