# 架构健康监控与推荐系统 - 完整设计方案

## 一、系统概述

### 1.1 目标
创建一个独立的后台监控系统，持续评估 SpongeCodeAgent 项目的架构健康度，并提供智能改进建议。

### 1.2 设计原则
- **独立性**: 作为后台守护进程运行，不影响主业务流程
- **非侵入性**: 通过只读方式分析代码和运行时数据
- **智能化**: 结合规则引擎 + LLM 生成具体可执行的改进建议
- **可扩展性**: 支持添加新的评估指标和分析工具
- **可操作性**: 提供明确的优先级和行动建议

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                  架构健康监控系统                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  数据采集层   │  │  分析引擎层   │  │  推荐引擎层   │       │
│  │              │  │              │  │              │       │
│  │ • 静态分析   │  │ • 指标计算   │  │ • 规则匹配   │       │
│  │ • 动态监控   │  │ • 趋势分析   │  │ • LLM 生成    │       │
│  │ • Git 历史    │  │ • 异常检测   │  │ • 优先级排序 │       │
│  │ • 依赖扫描   │  │ • 健康评分   │  │ • 案例推荐   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│         └─────────────────┼─────────────────┘                │
│                           │                                  │
│                  ┌────────▼────────┐                         │
│                  │   数据存储层     │                         │
│                  │                 │                         │
│                  │ • SQLite 数据库  │                         │
│                  │ • 时序数据      │                         │
│                  │ • 报告缓存      │                         │
│                  └────────┬────────┘                         │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  API 接口层     │  │  定时调度器    │  │  通知服务     │
│               │  │               │  │               │
│ • REST API    │  │ • Celery Beat │  │ • 邮件通知    │
│ • WebSocket   │  │ • Cron Jobs   │  │ • Slack 集成   │
│ • GraphQL     │  │ • 触发器      │  │ • Webhook     │
└───────────────┘  └───────────────┘  └───────────────┘
```

---

## 三、核心模块设计

### 3.1 数据采集模块 (`app/arch_health/collectors/`)

#### 3.1.1 静态代码分析器
```python
# 使用 tree-sitter 进行 AST 解析
# 指标：耦合度、复杂度、重复率、分层违规
```

#### 3.1.2 依赖分析器
```python
# 分析 requirements.txt 和导入语句
# 指标：依赖新鲜度、安全漏洞、传递依赖
```

#### 3.1.3 Git 历史分析器
```python
# 解析 git log 获取变更历史
# 指标：变更频率、知识集中度、Bus Factor
```

#### 3.1.4 运行时监控采集器
```python
# 从 Prometheus/日志中获取运行时指标
# 指标：可用性、响应时间、错误率
```

### 3.2 分析引擎模块 (`app/arch_health/engines/`)

#### 3.2.1 指标计算器
- 实现 20 个具体指标的计算逻辑
- 支持阈值配置和权重调整
- 输出标准化分数 (0-100)

#### 3.2.2 健康评分器
```python
总体健康度 = Σ(维度得分 × 维度权重)
维度得分 = Σ(指标得分 × 指标权重)
```

#### 3.2.3 趋势分析器
- 对比历史数据识别改善/恶化趋势
- 预测未来健康度走向
- 识别周期性模式

### 3.3 推荐引擎模块 (`app/arch_health/recommenders/`)

#### 3.3.1 规则匹配引擎
```yaml
rules:
  - id: HIGH_COUPLING
    condition: "coupling_index > 0.6"
    severity: HIGH
    action: "考虑将模块拆分为独立服务"
    
  - id: CIRCULAR_DEPENDENCY
    condition: "circular_deps.count > 0"
    severity: CRITICAL
    action: "立即消除循环依赖"
```

#### 3.3.2 LLM 智能推荐器
- 输入：指标数据 + 代码上下文
- 输出：具体的重构建议和代码示例
- 支持多轮对话澄清需求

#### 3.3.3 案例库
- 存储历史问题和解决方案
- 基于相似度推荐过往成功案例
- 持续学习和优化

### 3.4 数据存储模块 (`app/arch_health/storage/`)

#### 3.4.1 数据库模型扩展
```python
class ArchitectureHealthSnapshot(Base):
    """架构健康度快照"""
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    overall_score = Column(Float)
    dimension_scores = Column(JSON)  # 五维度得分
    metrics_data = Column(JSON)      # 详细指标数据
    recommendations = Column(JSON)   # 生成的建议
    
class ArchitectureRecommendation(Base):
    """架构改进建议"""
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('health_snapshots.id'))
    priority = Column(String(50))  # critical/high/medium/low
    category = Column(String(100))
    title = Column(String(255))
    description = Column(Text)
    suggested_actions = Column(JSON)
    estimated_effort = Column(String(50))  # hours/days
    status = Column(String(50), default='pending')
