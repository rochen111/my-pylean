# Copilot Workspace Instructions

When a request is about discovering GitHub repositories for niche topics, hidden gems, emerging projects, or topic-focused alternatives:

1. Prefer the `github-niche-repo-scout` skill workflow.
2. If a subagent is appropriate, use the `GitHub Niche Repo Scout` agent.
3. Use transparent scoring and report it explicitly:
   - Topic relevance: 0-35
   - Semantic fit: 0-20
   - Maintenance freshness: 0-20
   - Community confidence: 0-15
   - Novelty with credibility: 0-10
4. Improve discoverability with topic-first search:
   - Discover topic tags first
   - Use topic search qualifiers where useful: `is:curated`, `is:featured`, `repositories:>n`, `created:>YYYY-MM-DD`
   - Use `topic:<tag>` queries during repository search
5. Always include maintenance and quality checks:
   - Last activity recency
   - Archived/dormant status
   - Deprecated/unmaintained signals
   - License clarity
   - Documentation quality
   - Originality checks (prefer non-fork, non-template, non-mirror unless justified)
6. Return practical, decision-ready output:
   - Ranked shortlist table
   - One-line rationale per repo
   - Scenario picks (starter, production, experimental)
   - Caveats and unknowns

For non-repo-discovery coding tasks, follow normal project instructions and do not force this workflow.

## Usage Examples
1. Find hidden gems on GitHub for backtesting with moving averages and measured moves.
2. Find niche repositories for Rust observability agents that are active, original, and non-deprecated.
3. Find topic-focused alternatives to mainstream feature flags platforms for self-hosted deployments.
4. Find emerging open source projects for synthetic data generation in healthcare with clear licensing.
5. Find niche repos for event sourcing in .NET with scenario picks for starter and production use.

## References and Provenance
- Workflow direction informed by Awesome Copilot patterns: https://github.com/github/awesome-copilot
- Topic-first discoverability guidance adapted from GitHub Docs: https://github.com/github/docs/blob/main/content/search-github/searching-on-github/searching-topics.md
- Repository search topic qualifier reference: https://github.com/github/docs/blob/main/content/search-github/searching-on-github/searching-for-repositories.md
- This instruction file is adapted for workspace-specific auto-routing and quality standards.
