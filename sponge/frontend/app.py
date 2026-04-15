"""
Sponge 前端 - Streamlit 多智能体协作界面
提供可视化的任务管理、工作流监控和结果查看功能
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# 配置
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")
AUTH_ENDPOINT = f"{API_BASE_URL}/api/v1/auth/login"
TASKS_ENDPOINT = f"{API_BASE_URL}/api/v1/tasks"
WORKFLOW_ENDPOINT = f"{API_BASE_URL}/api/v1/workflow/execute"
FILES_ENDPOINT = f"{API_BASE_URL}/api/v1/files"
HEALTH_ENDPOINT = f"{API_BASE_URL}/api/health"

st.set_page_config(
    page_title="Sponge - Multi-Agent System",
    page_icon="🧽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 600;
    }
    .status-pending { background-color: #fef3c7; color: #92400e; }
    .status-running { background-color: #dbeafe; color: #1e40af; }
    .status-completed { background-color: #d1fae5; color: #065f46; }
    .status-failed { background-color: #fee2e2; color: #991b1b; }
    .agent-card {
        background-color: #f9fafb;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .code-block {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'task_history' not in st.session_state:
        st.session_state.task_history = []


def login(username: str, password: str) -> bool:
    """用户登录"""
    try:
        response = requests.post(
            AUTH_ENDPOINT,
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.access_token = data['access_token']
            st.session_state.current_user = data['username']
            st.session_state.authenticated = True
            return True
        else:
            st.error(f"登录失败: {response.json().get('detail', '未知错误')}")
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"连接服务器失败: {str(e)}")
        return False


def get_headers() -> Dict[str, str]:
    """获取认证请求头"""
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}


def check_health() -> bool:
    """检查 API 健康状态"""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        return response.status_code == 200
    except:
        return False


def create_task(description: str, language: str = "python") -> Optional[Dict]:
    """创建新任务"""
    try:
        response = requests.post(
            TASKS_ENDPOINT,
            json={"description": description, "language": language},
            headers=get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"创建任务失败: {response.json().get('detail', '未知错误')}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"请求失败: {str(e)}")
        return None


def execute_workflow(task_id: str) -> Optional[Dict]:
    """执行工作流"""
    try:
        response = requests.post(
            f"{WORKFLOW_ENDPOINT}/{task_id}",
            headers=get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"执行工作流失败: {response.json().get('detail', '未知错误')}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"请求失败: {str(e)}")
        return None


def get_tasks() -> List[Dict]:
    """获取任务列表"""
    try:
        response = requests.get(TASKS_ENDPOINT, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []


def get_task(task_id: str) -> Optional[Dict]:
    """获取单个任务详情"""
    try:
        response = requests.get(
            f"{TASKS_ENDPOINT}/{task_id}",
            headers=get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def render_login_page():
    """渲染登录页面"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🧽 Sponge</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Multi-Agent Code Generation System</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("用户名", value="admin")
            password = st.text_input("密码", type="password", value="admin123")
            submit = st.form_submit_button("登录", use_container_width=True)
            
            if submit:
                if login(username, password):
                    st.success("登录成功！")
                    time.sleep(1)
                    st.rerun()
        
        st.info("💡 默认账号：admin / admin123")


def render_status_badge(status: str) -> str:
    """渲染状态徽章"""
    status_classes = {
        "pending": "status-pending",
        "running": "status-running",
        "completed": "status-completed",
        "failed": "status-failed"
    }
    class_name = status_classes.get(status.lower(), "status-pending")
    return f'<span class="status-badge {class_name}">{status.upper()}</span>'


def render_agent_card(agent_name: str, content: str, icon: str = "🤖"):
    """渲染 Agent 卡片"""
    agent_icons = {
        "Planner": "📋",
        "Coder": "💻",
        "Reviewer": "🔍",
        "Tester": "🧪",
        "Executor": "⚙️"
    }
    icon = agent_icons.get(agent_name, icon)
    
    st.markdown(f"""
    <div class="agent-card">
        <h4>{icon} {agent_name}</h4>
        <pre style="white-space: pre-wrap; margin: 0;">{content}</pre>
    </div>
    """, unsafe_allow_html=True)


