---
title: Meta-OS Insan Karar ve Onay Kuyrugu (DECISION_QUEUE)
tags: [metaos, cockpit, outbox, human-in-the-loop]
current_state: CLOSED
---
# Insan Denetim Kapilari, Counterfactual Handshake & Outbox Kuyrugu (`DECISION_QUEUE`)

Navigasyon: [[DASHBOARD]] | [[STATE_GRAPH]] | [[DECISION_QUEUE]] | [[EVIDENCE_LEDGER]]

## 1. Transactional Local Outbox Kayitlari (`.antigravity/outbox/`)

| Outbox ID | Tur (`kind`) | Durum (`status`) | Karar (`decision`) | Dosya Yolu |
| :--- | :--- | :--- | :--- | :--- |
| `OBX-62f0450cd7e74b13` | `HUMAN_AUDIT_REVIEW` | `ACKNOWLEDGED` | `APPROVED` | `.antigravity/outbox/OBX-62f0450cd7e74b13.json` |
| `OBX-9a4ff14b0cd461cf` | `GENESIS_NOTICE` | `ACKNOWLEDGED` | `APPROVED` | `.antigravity/outbox/OBX-9a4ff14b0cd461cf.json` |

## 2. Insan Onay Kapilari Akis Diyagrami (Mermaid)

```mermaid
sequenceDiagram
    participant A as Meta-OS Kernel / Agent
    participant O as .antigravity/outbox/
    participant H as Human Owner (Human-in-the-Loop)
    A->>O: outbox_emit (HANDSHAKE_REVIEW / HUMAN_AUDIT_REVIEW)
    O->>H: Counterfactual Handshake (V12-01) & ProofReceipt (LC-18A)
    H->>O: outbox_ack --decision APPROVED (sshsig-ed25519)
    O->>A: HumanApprovalToken verified (LC-08 / LC-19A -> READY_TO_MERGE)
```
