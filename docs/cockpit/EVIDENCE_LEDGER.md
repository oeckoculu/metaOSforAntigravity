---
title: Meta-OS Kriptografik Kanit Defteri (EVIDENCE_LEDGER)
tags: [metaos, cockpit, evidence, proof-receipt]
current_state: CLOSED
---
# Kriptografik Kanit Zinciri (`EVIDENCE_LEDGER`)

Navigasyon: [[DASHBOARD]] | [[STATE_GRAPH]] | [[DECISION_QUEUE]] | [[EVIDENCE_LEDGER]]

## 1. Uctan Uca Kanit Soyagaci (`IntentContract` -> `ProofReceipt`)

```mermaid
flowchart TD
    RB["research_briefing.md (Untrusted)"] -->|I-14 Envelope| ENV["provenance/research_briefing.envelope.json"]
    ENV -->|LC-04| IC["contracts/src/intent_contract.json"]
    IC -->|LC-06B| DC["contracts/src/domain_contracts.json"]
    DC -->|LC-09| SL["contracts/locks/spec.lock.json"]
    SL -->|LC-11 V12-05| RED["receipts/B1_admission_policy_pass.receipt.json"]
    RED -->|LC-13| GRN["receipts/b2_worktree_green.json"]
    GRN -->|LC-14..LC-16| GATES["Security + SBOM + Mutation (1.0) + Perf"]
    GATES -->|LC-17| PRF["receipts/pointers/latest_proof.json"]
```

## 2. Mühürlü Artefakt ve Makbuz Tablosu

| Katman / Kapi | Artefakt Yolu | Durum |
| :--- | :--- | :--- |
| `I-09` Kernel Lock | `.antigravity/genesis/kernel_lock.json` | `VERIFIED (97 files)` |
| `I-14` Briefing Envelope | `provenance/research_briefing.envelope.json` | `NONE_DATA_ONLY` |
| `LC-04` IntentContract | `contracts/src/intent_contract.json` | `LOCKED` |
| `LC-09` Spec Lock | `contracts/locks/spec.lock.json` | `LOCKED` |
| `LC-11` Triple RED Oracle | `receipts/B1_admission_policy_pass.receipt.json` | `PASS (V12-05)` |
| `LC-14` Security & SBOM | `provenance/sbom/layer_b_sbom.json` | `PASS` |
| `LC-15` Mutation Verification | `receipts/b2_mutation_verification.json` | `PASS (1.0)` |
| `LC-16` Performance Proof | `receipts/b2_performance_scan_proof.json` | `PASS` |
| `LC-17` Proof Pointer | `receipts/pointers/latest_proof.json` | `sha256:de597e487325d1eb5f8556c0e425a5aeb38ea7bbd9238ead982257f921e50f01` |
