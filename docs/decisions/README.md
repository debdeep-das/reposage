# Architecture Decision Records

This directory documents the non-obvious technical choices made while building
RepoSage. Each ADR captures the context that surrounded a decision, the options
considered, the call we actually made, and what would cause us to revisit it.

The format is a light variant of [Michael Nygard's ADR template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
ADRs are immutable once accepted; if a decision is reversed, a new ADR supersedes
the old one rather than editing it in place.

## Index

| ADR | Title | Status |
|---|---|---|
| [0006](0006-disable-similarity-threshold-v1.md) | Ship v1 with the cosine-similarity threshold disabled | Accepted |

More ADRs will be added as the build progresses. The numbering reflects topic
groups (embedder, chunker, retrieval, etc.), not chronology.