```

---

## 四、评估指标体系

### 4.1 五大维度详细指标

| 维度 | 权重 | 指标数 | 关键指标 |
|------|------|--------|----------|
| **结构耦合度** | 25% | 4 | 耦合指数、循环依赖、上帝模块、分层违规 |
| **代码质量** | 20% | 5 | 技术债务、重复率、测试覆盖、复杂度、文档覆盖 |
| **依赖管理** | 15% | 3 | 新鲜度、深度、传递依赖爆炸 |
| **可维护性** | 20% | 4 | 内聚度、变更稳定性、知识集中、重构需求 |
| **运行时健康** | 20% | 4 | 可用性、响应时间、错误率、资源利用 |

### 4.2 评分标准

| 总分 | 等级 | 颜色 | 行动 |
|------|------|------|------|
| 90-100 | 优秀 | 🟢 | 保持监控 |
| 75-89 | 良好 | 🟡 | 关注警告项 |
| 60-74 | 一般 | 🟠 | 优先处理高风险 |
| < 60 | 危险 | 🔴 | 立即介入重构 |

---

## 五、API 接口设计

### 5.1 RESTful API

```python
# app/api/architecture_health.py

GET /api/v1/architecture/health
  - 返回当前健康度快照
  
GET /api/v1/architecture/health/history
  - 参数：start_date, end_date, granularity
  - 返回历史趋势数据
  
GET /api/v1/architecture/health/dimensions
  - 返回五维度详细得分
  
GET /api/v1/architecture/recommendations
  - 参数：status, priority, category
  - 返回改进建议列表
  
POST /api/v1/architecture/recommendations/{id}/accept
  - 标记建议为已接受
  
POST /api/v1/architecture/recommendations/{id}/dismiss
  - 标记建议为已忽略
  
POST /api/v1/architecture/analyze/trigger
  - 手动触发一次完整分析
  
GET /api/v1/architecture/report/latest
  - 获取最新完整报告 (PDF/Markdown)
```

### 5.2 WebSocket 实时推送

```python
# 推送健康度变化、新发现的问题、建议更新
ws://localhost:8000/ws/architecture-health
```

---

## 六、定时任务调度

### 6.1 Celery Beat 配置

```python
# app/arch_health/scheduler.py

CELERY_BEAT_SCHEDULE = {
    # 每日轻量级分析
    'daily-light-analysis': {
        'task': 'arch_health.tasks.run_light_analysis',
        'schedule': crontab(hour=2, minute=0),  # 凌晨 2 点
    },
    
    # 每周完整分析
    'weekly-full-analysis': {
        'task': 'arch_health.tasks.run_full_analysis',
        'schedule': crontab(day_of_week='monday', hour=3, minute=0),
    },
    
    # 每月生成报告
    'monthly-report-generation': {
        'task': 'arch_health.tasks.generate_monthly_report',
        'schedule': crontab(day_of_month=1, hour=4, minute=0),
    },
    
    # 每小时检查运行时指标
    'hourly-runtime-check': {
        'task': 'arch_health.tasks.check_runtime_metrics',
        'schedule': crontab(minute=0),
    },
}
```

### 6.2 触发机制

1. **定时触发**: Celery Beat 按计划执行
2. **事件触发**: Git push、部署完成后自动分析
3. **手动触发**: API 调用或命令行工具
4. **阈值触发**: 关键指标突破阈值时立即分析

---

## 七、报告输出

### 7.1 实时仪表盘数据

```json
{
  "overall_score": 78.5,
  "grade": "GOOD",
  "dimensions": {
    "structural_coupling": {"score": 72, "trend": "↓"},
    "code_quality": {"score": 85, "trend": "↑"},
    "dependency_management": {"score": 90, "trend": "→"},
    "maintainability": {"score": 75, "trend": "↓"},
    "runtime_health": {"score": 82, "trend": "↑"}
  },
  "top_risks": [
    {
      "id": "RISK-001",
      "title": "检测到循环依赖",
      "severity": "HIGH",
      "affected_modules": ["agents", "workflow"]
    }
  ],
  "active_recommendations": 5
}
```

### 7.2 周报模板

```markdown
# 架构健康周报 (2024-W42)

## 执行摘要
- 总体健康度：**78.5** (↑ 2.3 分)
- 新增问题：3 个
- 已解决问题：5 个
- 本周重点：消除循环依赖

## 维度分析
[雷达图]

## 趋势变化
[折线图]

## 优先级建议
1. 🔴 [紧急] 消除 agents 和 workflow 模块的循环依赖
   - 预计工作量：4 小时
   - 影响范围：高
   
2. 🟡 [重要] 提升测试覆盖率至 80%
   - 预计工作量：2 天
   - 影响范围：中

