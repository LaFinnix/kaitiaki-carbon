# iwi engagement protocol

> **Read this before opening a PR or schema change.** This is the cultural protocol that governs `kaitiaki-carbon`. Schema changes are not optional cosmetic edits — they have implications for iwi data sovereignty.

---

## The user community

The user community of this tool is **iwi and hapū**, not "forestry enthusiasts". The framing matters:

- A forester asks: *"How much carbon is on this block?"*
- An iwi asks: *"What does it mean for us, in our accountability to tūpuna and to mokopuna, to put a number on that block?"*

The answer to the second question is what this tool enables. It is not the answer itself — the answer is the iwi's kōrero, their tikanga, their decision. Our job is to make sure the **numeric substrate** they reason with is honest, attested, and revisable.

---

## What this document governs

This document governs three types of changes:

1. **Schema changes** (anything in `attest.py` or `docs/ATTESTATION-SCHEMA.md`)
2. **Methodology changes** (anything in `core.py` or `docs/METHODOLOGY.md` that changes the math, the data sources, or the formula)
3. **Engagement-protocol changes** (this document itself, or the i18n layer in `i18n/mi.json`)

Other changes (CLI bug fixes, NDVI-ingestion improvements, doc typos) follow the standard CONTRIBUTING.md process and do not require iwi consultation.

---

## How we consult

Schema and methodology changes follow a **two-week comment window** plus a **named iwi reviewer**.

### Process

1. **Open an issue first.** Tag it `protocol-change`. Describe the proposed schema or methodology change.
2. **Wait 14 calendar days.** Comment during this period is encouraged. Maintain a comment log in the issue.
3. **Identify a reviewer.** If the change touches iwi attestation, request review from at least one iwi-affiliated contributor (see `CONTRIBUTING.md` for the current maintainer list). If no iwi-affiliated maintainer is available, **defer the change**. Don't merge without iwi eyes.
4. **Document the consultation.** Append a section to `docs/protocol-changelog.md` with the issue link, the reviewer name(s), and the resolution.
5. **Merge.** PR can be merged once the issue is closed with consensus.

### What counts as consultation

- A named iwi-affiliated individual who reviews the PR with iwi eyes — not just technical eyes
- A letter from an iwi rūnanga that touches the affected domain
- A council of marae representatives (rare, heavier-weight)

What **does not** count:

- Anyone who reviews the PR for technical correctness but is not iwi-affiliated
- Generic "no objections" comments without engagement with the iwi context
- Comments from non-iwi cultural theorists (helpful but not authoritative)

---

## Scope — what an iwi reviewer is asked to check

For a schema change, an iwi reviewer checks:

1. **Whakapapa respect**: Does the schema represent iwi, hapū, and marae accurately? Are the levels right?
2. **Rangatiratanga**: Does the schema leave iwi groups in control of *when* and *how* they attest, or does it presume?
3. **Tino rangatiratanga over data**: Does the schema ever claim iwi data without their attested consent?
4. **Manaakitanga**: Does the schema make the cost of being attested equal across iwi? (i.e., a small hapū isn't priced out of using the tool)
5. **Wairuatanga**: Are there places where the schema encodes a non-Māori assumption about how iwi relate? (i.e., the schema shouldn't presume iwi = individual members)

For a methodology change:

1. **Are the data sources accurate to NZ context?** (Pacific, native flora, etc.)
2. **Do the assumptions match iwi-driven land use?** (i.e., the math should not privilege exotic forestry over native re-establishment)
3. **Is the uncertainty honestly represented?** (i.e., wide CIs on small datasets is a feature, not a bug)

---

## What this document is **not**

It is **not** a blanket veto. iwi reviewers may reject a schema change. They may not reject a request to *engage with iwi*. The expectation is that every protocol change gets reviewed; the question is whether it merges with or without endorsement.

It is **not** a property claim. Nothing in this tool is owned by an iwi or assumes an iwi's consent. The attestation is opt-in: iwi and hapū can ignore this tool entirely and use their own. Our obligation is to make the option *clean* for those who choose to use it.

---

## Living-document commitments

- We will publish every protocol-change decision to `docs/protocol-changelog.md`.
- We will maintain a list of iwi-affiliated maintainers in `CONTRIBUTING.md`.
- We will not push schema changes during Matariki or Te Wiki o te Reo Māori unless the change is *into* those observances, not *about* them.

---

## Karakia for opening

We do not include karakia in source files. Karakia are spoken, not coded. If you want karakia before you start work, take it offline. The code stands on its own; the protocol is between us.

---

Kia kaha tātou i ngā mahi.
