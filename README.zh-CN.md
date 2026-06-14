# bib-arxiv-daily

[English README](./README.md)

`bib-arxiv-daily` 会根据你放在本仓库中的 `.bib` 文件，去匹配每天新发布的 arXiv 论文，然后通过 GitHub Actions 每天自动把结果部署到 GitHub Pages。仓库里还提供了一个"最近 7 天 + 最接近 10 篇"的手动工作流。

所以，这个项目既可以作为一个每天自动推荐相关论文的工具，也可以作为一个基于你自己的 `.bib` 馆藏做语义检索和排序的搜索工具。对于"按研究兴趣找论文"这类场景，它通常会比纯关键词加字段过滤更顺手。

你既可以在本地手动运行、生成 HTML 报告并直接在浏览器里查看，也可以交给 GitHub Actions 每天定时执行并部署到 GitHub Pages。

这个仓库是按"小白可上手"来设计的：

- 你把一个或多个 `.bib` 文件放到 `data/`
- 你在 `config.yaml` 里配置几个 arXiv 分类
- GitHub Actions 每天自动运行
- 工作流把推荐结果部署到 GitHub Pages，所有历史按日期保留

当前版本不使用 OpenAI、Claude 或任何付费大模型 API。它在 GitHub Actions 运行器上本地调用开源 embedding 模型。

## 这个项目会做什么

1. 读取 `data/**/*.bib` 下的所有 `.bib` 文件
2. 保留同时包含 `title` 和 `abstract` 的条目
3. 优先抓取你配置的 arXiv 分类 RSS；如果 RSS 临时为空，则退回到 `https://export.arxiv.org/api/query` 查询最近 `24` 小时提交的论文
4. 计算你的馆藏论文和候选论文的文本向量
5. 根据相似度排序
6. 生成 HTML 报告并部署到 GitHub Pages

你也可以手动触发一个周报流程：直接查询最近 `7` 天提交到 arXiv 的论文，筛出最接近你 bib 库的前 `10` 篇并部署。

每篇日报包含：

- 论文标题
- 相似度分数
- 作者
- 摘要片段
- arXiv 链接
- PDF 链接
- 与你 bib 库最接近的几篇论文标题

所有报告按日期保存在 `docs/YYYY/MM/DD/` 下，站点首页展示最新报告和完整历史。

## 仓库结构

```text
.
├── data/                     # 把一个或多个 .bib 文件放这里
├── docs/                     # 生成的 HTML 报告（GitHub Pages 源）
│   ├── index.html            # 站点首页（最新报告 + 历史列表）
│   └── 2026/06/12/index.html # 按日期保存的日报
├── src/
│   ├── bib_loader.py
│   ├── arxiv_fetcher.py
│   ├── embedder.py
│   ├── embedding_cache.py
│   ├── recommender.py
│   ├── report_builder.py     # HTML 报告生成
│   ├── index_builder.py      # 站点首页生成
│   └── main.py
├── config.yaml               # 非私密配置
├── requirements.txt
└── .github/workflows/
    ├── daily.yml
    └── manual-weekly-top10.yml
```

## 开始前你需要准备什么

你需要：

- 一个 GitHub 仓库
- 一个或多个带摘要的 `.bib` 文件

重要提醒：

- `data/*.bib` 会作为仓库内容提交到 Git 历史里。如果你的书目库是私密的，不要放在公开仓库里。

## 快速开始

### 1. 把 `.bib` 文件放到 `data/` 目录

支持多个 `.bib` 文件，例如：

```text
data/library.example.bib
data/reading/ml.bib
data/reading/vision.bib
```

最小可用的 BibTeX 示例：

```bibtex
@article{attention2023,
  title = {A Paper Title},
  abstract = {This abstract is required for similarity matching.},
  author = {Alice Example and Bob Example},
  year = {2023}
}
```

如果某个条目没有 `abstract`，当前版本会直接跳过。

### 2. 修改 `config.yaml`

先从和自己研究方向最相关的少量 arXiv 分类开始，不要一上来配太多。

示例：

```yaml
arxiv:
  categories:
    - cs.LG
    - cs.AI
    - cs.CL
  max_candidates: 80

embedding:
  model: BAAI/bge-small-en-v1.5
  batch_size: 32

ranking:
  top_k_neighbors: 5
  max_results: 15

runtime:
  data_dir: data
  output_html: output/latest_report.html
  cache_dir: .cache/recommender
```

给新手的建议：

- 一开始先用 `2` 到 `4` 个分类
- `max_candidates` 先控制在 `50` 到 `100`
- embedding 模型先不要改，先跑通默认值

## GitHub Pages 设置

### 1. 为仓库启用 GitHub Pages

打开：

`Settings` -> `Pages`

在 **Branch** 部分：

- 选择 `main` 分支
- 选择 `/docs` 文件夹
- 点击 **Save**

