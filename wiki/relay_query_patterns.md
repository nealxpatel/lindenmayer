---
name: relay_query_patterns
desc: How to filter relay queries correctly -- NIP-01 admits only single-letter tag filters, so multi-character constraints must be enforced client-side.
tags: [relay, nostr, nip01, privacy]
sources: [docs/DESIGN.md, src/lindenmayer/evergreen/query.py]
created: 2026-07-24T00:41:53Z
updated: 2026-07-24T00:41:53Z
---

# relay_query_patterns

Read this before writing any relay query that filters on a tag. It
describes a defect that has already shipped in one node's reader and was
caught in another's, and the pattern that avoids it.

## NIP-01 admits only single-letter tag filters

A filter key of the form `#<single-letter>` (`#e`, `#p`, `#d`, ...) is part
of NIP-01. A **multi-character key like `#branch` or `#template_name` is
not.** A compliant relay does not error on it -- it ignores the key and
returns every event matching the remaining terms.

Measured against this tree's dev relay:

```
{"kinds":[42010],"#branch":["main.evergreen"]}   -> 12 events
{"kinds":[42010]}                                -> 12 events (identical)
```

The twelve "filtered" events spanned twelve *different* branches and
included zero `main.evergreen` events. The filter did nothing at all.

Lindenmayer's own wire format leans heavily on multi-character tags --
`branch`, `run`, `iter`, `step`, `status`, `template_name`, `version`,
`git_ref`, `detection`. **None of them is filterable relay-side.** Only
`d`, `e`, and `p` are.

## The rule

Send NIP-01-valid terms to the relay (`kinds`, `authors`, `ids`, `#d`,
`#e`, `#p`) and treat every other constraint as a **client-side** filter
applied after `event.verify()`:

```python
events = await relay.query([{"kinds": [KIND_NODE_LIFECYCLE], "authors": [pubkey]}])
records = [
    parse(e) for e in events
    if e.verify() and e.first_tag_value("branch") == branch
]
```

Sending `#branch` anyway is harmless -- a permissive relay may narrow the
result set for you -- but **correctness must never depend on it.** This is
the same posture DESIGN.md §6 principle 5 already mandates for every other
relay behavior: relay-side enforcement is an optimization, never an
assumption. Apply it to `#d` too; addressable collapse is a relay
convenience, not a guarantee.

## Why this is a privacy defect, not only a correctness one

A query scoped to one branch that silently returns twelve other branches'
events, rendered under that branch's heading, is an **aggregates-up
violation** (§6.1) the moment the output is committed, exported, or
cross-posted. A surface labeled for one subgraph must never carry another
subgraph's rows because a relay declined to filter. Treat a missing
client-side tag check in any published surface as blocking, not cosmetic.

## Do not "fix" this in the mock

`tests/relay_mock.py` matches only single-letter tag keys, which is
**faithful to real relay behavior** -- keep it that way. Widening the mock
to match multi-character keys makes every node's tests pass against
semantics no real relay has, and hides this entire bug class tree-wide.
That change was made and reverted during evergreen's build for exactly this
reason.

The corollary for test design: a fixture with only one branch (or one
template) present cannot detect an ignored filter, because filtered and
unfiltered results coincide. **Put at least two distinct tag values in the
fixture** whenever a test asserts that a tag-scoped query is scoped.

## Known instances

- `src/lindenmayer/evergreen/query.py` -- enforces every multi-character
  constraint client-side; two named regression tests pin the behavior.
- `src/lindenmayer/registry/reader.py` -- `get_version_history()` sends
  `#template_name` and does not re-check it client-side, so on a real relay
  it returns every template that author published, each labeled as the
  requested template. Its tests pass because no fixture has two template
  names present. Raised with the architect for registry to fix;
  `get_current_pointer()` uses `#d` and is unaffected.
