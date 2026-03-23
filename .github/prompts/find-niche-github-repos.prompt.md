---
description: 'Generate a ranked shortlist of niche-topic GitHub repositories with transparent scoring and maintenance checks.'
---

Find niche-topic GitHub repositories for: ${input:topic}

Constraints:
- Preferred languages/frameworks: ${input:stack}
- Minimum maintenance expectations: ${input:maintenance}
- Exclusions (topics/repos): ${input:exclusions}
- Number of recommendations: ${input:count}

Requirements:
1. Discover topic tags first using topic search qualifiers where useful: is:curated, is:featured, repositories:>n, created:>YYYY-MM-DD.
2. Use multiple repository search variants (topic terms, synonyms, topic:<tag>, stack filters, and fork:false when originality matters).
3. Gather a broad candidate pool before final ranking.
4. Score each candidate using:
- 35% topic relevance
- 20% semantic fit
- 20% maintenance freshness
- 15% community confidence
- 10% novelty
5. Apply trust filters and flags:
- Active recency
- Deprecated/unmaintained signals
- Archived status
- License clarity
- Originality (fork/template/mirror)
6. Return:
- A ranked markdown table
- Top 3 picks with use-case fit
- Caveats and assumptions

## References and Provenance
- Prompt structure informed by Awesome Copilot customization patterns: https://github.com/github/awesome-copilot
- Topic-search qualifier usage adapted from GitHub Docs: https://github.com/github/docs/blob/main/content/search-github/searching-on-github/searching-topics.md
- Repository topic qualifier reference (`topic:<tag>`): https://github.com/github/docs/blob/main/content/search-github/searching-on-github/searching-for-repositories.md
- This prompt is customized for this workspace's niche-repo scouting workflow.

## Usage Examples
1. Topic: moving average backtesting with measured moves; Stack: Python; Maintenance: active in 180 days; Exclusions: archived, forks; Count: 10.
2. Topic: topic-modeling libraries for legal documents; Stack: Python, Rust; Maintenance: active in 365 days; Exclusions: deprecated; Count: 8.
3. Topic: real-time CDC to lakehouse pipelines; Stack: Go, Java; Maintenance: releases in last year; Exclusions: GPL; Count: 12.
4. Topic: lightweight vector databases for edge devices; Stack: C++, Rust; Maintenance: active in 180 days; Exclusions: templates; Count: 7.
5. Topic: open source options backtesting engines; Stack: Python; Maintenance: active in 90 days; Exclusions: unlicensed repos; Count: 10.
