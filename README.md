# ai-market-brief-cn

每天自动生成一份中文版 AI / 半导体 / Edge AI / 电力 / Robotics 主题趋势研究报告，并每天轮换研究一家公司商业逻辑。

项目已经升级为：

```text
AI Theme Intelligence System（AI 主题趋势研究系统）
```

它不只是做新闻摘要，而是更关注：

- 市场 narrative（叙事）变化
- AI 产业结构
- 估值重估逻辑（rerating）
- 护城河分析
- 趋势验证
- 板块轮动
- AI 基础设施演化
- 交易日 / 非交易日的不同研究模式

报告会保存到 `reports/` 目录，文件名格式为：

```text
YYYY-MM-DD-ai-market-brief-cn.md
```

这个项目适合直接上传到 GitHub，用 GitHub Actions 每天自动运行，也可以在本地手动运行。

## 项目用途

这个项目帮助你每天复盘以下问题：

- AI、半导体、Edge AI、数据中心电力、机器人相关产业链发生了什么。
- watchlist 中的重点公司有没有新的新闻线索。
- 新闻是否会影响公司的长期商业逻辑。
- 每天深入研究一家公司的赚钱方式、增长故事、护城河、风险和验证点。

当前 watchlist 包含：

```text
NVDA, QCOM, AMBA, AMD, AVGO, TSM, ANET, VRT, GEV, VST, CEG, AAPL, MSFT, TSLA
```

## 项目结构

```text
ai-market-brief-cn/
  README.md
  requirements.txt
  .env.example
  .gitignore
  scripts/
    daily_brief.py
    company_rotation.py
    market_calendar.py
    narrative_detection.py
    theme_clustering.py
    dynamic_mover_scanner.py
    sector_relationship_engine.py
    rerating_analysis.py
    thesis_tracker.py
    sources.py
    llm_summary.py
  reports/
    .gitkeep
  data/
    company_watchlist.json
  .github/
    workflows/
      daily.yml
```

## 如何安装

建议使用 Python 3.11 或更高版本。

```bash
cd ai-market-brief-cn
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 如何配置 `.env`

复制示例配置：

```bash
cp .env.example .env
```

编辑 `.env`：

```text
OPENAI_API_KEY=你的 OpenAI API Key

# 可选：默认 gpt-4o-mini
OPENAI_MODEL=gpt-4o-mini
```

如果没有 `OPENAI_API_KEY`，脚本也能运行。它会抓取 RSS 新闻并生成基础中文模板，只是不会调用 OpenAI 做更完整的总结。

## 如何本地运行

```bash
cd ai-market-brief-cn
source .venv/bin/activate
python scripts/daily_brief.py
```

运行成功后，会在 `reports/` 目录看到当天报告，例如：

```text
reports/2026-05-24-ai-market-brief-cn.md
```

## 报告模式

系统会自动判断今天是否是美股交易日。

如果是交易日，报告使用：

```text
Trading Day Mode（交易日模式）
```

重点关注：

- 今日股价异动
- 成交量变化
- 板块轮动
- earnings reaction
- market narrative shift
- dynamic movers

如果是周末或美国主要节假日，报告使用：

```text
Non-Trading Day / Weekend Research Mode（非交易日研究模式）
```

重点改为：

- 最近 AI narrative 变化
- 长期趋势研究
- 深度公司研究
- AI 产业链 mapping
- thesis tracking
- edge AI / robotics / inference / power 等长期方向

非交易日报告会更像“周末科技产业研究笔记”，不会强行写“今日股价异动”。

## 新版报告结构

新版报告会包含：

```text
0. 报告模式
1. 今日市场主线
2. Narrative Shift（叙事迁移）
3. AI Sector Heatmap（AI 板块热度图）
4. Dynamic AI Movers（动态 AI 异动发现）
5. 深度公司研究
6. AI Industry Chain Mapping（AI 产业链关系图）
7. Thesis Tracking（长期 thesis 跟踪）
8. Thinking Questions（思考问题）
```

## 新闻来源

项目优先使用免费、简单、稳定的来源：

- Google News RSS：用于主题新闻搜索。
- Yahoo Finance RSS：用于单个 ticker 的新闻。
- SEC filings 链接：用于公司研究参考。
- Yahoo Finance / Google News 链接：用于后续手动验证。

部分网站可能无法稳定抓取正文，所以项目只依赖标题、链接和 RSS 摘要，不会因为某个来源失败而中断整份报告。

## 如何上传 GitHub

如果你还没有创建 GitHub 仓库，可以在 GitHub 上创建一个名为 `ai-market-brief-cn` 的新仓库。

然后在本地执行：

```bash
cd ai-market-brief-cn
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yew46/ai-market-brief-cn.git
git push -u origin main
```

如果这个目录已经在一个更大的 Git 仓库里，也可以直接把 `ai-market-brief-cn/` 目录作为项目内容上传。

## 如何开启 GitHub Actions

项目已经包含：

```text
.github/workflows/daily.yml
```

上传到 GitHub 后，进入仓库页面：

1. 打开 `Actions` 标签。
2. 如果 GitHub 提示需要启用 workflows，点击启用。
3. 这个 workflow 支持每天自动运行，也支持手动点击 `Run workflow`。

默认计划任务使用 UTC 时间运行。当前配置大约对应美国东部时间晚上 9 点附近；夏令时和冬令时会有 1 小时偏差。

## 如何在 GitHub Secrets 添加 `OPENAI_API_KEY`

在 GitHub 仓库页面：

1. 进入 `Settings`。
2. 点击 `Secrets and variables`。
3. 点击 `Actions`。
4. 点击 `New repository secret`。
5. Name 填：

```text
OPENAI_API_KEY
```

Value 填你的 OpenAI API Key。

保存后，GitHub Actions 每天运行时就可以调用 OpenAI 生成更完整的中文报告。

如果不添加这个 Secret，workflow 仍然可以运行，只会生成基础模板。

## 如何修改 watchlist

编辑：

```text
data/company_watchlist.json
```

每家公司保持以下字段：

```json
{
  "ticker": "QCOM",
  "中文名": "高通",
  "所属主题": "Edge AI / 手机 / AI PC / 汽车芯片",
  "核心观察逻辑": "观察端侧 AI 是否推动手机换机、AI PC 渗透和汽车芯片设计导入，从而降低对手机周期的依赖。"
}
```

修改后提交到 GitHub，下一次自动运行会使用新的 watchlist。

## 如何每天阅读报告

每天运行后，打开 `reports/` 目录中最新的 Markdown 文件。

建议阅读顺序：

1. 先看 `今日核心结论`，判断今天最重要的线索。
2. 再看 `今日 AI / 半导体 / Edge AI 新闻`，点开原始链接验证。
3. 阅读 `重点股票观察`，区分短期新闻和长期逻辑。
4. 深入阅读 `今日公司商业逻辑研究`，记录自己是否认同。
5. 用最后的 3 个问题作为第二天继续研究的入口。

## 注意事项

这个项目只用于投资学习和研究复盘，不构成投资建议。脚本不会编造实时股价；如果没有足够信息，会明确提示需要继续验证。