def render_main_dashboard():
    """渲染主仪表板"""
    # 顶部导航栏
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1 class="main-header">🧽 Sponge Dashboard</h1>', unsafe_allow_html=True)
    with col2:
        if st.button("退出登录", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.access_token = None
            st.session_state.current_user = None
            st.rerun()
    
    # 健康检查
    if not check_health():
        st.error("⚠️ 无法连接到 API 服务器，请确保后端服务正在运行")
    
    # 侧边栏
    with st.sidebar:
        st.markdown(f"👤 **用户**: {st.session_state.current_user}")
        st.divider()
        
        menu = st.radio(
            "导航菜单",
            ["新建任务", "任务列表", "系统监控", "关于"],
            label_visibility="collapsed"
        )
        
        st.divider()
        st.markdown("### 快捷操作")
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
    
    return menu


def render_new_task_page():
    """渲染新建任务页面"""
    st.header("📝 创建新任务")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        description = st.text_area(
            "任务描述",
            placeholder="请详细描述您需要完成的任务，例如：创建一个 Python 函数，计算斐波那契数列的第 n 项...",
            height=200
        )
    
    with col2:
        language = st.selectbox(
            "编程语言",
            ["python", "javascript", "java", "cpp", "go", "rust"],
            index=0
        )
        
        st.info("💡 提示：描述越详细，生成的代码质量越高")
    
    if st.button("🚀 创建并执行任务", type="primary", use_container_width=True):
        if not description.strip():
            st.warning("请输入任务描述")
        else:
            with st.spinner("正在创建任务..."):
                task = create_task(description, language)
                if task:
                    st.session_state.task_history.append(task)
                    st.success(f"✅ 任务创建成功！ID: `{task['id']}`")
                    
                    # 自动执行工作流
                    with st.spinner("正在执行多智能体工作流..."):
                        result = execute_workflow(task['id'])
                        if result:
                            st.success("✅ 工作流执行完成！")
                            st.session_state.current_task_result = result
                            st.rerun()
                        else:
                            st.error("工作流执行失败")


def render_task_list_page():
    """渲染任务列表页面"""
    st.header("📋 任务列表")
    
    tasks = get_tasks()
    
    if not tasks:
        st.info("暂无任务，点击'新建任务'开始使用")
        return
    
    # 任务统计
    col1, col2, col3, col4 = st.columns(4)
    status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
    for task in tasks:
        status = task.get('status', 'pending').lower()
        if status in status_counts:
            status_counts[status] += 1
    
    col1.metric("总计", len(tasks))
    col2.metric("进行中", status_counts['running'])
    col3.metric("已完成", status_counts['completed'])
    col4.metric("失败", status_counts['failed'])
    
    st.divider()
    
    # 任务表格
    for task in sorted(tasks, key=lambda x: x.get('created_at', ''), reverse=True):
        with st.expander(
            f"{render_status_badge(task.get('status', 'pending'))} **{task.get('description', '无标题')[:80]}** "
            f"`({task.get('id', '')[:8]}...)` - {task.get('language', 'unknown').upper()}",
            expanded=False
        ):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**任务描述:**")
                st.write(task.get('description', '无描述'))
                
                st.markdown("**创建时间:**")
                st.text(task.get('created_at', '未知'))
            
            with col2:
                st.markdown("**详细信息:**")
                st.json({
                    "ID": task.get('id'),
                    "状态": task.get('status'),
                    "语言": task.get('language'),
                    "文件数": len(task.get('files', []))
                })
                
                if st.button("查看详情", key=f"view_{task['id']}"):
                    st.session_state.selected_task_id = task['id']
                    st.rerun()


def render_task_detail_page(task_id: str):
    """渲染任务详情页"""
    task = get_task(task_id)
    
    if not task:
        st.error("任务不存在")
        return
    
    st.header(f"任务详情: {task['id'][:8]}...")
    
    # 基本信息
    col1, col2, col3 = st.columns(3)
    col1.metric("状态", task.get('status', 'unknown'))
    col2.metric("语言", task.get('language', 'unknown').upper())
    col3.metric("文件数", len(task.get('files', [])))
    
    st.markdown("**任务描述:**")
    st.write(task.get('description', '无描述'))
    
    st.divider()
    
    # Agent 执行结果
    st.subheader("🤖 智能体执行结果")
    
    agent_results = task.get('agent_results', {})
    
    if 'planner' in agent_results:
        render_agent_card("Planner", agent_results['planner'])
    
    if 'coder' in agent_results:
        render_agent_card("Coder", agent_results['coder'])
    
    if 'reviewer' in agent_results:
        render_agent_card("Reviewer", agent_results['reviewer'])
    
    if 'tester' in agent_results:
        render_agent_card("Tester", agent_results['tester'])
    
    # 生成的文件
    files = task.get('files', [])
    if files:
        st.divider()
        st.subheader("📁 生成的文件")
        
        for file_info in files:
            with st.expander(f"📄 {file_info.get('filename', 'unknown')}"):
                st.code(file_info.get('content', ''), language=task.get('language', 'python'))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="下载文件",
                        data=file_info.get('content', ''),
                        file_name=file_info.get('filename', 'download.txt'),
                        mime="text/plain"
                    )
                with col2:
                    st.text(f"大小: {file_info.get('size', 0)} bytes")


