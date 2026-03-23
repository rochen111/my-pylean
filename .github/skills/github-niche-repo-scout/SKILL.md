---
name: github-niche-repo-scout
description: 'Discover and rank niche-topic GitHub repositories with transparent scoring, maintenance checks, and practical shortlist output. Use when the user asks to find niche repos, hidden gems, emerging projects, or topic-focused alternatives.'
---

# GitHub Niche Repo Scout

## Goal
Produce a high-quality shortlist of niche GitHub repositories for a specific topic.

## Trigger Phrases
- "find niche repos"
- "hidden gems on github"
- "emerging open source projects"
- "repos for [topic]"
- "alternatives to [popular repo]"

## Inputs
- Topic or problem area
- Optional stack constraints (language/framework)
- Optional quality constraints (active maintenance, license, stars range)
- Optional exclusions

## Process
1. Normalize scope:
- Convert the request into a precise niche statement.
- Expand with synonyms and adjacent terms.

2. Discover and validate topic tags first:
- Search topic names and related terms.
- Use topic qualifiers when helpful: `is:curated`, `is:featured`, `is:not-curated`, `repositories:>n`, `created:>YYYY-MM-DD`.
- Build a short list of high-signal topic tags before repository search.

3. Build repository search variants:
- Phrase queries
- Language-constrained queries
- Topic-tag queries using `topic:<tag>`
- Include/exclude filters

4. Candidate collection:
- Aggregate from multiple query variants.
- Deduplicate by owner/repo.
- Prefer primary repositories (`fork:false`) for originality.
- Keep a broad pool before ranking.

5. Candidate evaluation rubric:
- Topic relevance (0-35)
- Semantic match from description/README (0-20)
- Maintenance freshness (0-20)
- Community confidence (0-15)
- Novelty while still credible (0-10)

6. Risk checks:
- Archived or dormant repos
- Deprecation or unmaintained notices in README/repo metadata
- Weak documentation
- Missing or unclear license
- Fork/template/mirror indicators that reduce originality
- Low signal-to-noise quality

7. Final curation:
- Return top results with concise rationale.
- Add scenario-based picks (best starter, best production-ready, best experimental).

## Output Template
### Top N Niche Repositories

| Rank | Repository | Niche Fit | Activity | Score | Why It Matters |
|---|---|---|---|---:|---|
| 1 | owner/repo | High | Active in last 90 days | 88 | Strong fit for X |

Include these quality fields in the table or inline rationale:
- Last activity recency
- Deprecated status
- Archived status
- License clarity
- Originality notes (fork/template/mirror)

### Best Picks by Scenario
- Starter-friendly:
- Production-focused:
- Experimental/innovative:

### Caveats
- Note data gaps and assumptions.
- Note any trade-offs in the top-ranked projects.

## Rules
- Be transparent about unknowns.
- Keep scoring consistent across candidates.
- Prefer practical recommendations over generic popularity.
- Use topic discovery before repository ranking when topic tags are ambiguous.
- Prefer active and non-deprecated projects unless the user asks for historical references.

## References and Provenance
- Based on customization patterns from Awesome Copilot: https://github.com/github/awesome-copilot
- Topic-search qualifier guidance adapted from GitHub Docs: https://github.com/github/docs/blob/main/content/search-github/searching-on-github/searching-topics.md
- Repository topic query approach (`topic:<tag>`) aligned with GitHub search docs: https://github.com/github/docs/blob/main/content/search-github/searching-on-github/searching-for-repositories.md
- This file contains workspace-specific adaptation for niche repository scouting and scoring.

## Usage Examples
1. Find niche repos for event-driven backtesting in Python, active in the last 180 days, MIT or Apache only.
2. Find hidden gems for Rust time-series anomaly detection with `topic:anomaly-detection` and exclude archived repos.
3. Find alternatives to a mainstream MLOps repo focused on lightweight self-hosted deployment.
4. Find emerging open source projects for browser automation testing with Playwright and low star-count bias.
5. Find niche repos for crypto market microstructure research, prioritize original non-fork repositories.
