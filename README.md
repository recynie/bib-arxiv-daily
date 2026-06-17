# bib-arxiv-daily

[简体中文说明 / Chinese README](./README.zh-CN.md)

`bib-arxiv-daily` recommends newly announced arXiv papers based on the papers in your local `.bib` files, then publishes the results to GitHub Pages on a daily schedule using GitHub Actions. It also includes a manual workflow for a last-7-days top-10 recommendation run.

So this project works both as a daily recommender and as a search tool that ranks arXiv papers against your own `.bib` library. For "find papers close to my research taste" style queries, it is often more useful than plain keyword-and-field filtering.

You can run it locally to generate an HTML report, or let GitHub Actions run it on schedule and deploy the results automatically to GitHub Pages.

This repository is designed for beginners:

- You put one or more `.bib` files under `data/`
- You choose a few arXiv categories in `config.yaml`
- GitHub Actions runs every day
- The workflow deploys an HTML page with arXiv and PDF links, and builds a browsable archive of all daily reports

The current version does not use OpenAI, Claude, or any paid LLM API. It uses an open-source embedding model locally on the GitHub Actions runner.

## What This Project Does

1. Read every `.bib` file under `data/**/*.bib`
2. Keep entries that have both `title` and `abstract`
3. Fetch newly announced arXiv papers from the categories you configured, and fall back to `https://export.arxiv.org/api/query` over the last 24 hours when RSS is temporarily empty
4. Compute text embeddings for your library papers and the new arXiv candidates
5. Rank candidates by similarity to your library
6. Generate an HTML report and deploy it to GitHub Pages

You can also trigger a manual weekly run that queries arXiv submissions from the last `7` days through the export API and ranks the top `10` closest matches.

Each daily report includes:

- paper title
- score
- authors
- abstract snippet
- arXiv link
- PDF link
- the closest matching papers from your `.bib` library

All reports are preserved by date under `docs/YYYY/MM/DD/`. The site index page shows the latest report and a full history.

## Repository Layout

```text
.
├── data/                     # Put one or more .bib files here
├── docs/                     # Generated HTML reports (GitHub Pages source)
│   ├── index.html            # Site index (latest report + history)
│   └── 2026/06/12/index.html # Daily reports by date
├── scripts/
│   └── clean_bib.py          # Strip bib entries to only the fields the project uses
├── src/
│   ├── bib_loader.py
│   ├── arxiv_fetcher.py
│   ├── embedder.py
│   ├── embedding_cache.py
│   ├── recommender.py
│   ├── report_builder.py     # HTML report generation
│   ├── index_builder.py      # Site index generation
│   └── main.py
├── config.yaml               # Non-secret configuration
├── requirements.txt
└── .github/workflows/
    ├── daily.yml
    └── manual-weekly-top10.yml
```

## Before You Start

You need:

- a GitHub repository
- one or more `.bib` files with abstracts

Important:

- `data/library.bib` is listed in `.gitignore` and will **not** be committed to Git. In CI (GitHub Actions), its content is restored from a repository secret.
- Other `.bib` files you add under `data/` will be tracked by Git. If you have private bibliographies, keep them in a private repository or add them to `.gitignore`.

## Quick Start

### 1. Put your `.bib` files into `data/`

This project supports multiple `.bib` files.

Examples:

```text
data/library.example.bib        # Example file, tracked by Git
data/library.bib                # Your personal library, NOT tracked (see .gitignore)
data/reading/ml.bib             # You can add more .bib files manually
data/reading/vision.bib
```

Minimal working BibTeX entry:

```bibtex
@article{attention2023,
  title   = {A Paper Title},
  abstract = {This abstract is required for similarity matching.}
}
```

The project only reads `title`, `abstract`, `author`, `doi`, `eprint`, `archiveprefix`, and `url` from bib entries.
Fields like `year`, `journal`, `volume`, `pages`, `keywords`, `file`, `publisher`, and `urldate` are **ignored**.

If an entry does not contain an `abstract`, it is skipped.