def render_monitoring_page():
    """渲染系统监控页面"""
    st.header("📊 系统监控")
    
    # API 健康状态
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### API 服务状态")
        if check_health():
            st.success("✅ API 服务正常运行")
            try:
                response = requests.get(HEALTH_ENDPOINT, timeout=5)
                health_data = response.json()
                st.json(health_data)
            except Exception as e:
                st.error(f"获取健康信息失败: {e}")
        else:
            st.error("❌ API 服务不可用")
    
    with col2:
        st.markdown("### Celery Worker 状态")
        st.info("Celery Worker 状态监控待实现")
    
    st.divider()
    
    # 性能指标
    st.markdown("### 性能指标")
    
    tasks = get_tasks()
    if tasks:
        # 任务状态分布
        status_dist = {}
        for task in tasks:
            status = task.get('status', 'unknown')
            status_dist[status] = status_dist.get(status, 0) + 1
        
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(status_dist)
        with col2:
            st.markdown("**任务状态分布:**")
            for status, count in status_dist.items():
                st.write(f"- {status}: {count}")
    else:
        st.info("暂无任务数据")


def render_about_page():
    """渲染关于页面"""
    st.header("ℹ️ 关于 Sponge")
    
    st.markdown("""
    ### 🧽 Sponge - 多智能体代码生成系统
    
    Sponge 是一个基于 LangGraph 的多智能体协作系统，能够自动完成代码生成、审查和测试任务。
    
    #### 核心特性
    
    - 🤖 **多智能体协作**: Planner、Coder、Reviewer、Tester 四个智能体协同工作
    - 🔄 **自动化工作流**: 从需求分析到代码生成的完整自动化流程
    - 🔍 **代码审查**: 自动检测代码质量和潜在问题
    - 🧪 **测试验证**: 自动生成测试用例并验证代码正确性
    - 🔐 **安全认证**: JWT 身份验证保护所有接口
    - ⚡ **异步处理**: 基于 Celery 的异步任务队列
    
    #### 技术栈
    
    - **后端**: FastAPI, SQLAlchemy, LangGraph, Celery
    - **前端**: Streamlit
    - **数据库**: SQLite / PostgreSQL
    - **消息队列**: Redis
    
    #### 版本信息
    
    - 当前版本: 1.0.0
    - 构建日期: 2024
    """)
    
    st.divider()
    
    st.markdown("### 📚 文档链接")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.link_button("API 文档", "/docs/API_REFERENCE.md")
    with col2:
        st.link_button("架构说明", "/docs/ARCHITECTURE.md")
    with col3:
        st.link_button("开发指南", "/docs/DEVELOPMENT_GUIDE.md")


def main():
    """主函数"""
    init_session_state()
    
    if not st.session_state.authenticated:
        render_login_page()
        return
    
    menu = render_main_dashboard()
    
    if menu == "新建任务":
        render_new_task_page()
    elif menu == "任务列表":
        if hasattr(st.session_state, 'selected_task_id') and st.session_state.selected_task_id:
            render_task_detail_page(st.session_state.selected_task_id)
        else:
            render_task_list_page()
    elif menu == "系统监控":
        render_monitoring_page()
    elif menu == "关于":
        render_about_page()


if __name__ == "__main__":
    main()
