# AI Token Usage

一个统一的 AI 工具 token 用量追踪项目，支持 OpenClaw、Claude 和 Qwen。

## 功能特性

- 统一收集多个 AI 工具的 token 使用数据
- 自动每天运行并保存数据到 SQLite 数据库
- 支持命令行查询和统计
- 支持邮件发送每日/周期性报告
- 即将支持 Web 界面图表展示

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/richardhuang/ai_token_usage.git
cd ai_token_usage
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

复制配置模板并修改：

```bash
cp config/settings.json.sample config/settings.json
```

编辑 `config/settings.json` 填写你的邮箱配置和 API token。

### 4. 运行首次数据获取

```bash
# 设置 OpenClaw token（如果需要）
export OPENCLAW_TOKEN="your_token"

# 运行获取脚本
python3 scripts/fetch_openclaw.py --days 7
python3 scripts/fetch_claude.py --days 7
python3 scripts/fetch_qwen.py --days 7
```

### 5. 设置定时任务（Cron）

编辑 crontab：

```bash
crontab -e
```

添加（每天 0:30 运行）：

```
30 0 * * * /path/to/ai_token_usage/cron/daily_run.sh >> /path/to/ai_token_usage/logs/cron.log 2>&1
```

## 命令行工具

```bash
# 查看今天用量
python3 cli.py today

# 查看某天的数据
python3 cli.py query 2026-02-26

# 查看最近7天的用量Top
python3 cli.py top --days 7

# 查看汇总统计
python3 cli.py summary

# 发送邮件报告
python3 cli.py report email
```

## 项目结构

```
ai_token_usage/
├── cli.py                        # 统一命令行工具
├── requirements.txt              # Python 依赖
├── README.md
├── config/
│   └── settings.json.sample      # 配置模板
├── scripts/
│   ├── fetch_openclaw.py         # OpenClaw 数据获取
│   ├── fetch_claude.py           # Claude 数据获取
│   ├── fetch_qwen.py             # Qwen 数据获取
│   └── shared/
│       ├── db.py                 # 数据库操作
│       ├── email.py              # 邮件发送
│       └── utils.py              # 工具函数
├── cron/
│   └── daily_run.sh              # 每日定时任务脚本
└── logs/                         # 日志目录（自动创建）
```

## 数据库

数据保存在 `~/.ai_token_usage/usage.db`，表结构：

```sql
CREATE TABLE daily_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    tool_name TEXT,
    tokens_used INTEGER,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_tokens INTEGER DEFAULT 0,
    models_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, tool_name)
);
```

## 支持的工具

| 工具 | 数据源 | 配置 | 支持状态 |
|------|--------|------|----------|
| OpenClaw | WebSocket API | OPENCLAW_TOKEN | ✅ |
| Claude | JSONL 日志 | 无需额外配置 | ✅ |
| Qwen | JSONL 日志 | 无需额外配置 | ✅ |

## 后续计划

- [ ] Web 界面（Flask/FastAPI + Chart.js）
- [ ] 更多工具支持（ChatGPT、Gemini 等）
- [ ] 成本计算和统计
- [ ] 使用周期分析