## 改进进展
- ✅ 已完成：重构 file_tools 模块
- 🔄 进行中：优化数据库查询
- ⏳ 待开始：添加 API 文档
```

---

## 八、实施路线图

### 阶段 1: 基础设施 (2 周)
- [ ] 创建 `app/arch_health/` 目录结构
- [ ] 实现数据库模型
- [ ] 集成 tree-sitter 进行代码解析
- [ ] 配置 Celery Beat 定时任务

### 阶段 2: 数据采集 (2 周)
- [ ] 实现静态代码分析器
- [ ] 实现依赖分析器
- [ ] 实现 Git 历史分析器
- [ ] 建立数据采集管道

### 阶段 3: 分析引擎 (2 周)
- [ ] 实现 20 个指标计算逻辑
- [ ] 实现健康评分算法
- [ ] 实现趋势分析
- [ ] 配置阈值和权重

### 阶段 4: 推荐系统 (2 周)
- [ ] 实现规则匹配引擎
- [ ] 集成 LLM 生成建议
- [ ] 建立案例库
- [ ] 实现优先级排序

### 阶段 5: API 与界面 (2 周)
- [ ] 实现 REST API
- [ ] 实现 WebSocket 推送
- [ ] 生成报告模板
- [ ] 配置通知服务

### 阶段 6: 优化与上线 (1 周)
- [ ] 性能优化
- [ ] 文档完善
- [ ] 测试验证
- [ ] 正式上线

**总周期**: 11 周

---

## 九、文件结构

```
sponge/app/arch_health/
├── __init__.py
├── README.md
├── config.py                 # 配置文件
├── models.py                 # 数据库模型
├── schemas.py                # Pydantic 模式
├── tasks.py                  # Celery 任务
├── collectors/               # 数据采集器
│   ├── __init__.py
│   ├── base_collector.py
│   ├── code_analyzer.py
│   ├── dependency_analyzer.py
│   ├── git_history_analyzer.py
│   └── runtime_monitor.py
├── engines/                  # 分析引擎
│   ├── __init__.py
│   ├── metrics_calculator.py
│   ├── health_scorer.py
│   └── trend_analyzer.py
├── recommenders/             # 推荐引擎
│   ├── __init__.py
│   ├── rule_engine.py
│   ├── llm_recommender.py
│   └── case_library.py
├── storage/                  # 数据存储
│   ├── __init__.py
│   ├── repository.py
│   └── cache_manager.py
├── reporters/                # 报告生成
│   ├── __init__.py
│   ├── dashboard_builder.py
│   ├── pdf_generator.py
│   └── markdown_exporter.py
├── notifiers/                # 通知服务
│   ├── __init__.py
│   ├── email_notifier.py
│   ├── slack_notifier.py
│   └── webhook_notifier.py
└── api/                      # API 路由
    ├── __init__.py
    └── architecture_health.py
```

---

## 十、技术栈

### 已有组件复用
- ✅ Celery (任务调度)
- ✅ SQLAlchemy (数据库)
- ✅ FastAPI (API 服务)
- ✅ tree-sitter (代码解析)
- ✅ LangChain/LLM (智能推荐)

### 需要新增的依赖
```txt
# 代码分析
radon>=6.0.0          # 复杂度分析
deptry>=0.12.0        # 依赖检查
pylint>=3.0.0         # 代码质量

# 可视化
plotly>=5.18.0        # 图表生成
reportlab>=4.0.0      # PDF 生成

# Git 分析
GitPython>=3.1.0      # Git 操作

# 通知服务
aiosmtplib>=3.0.0     # 邮件发送
slack-sdk>=3.25.0     # Slack 集成
```

---

## 十一、成功度量

### 11.1 系统指标
- 分析准确率 > 90%
- 误报率 < 5%
- 分析耗时 < 10 分钟 (完整分析)
- API 响应时间 < 200ms

### 11.2 业务价值
- 架构问题发现时间缩短 70%
- 技术债务增长率降低 50%
- 重构决策效率提升 60%
- 团队架构意识显著提升

---

## 十二、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 分析性能影响 | 高 | 异步执行、资源限制、增量分析 |
| 误报过多 | 中 | 人工校准、反馈循环、机器学习优化 |
| 建议不可行 | 中 | LLM 提示工程、专家评审、案例验证 |
| 团队抵触 | 低 | 渐进推广、培训宣导、正向激励 |

---

## 十三、下一步行动

1. **立即开始**: 创建基础目录结构和数据库模型
2. **第一周完成**: 实现静态代码分析器和依赖分析器
3. **第二周完成**: 实现指标计算和健康评分
4. **持续迭代**: 根据反馈优化推荐质量

是否需要我开始实现这个系统？我可以从创建基础框架开始。