> **Note for CI users:** `data/library.bib` is ignored by Git. In GitHub Actions, its content is restored from the `LIBRARY_BIB_BASE64` repository secret (a base64-encoded copy of your bib file).
> See [GitHub Actions Configuration](#3-github-actions-configuration-secret-setup) below to set it up.

### 2. Edit `config.yaml`

Start with categories that are close to your research area. Do not use too many categories at first.

Example:

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

Advice for beginners:

- Start with `2` to `4` categories
- Keep `max_candidates` around `50` to `100`
- Leave the embedding model as default first

## GitHub Pages Setup

### 1. Enable GitHub Pages for the repository

Open:

`Settings` -> `Pages`

Under **Branch**:

- Select `main` branch
- Select `/docs` folder
- Click **Save**

GitHub will provide a URL like `https://<username>.github.io/<repository>/`.

### 2. Enable GitHub Actions for the repository

Open:

`Settings` -> `Actions` -> `General`

Recommended settings for beginners:

- `Actions permissions`: `Allow all actions and reusable workflows`
- `Workflow permissions`: `Read and write permissions` (the workflow needs to commit to the repository)

### 3. If this is a fork, enable workflows in the Actions tab

GitHub official docs say:

- workflows do not run in forked repositories by default
- scheduled workflows are disabled by default in public forks
- scheduled workflows in public repositories can also be automatically disabled after 60 days of no repository activity

So after forking:

1. Open the `Actions` tab
2. Click the button to enable workflows
3. If the schedule stops later, re-enable the workflow in the Actions UI

GitHub official references:

- Events in forks: https://docs.github.com/en/actions/reference/events-that-trigger-workflows
- Disable/enable workflows: https://docs.github.com/actions/managing-workflow-runs/disabling-and-enabling-a-workflow

### 3. GitHub Actions Configuration (Secret Setup)

Because `data/library.bib` is not tracked by Git (see `.gitignore`), CI workflows need its content provided via a **GitHub repository secret**.

#### Step 1: Base64-encode your library.bib

```bash
base64 -w0 data/library.bib | pbcopy   # macOS
# or
base64 -w0 data/library.bib            # Linux — then select and copy the output
```

> The `-w0` flag produces a single-line base64 string without line breaks, which works reliably as a GitHub secret.

#### Step 2: Add the secret

1. Go to your GitHub repository page
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. **Name**: `LIBRARY_BIB_BASE64`
5. **Secret**: Paste the base64 output from step 1
6. Click **Add secret**

That is all. When the workflows run, they will decode this secret into `data/library.bib` before executing the main program.

> If `LIBRARY_BIB_BASE64` is not set, the workflow falls back to `data/library.example.bib` so the pipeline does not break.

> **Note:** If you previously added `LIBRARY_BIB` (raw text), you can remove it — it is no longer used.

## First Manual Test

After you commit your files and set up the secret:

1. Open the `Actions` tab
2. Open the `arxiv-daily` workflow
3. Click `Run workflow`
4. Wait for the run to finish

What to look for in the logs:

- `Restored library.bib` appears early in the run
- `library loaded successfully`
- arXiv papers fetched successfully
- `Saved ... library embeddings to cache ...` on the first run
- `Loaded ... library embeddings from cache ...` on later runs
- `Wrote HTML report to ...`
- `Rebuilt index page at ...`

After the run finishes, check:

- The `docs/` directory now contains `YYYY/MM/DD/index.html`
- Your GitHub Pages URL shows the latest report
- The index page includes a link to the report

If you want a manual weekly summary instead of the normal daily run:

1. Open the `Actions` tab
2. Open the `arxiv-weekly-manual-top10` workflow
3. Click `Run workflow`
4. Wait for the run to finish

That workflow is manual-only. It queries the last `7` days of arXiv submissions through the export API, keeps up to `500` candidates, ranks them against your `.bib` library, and deploys the top `10` matches.

## Daily Schedule

The current workflow schedule is defined in:

- [`.github/workflows/daily.yml`](./.github/workflows/daily.yml)

Current cron:

```yaml
schedule:
  - cron: "30 6 * * *"
```

That means the workflow runs at `06:30 UTC` every day.

If you want a different time, edit the cron line and commit the change.

## Manual Weekly Workflow

The repository also includes:

- [`.github/workflows/manual-weekly-top10.yml`](./.github/workflows/manual-weekly-top10.yml)

This workflow has `workflow_dispatch` only. It does not run on a schedule.

Current fixed behavior:

- query arXiv papers submitted in the last `7` days
- use the export API directly instead of RSS
- score up to `500` candidates
- deploy the top `10` matches

## Model Used

This project currently uses the open-source embedding model:

- `BAAI/bge-small-en-v1.5`

It is loaded through `sentence-transformers` and runs locally on the GitHub runner.

Important:

- This is an embedding model, not a chat model
- It is used only for text similarity
- No OpenAI API key is required
- No per-token API billing is involved

Model card:

- https://huggingface.co/BAAI/bge-small-en-v1.5

## Runtime and Time Cost

The main runtime factors are:

1. dependency installation
2. PyTorch installation
3. first-time model download
4. number of `.bib` entries with abstracts
5. number of new arXiv candidates
6. GitHub Actions cache hit or miss
7. network speed to GitHub, Hugging Face, and arXiv

This repository now caches:

- Hugging Face model files
- library embeddings in `.cache/recommender`

That means:

- if your `.bib` files do not change, library embeddings are reused
- only the daily arXiv candidates need fresh embedding work

Rough runtime estimates on standard `ubuntu-latest` runners are:

- first cold run: about `5` to `12` minutes
- normal warm run with cache hit: about `1` to `4` minutes
- large libraries with thousands of papers: can be much slower

These are practical estimates, not hard guarantees.

GitHub official runner reference for standard public runners:

- `ubuntu-latest` standard runner: `4 vCPU`, `16 GB RAM`, `14 GB SSD`
- source: https://docs.github.com/en/actions/reference/github-hosted-runners-reference

## GitHub Actions Free Minutes

This part changes over time, so the numbers below are verified against GitHub Docs as of `2026-03-07`.

### Public repositories

For standard GitHub-hosted runners, GitHub Actions usage is free and unlimited in public repositories.

### Private repositories

Included monthly minutes for standard GitHub-hosted runners:

| Plan | Included minutes per month |
| --- | ---: |
| GitHub Free | 2,000 |
| GitHub Pro | 3,000 |
| GitHub Free for organizations | 2,000 |
| GitHub Team | 3,000 |
| GitHub Enterprise Cloud | 50,000 |

Notes:

- larger runners are billed separately
- if your account has no valid payment method, usage is blocked after the included quota is exhausted
- storage for artifacts and caches also has plan limits

Official references:

- Billing overview: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions
- Included usage table: https://docs.github.com/en/billing/reference/product-usage-included

## Recommended Beginner Setup

If you want the simplest path:

1. Use a private GitHub repository if your bibliography is private
2. Put only a few `.bib` files under `data/`
3. Use `2` to `4` arXiv categories
4. Enable GitHub Pages with `/docs` folder
5. Trigger the workflow manually first
6. Check that cache hits appear on the second run

## Local Run

If you want to test locally before using GitHub Actions:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/main.py --config config.yaml
```

The HTML report will be written to the path specified in `config.yaml` (default: `output/latest_report.html`).

To reproduce the manual weekly top-10 workflow locally:

```bash
.venv/bin/python src/main.py --config config.yaml --lookback-days 7 --max-candidates 500 --max-results 10 --output-html output/manual_weekly_top10_report.html
```

Useful CLI overrides:

- `--lookback-days N`: query the last `N` days through the arXiv export API instead of RSS new announcements
- `--max-candidates N`: override `arxiv.max_candidates` from `config.yaml`
- `--max-results N`: override `ranking.max_results` from `config.yaml`
- `--output-html PATH`: write the rendered report to a custom path

## Troubleshooting

### RSS returns 0 papers

There are two different cases:

- weekends or holidays, when arXiv may simply have no new announcement batch for your categories
- the RSS blank window, where the daily announcement is already visible but `rss.arxiv.org` has not caught up yet

In practice this means you can sometimes see:

- arXiv daily announcement is already online
- `RSS new papers = 0`
- a few hours later the RSS feed starts returning entries normally

This repository now handles that gap automatically:

- it still checks RSS first
- if RSS returns `0` new ids, it falls back to `https://export.arxiv.org/api/query`
- the fallback searches `submittedDate` in the last `24` hours for your configured categories

This fallback helps during the RSS propagation lag, but it does not magically create papers on days when arXiv really did not release a new batch.

### No report appears on GitHub Pages

Check:

- whether the workflow succeeded
- whether GitHub Pages is configured to use the `main` branch `/docs` folder
- whether the `docs/` directory was committed and pushed
- whether the Pages build completed (see the Environment section in the repository)

### Workflow is visible but does not run on schedule

Check:

- whether Actions are enabled for the repository
- whether the workflow was disabled manually
- whether this is a fork and scheduled workflows were disabled by default
- whether the repository was inactive long enough for GitHub to disable scheduled workflows automatically

### The first run is very slow

That is expected if:

- dependencies are being installed for the first time
- the embedding model is downloaded for the first time
- your library cache has not been built yet

### Too many irrelevant recommendations

Usually fix this by:

- narrowing your arXiv categories
- reducing `max_candidates`
- cleaning low-quality `.bib` entries
- removing entries without meaningful abstracts

### Optional: Clean your bib files

The project provides a utility script to strip bib entries down to the fields it actually uses:

```bash
python scripts/clean_bib.py data/library.bib        # in-place
python scripts/clean_bib.py data/library.bib -o clean.bib  # safe mode
```

This removes fields like `year`, `journal`, `keywords`, `file`, and `urldate` that the embedding and recommendation pipeline never looks at.

## Current Limitations

- no PDF attachments (links only)
- no full-text search (recommendations rely on title + abstract)
- entries without `abstract` are skipped

## References

- GitHub Pages docs:
  https://docs.github.com/en/pages
- GitHub Actions repository settings:
  https://docs.github.com/github/administering-a-repository/managing-repository-settings/disabling-or-limiting-github-actions-for-a-repository
- GitHub workflow enable/disable:
  https://docs.github.com/actions/managing-workflow-runs/disabling-and-enabling-a-workflow
- GitHub Actions billing:
  https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions
- GitHub included usage:
  https://docs.github.com/en/billing/reference/product-usage-included
- GitHub-hosted runner specs:
  https://docs.github.com/en/actions/reference/github-hosted-runners-reference
