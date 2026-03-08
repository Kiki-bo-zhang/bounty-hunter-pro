# Bounty Hunter Pro 🎯

基于多 Agent 架构的智能赏金任务搜索与分析系统。

## 🚀 核心特性

- **多 Agent 协作**: Search/Analysis/Competition/Value/Report/Forum 六大 Agent
- **IR 中间表示**: 统一的赏金任务中间表示，支持多格式输出
- **论坛协作机制**: Agent 间通过 ForumAgent 讨论确认任务质量
- **智能评估**: 技术匹配度、竞争分析、风险评估
- **多平台搜索**: GitHub, IssueHunt 等平台统一搜索

## 📁 项目结构

```
bounty-hunter-pro/
├── agents/                 # Agent 模块
│   ├── search_agent.py     # 搜索 Agent
│   ├── analysis_agent.py   # 分析 Agent
│   ├── competition_agent.py# 竞争分析 Agent
│   ├── value_agent.py      # 价值评估 Agent
│   ├── report_agent.py     # 报告生成 Agent
│   └── forum_agent.py      # 论坛协作 Agent
├── ir/                     # 中间表示层
│   ├── schema.py           # IR Schema 定义
│   ├── validator.py        # IR 校验器
│   └── renderer.py         # 多格式渲染器
├── utils/                  # 工具函数
│   ├── github_api.py       # GitHub API 封装
│   ├── filters.py          # 任务过滤器
│   └── config.py           # 配置管理
├── reports/                # 报告输出
├── config/                 # 配置文件
├── main.py                 # 主入口
└── README.md
```

## 🏗️ Agent 架构

### 1. SearchAgent - 搜索 Agent
- 多平台搜索（GitHub, IssueHunt）
- 实时获取开放赏金任务
- 初步过滤（金额、语言、状态）

### 2. AnalysisAgent - 分析 Agent
- 技术栈匹配度分析
- 任务复杂度评估
- 实现可行性判断

### 3. CompetitionAgent - 竞争分析 Agent
- PR 竞争情况检查
- 维护者活跃度分析
- 任务热度评估

### 4. ValueAgent - 价值评估 Agent
- 赏金金额性价比
- 时间投入预估
- 风险评级（货币类型、项目稳定性）

### 5. ForumAgent - 论坛协作 Agent
- 协调多个 Agent 讨论
- 主持人模型引导决策
- 达成共识推荐

### 6. ReportAgent - 报告生成 Agent
- IR 中间表示生成
- 多格式输出（Markdown, JSON, HTML）
- 邮件自动发送

## 🔄 工作流程

```
用户输入需求 → SearchAgent 搜索 → 
多个 Agent 并行分析 → ForumAgent 讨论 → 
ReportAgent 生成 IR → 渲染多格式报告
```

## 🛠️ 安装

```bash
# 克隆仓库
git clone https://github.com/Kiki-bo-zhang/bounty-hunter-pro.git
cd bounty-hunter-pro

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 GitHub Token
```

## 📝 配置

编辑 `.env` 文件：

```env
# GitHub API Token
GITHUB_TOKEN=your_github_token

# 搜索配置
MIN_BOUNTY=20
DEFAULT_CURRENCY=USD
MAX_TASKS_PER_RUN=50

# Agent 配置
ENABLE_FORUM_DISCUSSION=true
FORUM_ROUNDS=3
```

## 🚀 使用

```bash
# 运行完整搜索
python main.py --query "python javascript" --min-bounty 20

# 仅搜索不生成报告
python main.py --search-only

# 指定输出格式
python main.py --format markdown --email your@email.com

# 查看帮助
python main.py --help
```

## 📊 IR 中间表示

赏金任务 IR Schema:

```json
{
  "task_id": "owner/repo#123",
  "title": "Task title",
  "url": "https://github.com/...",
  "bounty": {
    "amount": 100,
    "currency": "USD"
  },
  "analysis": {
    "tech_match": 0.85,
    "complexity": "medium",
    "feasibility": 0.9
  },
  "competition": {
    "open_prs": 0,
    "maintainer_active": true
  },
  "value": {
    "score": 8.5,
    "risk": "low"
  },
  "forum_consensus": "recommend",
  "final_score": 8.2
}
```

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📜 License

MIT License
