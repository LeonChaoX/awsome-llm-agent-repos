# 每日 LLM & Agent 热门仓库

每天北京时间 10:00 搜索 GitHub 上近期创建的 LLM、AI Agent、RAG、MCP 和多智能体相关项目，按 Star 增长速度与主题相关性选出 10 个仓库，并推送到飞书群机器人。

## 排名方式

- 候选范围：最近 180 天创建、非 Fork、未归档且与 LLM/Agent 关键词相关的公开仓库。
- 核心指标：当前 Star 数减去至少 7 天前的 Star 快照。
- 冷启动：部署不足 7 天时，根据已有观测期或项目创建以来的速度估算 7 日增长，并在飞书卡片中明确显示“约”。
- 快照存储：Action 自动创建并维护 `data` 分支的 `stars.json`，主分支不保存每日数据。
- 相关性：仓库名称、简介和 Topics 必须命中 LLM、Agent、MCP、RAG 等主题词。

GitHub Search API 不直接提供历史 Star 增量，因此首次部署需要 7 天才能得到完全基于快照的真实周增长榜。

## 配置飞书机器人

进入仓库 `Settings → Secrets and variables → Actions`，添加：

| Secret | 是否必需 | 用途 |
| --- | --- | --- |
| `FEISHU_WEBHOOK_URL` | 是 | 飞书自定义机器人的 Webhook URL |
| `FEISHU_SIGNING_SECRET` | 否 | 机器人开启“签名校验”时使用的密钥 |

不需要创建个人 GitHub Token。工作流使用 GitHub 自动提供的 `GITHUB_TOKEN`，权限仅为当前仓库内容读写，用于调用公开搜索 API 和更新 `data` 分支。

如果暂时没有设置 `FEISHU_WEBHOOK_URL`，工作流仍会完成采集和快照更新，但会跳过消息发送。

## 启用与测试

1. 将代码推送到默认分支。
2. 在仓库的 **Actions** 页面启用工作流。
3. 打开 **Daily LLM & Agent repositories**，点击 **Run workflow** 手动验证。
4. 确认飞书收到卡片；之后工作流每天 `02:00 UTC` 运行，对应北京时间 10:00。

GitHub 官方说明定时工作流在平台繁忙时可能排队，因此 10:00 是触发时间，消息偶尔会延迟几分钟。

## 本地测试

项目只使用 Python 标准库：

```bash
python -m unittest discover -s tests -v
```

本地执行采集需要可访问 GitHub API。可选地通过当前进程环境变量提供 Token，以提高 Search API 配额：

```bash
python scripts/collect_repos.py
python scripts/send_feishu.py output/repos.json --dry-run
```

不要把 Webhook、签名密钥或 Token 写进仓库文件。
