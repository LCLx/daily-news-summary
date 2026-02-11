# News Summary — 需求文档

## Phase 1（已完成）

**目标：** 每日自动抓取新闻，用 Claude 总结成中文，通过邮件发送。

### 已实现功能

- **RSS 抓取**：4 个分类（国际政治、经济商业、科技 AI、健康科学），共 11 个来源
- **过滤逻辑**：只抓最近 24 小时内的文章
- **图片提取**：多策略提取文章配图（media_thumbnail / media_content / HTML img）
- **Claude 摘要**：调用 Anthropic API，输出中文 markdown 格式摘要
- **HTML 邮件**：渲染成格式化 HTML，通过 Resend 发送
- **自动化调度**：GitHub Actions，每天 08:00 PST 运行
- **测试**：RSS 可达性测试 + Claude pipeline 预览测试
- **成本优化**：Haiku 模型，约 $0.014/次，$0.42/月

---

## Phase 2（待定义）

> 在下方描述你的需求，越具体越好。

### 需求列表

<!-- 在此添加 Phase 2 的功能需求 -->