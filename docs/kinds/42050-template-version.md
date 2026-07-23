# Kind 42050: Template Version

## Overview

**Kind Number:** 42050  
**Range:** Regular (append-only history)  
**Status:** Draft  

One immutable event per registered template version. Templates are node configurations (system prompts, skills, files, references, DESIGN.md §3) that can be versioned and inherited. The full version history for a template is the set of all kind 42050 events sharing a `template_name` tag, ordered by `created_at`.

## Range Semantics

This kind is in the **420xx** block (≥40000), which per NIP-01 defaults to append-only **regular** events: every version is stored immutably. This is correct for versioning — you need the full history to reconstruct what a template looked like at any point in time, and DESIGN.md §3 requires versions to be "diffable" against each other.

A replaceable event would overwrite historical versions, making diffing impossible. Append-only preserves the complete audit trail.

## Tag Table

| Tag | Meaning | Required? | Format |
|-----|---------|-----------|--------|
| `template_name` | Template's stable name (the key pointer events key off) | yes | string |
| `version` | Monotonic version identifier | yes | string |
| `e` (marker `inherit`) | Parent template version event id, if this version extends another | no | 4-element array: `["e", "<id>", "", "inherit"]` |
| `git_ref` | Commit/tag in templates' git history (if template content is git-hosted) | no | string |

## Content JSON Schema

```json
{
  "summary": "<string, describing what changed this version>"
}
```

The `summary` field is required. It explains the changes in this version relative to the previous one (if any). Kept thin — the template's actual content (system prompts, skills, files) is not duplicated into the event; `git_ref` is the pointer to it, keeping this a registry entry, not a second copy of the artifact (consistent with DESIGN.md §6 principle 2, no new storage systems).

## Worked Example

```json
{
  "kind": 42050,
  "tags": [
    ["template_name", "default-node"],
    ["version", "1.0.0"],
    ["git_ref", "main@abc123d"]
  ],
  "content": "{\"summary\":\"Initial release of default node template\"}",
  "created_at": 1721761206,
  "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "id": "7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f",
  "sig": null
}
```

## Inheritance

A template version can extend another by `e`-tagging it with marker `inherit`:

```json
{
  "kind": 42050,
  "tags": [
    ["template_name", "specialized-node"],
    ["version", "1.0.0"],
    ["e", "7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f", "", "inherit"]
  ],
  "content": "{\"summary\":\"Specialization of default-node with GPU acceleration\"}",
  "created_at": 1721761207,
  "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "id": "8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
  "sig": null
}
```

Inheritance chains are queryable by any Nostr client via ordinary tag filters, no Lindenmayer-specific indexing needed.

## Evals Anchor

DESIGN.md §8 notes that "What an eval attaches to" is the version event's id. This document does not design the evals pillar (explicitly future work) but the Template Version kind's `e`-taggability is sufficient anchor for whatever eval-result kind that future work defines — a single query can retrieve all eval results for a given template version.