GitHub 会提供一个像 `https://<用户名>.github.io/<仓库名>/` 这样的 URL。

### 2. 启用 GitHub Actions

打开：

`Settings` -> `Actions` -> `General`

给新手的推荐设置：

- `Actions permissions`: 选择 `Allow all actions and reusable workflows`
- `Workflow permissions`: 选择 `Read and write permissions`（工作流需要提交代码到仓库）

### 3. 如果这是 fork 出来的仓库，要在 Actions 页面手动启用工作流

GitHub 官方文档说明：

- fork 仓库默认不会自动运行工作流
- public fork 上的定时工作流默认是关闭的
- public 仓库如果长期没有活动，定时工作流也可能在 60 天后被自动禁用

所以你 fork 完之后要做：

1. 打开 `Actions` 页面
2. 点击启用 workflows
3. 如果以后定时任务不跑了，再到 Actions 页面里重新启用

GitHub 官方参考：

- fork 里的工作流事件：
  https://docs.github.com/en/actions/reference/events-that-trigger-workflows
- 工作流启用/禁用：
  https://docs.github.com/actions/managing-workflow-runs/disabling-and-enabling-a-workflow

## 第一次手动测试怎么做

把文件都准备好后：

1. 打开 `Actions`
2. 打开 `arxiv-daily` 这个 workflow
3. 点击 `Run workflow`
4. 等它跑完

日志里重点看这些信息：

- bib 库是否成功加载
- arXiv 是否成功抓取
- 第一次运行会出现 `Saved ... library embeddings to cache ...`
- 后续运行会出现 `Loaded ... library embeddings from cache ...`
- `Wrote HTML report to ...`
- `Rebuilt index page at ...`

跑完之后检查：

- `docs/` 目录下生成了 `YYYY/MM/DD/index.html`
- 你的 GitHub Pages 页面显示了最新的报告
- 首页包含指向该报告的链接

如果你想跑一次手动周报，而不是普通的日更流程：

1. 打开 `Actions`
2. 打开 `arxiv-weekly-manual-top10` 这个 workflow
3. 点击 `Run workflow`
4. 等它跑完

这个工作流只支持手动触发。它会直接使用 export API 查询最近 `7` 天的 arXiv 提交，最多打分 `500` 篇候选论文，并部署最接近的 `10` 篇。

## 每天什么时候运行

当前定时配置在：

- [`.github/workflows/daily.yml`](./.github/workflows/daily.yml)

现在的 cron 是：

```yaml
schedule:
  - cron: "30 6 * * *"
```

这表示每天 `06:30 UTC` 运行一次。也就是北京时间下午 14:30。

如果你想改时间，直接修改 cron 后提交即可。

## 手动周报工作流

仓库里还包含：

- [`.github/workflows/manual-weekly-top10.yml`](./.github/workflows/manual-weekly-top10.yml)

这个工作流只有 `workflow_dispatch`，不会自动定时运行。

当前固定行为：

- 查询最近 `7` 天提交的 arXiv 论文
- 直接走 export API，不依赖 RSS 当日公告
- 最多打分 `500` 篇候选论文
- 部署最接近的前 `10` 篇

## 当前使用的模型

当前仓库使用的开源 embedding 模型是：

- `BAAI/bge-small-en-v1.5`

它通过 `sentence-transformers` 加载，在 GitHub Actions 运行器本地执行。

要点：

- 这是 embedding 模型，不是对话大模型
- 只用于文本相似度计算
- 不需要 OpenAI API key
- 没有按 token 计费

模型卡：

- https://huggingface.co/BAAI/bge-small-en-v1.5

## 耗时主要受什么影响

主要耗时因素有：

1. 依赖安装
2. PyTorch 安装
3. 首次下载 embedding 模型
4. 你的 `.bib` 中带摘要条目的数量
5. 每天 arXiv 候选论文数
6. GitHub Actions 缓存是否命中
7. GitHub、Hugging Face、arXiv 的网络情况

当前仓库已经缓存了：

- Hugging Face 模型文件
- `.cache/recommender` 下的 library embeddings

这意味着：

- 只要你的 `.bib` 没变，馆藏向量就会复用
- 每天只需要重新算新抓到的 arXiv 候选论文

在标准 `ubuntu-latest` runner 上，粗略经验值是：

- 第一次冷启动：约 `5` 到 `12` 分钟
- 正常热启动且缓存命中：约 `1` 到 `4` 分钟
- 如果 bib 很大，达到几千篇，可能明显更慢

这些是工程经验估计，不是 GitHub 官方保证。

GitHub 官方标准 public runner 规格：

- `ubuntu-latest` 标准 runner：`4 vCPU`、`16 GB RAM`、`14 GB SSD`
- 来源：
  https://docs.github.com/en/actions/reference/github-hosted-runners-reference

## GitHub Actions 免费分钟数

这部分可能会变，所以我这里写的是截至 `2026-03-07` 通过 GitHub 官方文档核对过的数字。

### Public 仓库

使用标准 GitHub-hosted runners 时，public 仓库的 GitHub Actions 是免费且不限量的。

### Private 仓库

标准 GitHub-hosted runners 的每月包含分钟数如下：

| 套餐 | 每月包含分钟数 |
| --- | ---: |
| GitHub Free | 2,000 |
| GitHub Pro | 3,000 |
| GitHub Free for organizations | 2,000 |
| GitHub Team | 3,000 |
| GitHub Enterprise Cloud | 50,000 |

补充说明：

- larger runners 另行计费
- 如果账户没有有效付款方式，超出包含额度后会被阻止继续使用
- artifacts 和 caches 的存储空间也有套餐上限

GitHub 官方参考：

- 计费总览：
  https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions
- 套餐包含额度：
  https://docs.github.com/en/billing/reference/product-usage-included

## 给小白的推荐方案

如果你想用最省心的方式跑起来：

1. 如果书目是私密的，就用 private 仓库
2. 先只放少量 `.bib` 文件到 `data/`
3. 先选 `2` 到 `4` 个 arXiv 分类
4. 配置 GitHub Pages 使用 `/docs` 文件夹
5. 先手动触发一次 workflow
6. 第二次运行时确认日志里出现 cache hit

## 本地运行

如果你想在上 GitHub Actions 之前先本地测试：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/main.py --config config.yaml
```

HTML 报告会输出到 `config.yaml` 中 `runtime.output_html` 指定的路径（默认 `output/latest_report.html`）。

如果你想在本地复现"手动周报 top 10"流程，可以运行：

```bash
.venv/bin/python src/main.py --config config.yaml --lookback-days 7 --max-candidates 500 --max-results 10 --output-html output/manual_weekly_top10_report.html
```

几个有用的 CLI 覆盖参数：

- `--lookback-days N`：改成直接查最近 `N` 天的 arXiv 提交，不走 RSS new announcement
- `--max-candidates N`：覆盖 `config.yaml` 里的 `arxiv.max_candidates`
- `--max-results N`：覆盖 `config.yaml` 里的 `ranking.max_results`
- `--output-html PATH`：把 HTML 报告输出到自定义路径

## 常见问题排查

### RSS 没有条目

这里要区分两种情况：

- 周末或节假日，arXiv 本来就可能没有新的 announcement 批次
- RSS 空白期：announcement 已经出了，但 `rss.arxiv.org` 还没同步完成

所以你有时会看到这种现象：

- arXiv 当天的 announcement 已经能看到了
- 但是程序日志里还是 `RSS new papers = 0`
- 再过几个小时，RSS 才恢复正常返回

这就是所谓的 RSS 空白期。

当前仓库已经做了自动兜底：

- 先查 RSS
- 如果 RSS 返回 `0` 个新 id
- 就自动退回到 `https://export.arxiv.org/api/query`
- 用你配置的分类去查最近 `24` 小时的 `submittedDate`

这个兜底可以覆盖 announcement 已出、RSS 还没刷新的那段空白时间；但如果周末确实没有新论文批次，它也不会凭空产生结果。

### GitHub Pages 上没有显示报告

请检查：

- workflow 是否成功
- GitHub Pages 是否配置为使用 `main` 分支的 `/docs` 文件夹
- `docs/` 目录是否被提交并推送到了仓库
- Pages 构建是否完成（在仓库的 Environment 部分查看）

### Workflow 能看到但不会定时跑

请检查：

- 仓库是否启用了 GitHub Actions
- workflow 是否被手动禁用了
- 是否是 fork 仓库导致 schedule 默认关闭
- 是否因为仓库长时间无活动而被 GitHub 自动禁用 schedule

### 第一次运行很慢

这通常是正常的，因为第一次要做：

- 安装依赖
- 下载 embedding 模型
- 构建馆藏 embedding 缓存

### 推荐结果不太准

通常可以从这几个地方改：

- 缩小 arXiv 分类范围
- 降低 `max_candidates`
- 清理质量较差的 `.bib` 条目
- 去掉没有有效摘要的条目

## 当前限制

- 不发送 PDF 附件（只发链接）
- 推荐只基于标题 + 摘要，不是全文
- 没有 `abstract` 的条目会被跳过

## 参考资料

- GitHub Pages 文档：
  https://docs.github.com/en/pages
- GitHub Actions 仓库设置：
  https://docs.github.com/github/administering-a-repository/managing-repository-settings/disabling-or-limiting-github-actions-for-a-repository
- GitHub workflow 启用/禁用：
  https://docs.github.com/actions/managing-workflow-runs/disabling-and-enabling-a-workflow
- GitHub Actions 计费：
  https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions
- GitHub 套餐包含额度：
  https://docs.github.com/en/billing/reference/product-usage-included
- GitHub-hosted runner 规格：
  https://docs.github.com/en/actions/reference/github-hosted-runners-reference
