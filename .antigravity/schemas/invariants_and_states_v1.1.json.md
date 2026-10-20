{  
  "title": "Meta-OS Deterministic Invariants and State Machine Specification",  
  "version": "1.1.0",  
  "description": "Authoritative machine-readable matrices for architectural invariants, sequential lifecycle transitions, and patched recovery loopbacks.",  
  "invariants": \[  
    {  
      "id": "I-01",  
      "rule\_name": "Proposal/Admission/Commit Separation",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Policy Engine & Privileged Executor",  
      "description": "LLM or agents only produce signable ChangeProposal. Policy Engine evaluates admission. Privileged Executor applies admitted proposal. Day-0 bootstrap exception: GenesisBootstrapProposal is user-signed."  
    },  
    {  
      "id": "I-02",  
      "rule\_name": "Least Privilege",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Capability/Lease Manager",  
      "description": "Each agent receives short-lived capability tokens strictly bounded by task ID, time, file scope, tool scope, and action type."  
    },  
    {  
      "id": "I-03",  
      "rule\_name": "Append-Only Evidence",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Event Journal & State Projector",  
      "description": "Events, policy evaluations, test runs, and approvals write solely to append-only journals. Mutable views are regenerated via replay."  
    },  
    {  
      "id": "I-04",  
      "rule\_name": "Reproducibility",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Provenance & Attestation Registry",  
      "description": "No evidence is valid without source commit SHA, toolchain digest, lockfile hash, container image digest, test seed, and policy version."  
    },  
    {  
      "id": "I-05",  
      "rule\_name": "No Silent Self-Modification",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Admission Controller & PDP",  
      "description": "The system cannot mutate its own prompt, policies, dependencies, model routing, or template without an explicit PR proposal with rationale and diff."  
    },  
    {  
      "id": "I-06",  
      "rule\_name": "Risk-Based Human Gates & Gate Scheduling",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Risk Profile & Gate Scheduler",  
      "description": "Frequency and depth of heavy validation gates (mutation, deep perf, human approvals) are scheduled dynamically by risk\_class."  
    },  
    {  
      "id": "I-07",  
      "rule\_name": "Machine Authority, Human Projection",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Contract Registry & Deterministic Projections",  
      "description": "Machine authority belongs solely to schemas, policies, and tests. Human docs (Markdown, Confluence, Mermaid) are deterministically generated projections."  
    },  
    {  
      "id": "I-08",  
      "rule\_name": "Fail Closed",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Policy Decision Point (PDP)",  
      "description": "If capabilities, permissions, provenance, or policy outcomes are ambiguous, the protected action is rejected immediately."  
    },  
    {  
      "id": "I-09",  
      "rule\_name": "Reversible by Default",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Ephemeral Sandbox & Git Worktree",  
      "description": "Changes run inside ephemeral environments or worktrees. Any proposal lacking an executable rollback/compensation plan is rejected."  
    },  
    {  
      "id": "I-10",  
      "rule\_name": "Evidence Before Claim",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "EvidenceAssemblerAgent",  
      "description": "Claims of security, verified status, or performance can only be asserted if backed by signed proof receipts."  
    },  
    {  
      "id": "I-11",  
      "rule\_name": "No Vendor Lock-In at Core & Deterministic Fallback",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Integration Ports & Local Outbox Adapters",  
      "description": "External providers connect strictly through decoupled adapter interfaces. When remote adapters (Jira/Confluence) are unreachable, deterministic local file/Git outbox fallback activates automatically."  
    },  
    {  
      "id": "I-12",  
      "rule\_name": "Privacy and Secret Safety",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Secret Broker & Redaction Policy",  
      "description": "Secrets, PII, and classified data are scrubbed before prompt submission, telemetry logging, or human-facing projection."  
    },  
    {  
      "id": "I-13",  
      "rule\_name": "Polymorphic Adaptability",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "GenesisAgent & Topology Synthesizer",  
      "description": "Core kernel maintains zero language coupling. Domain and language setups bind dynamically via ProjectArchetypeProfile on Day-0."  
    },  
    {  
      "id": "I-14",  
      "rule\_name": "Untrusted Input & Prompt Injection Isolation",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "UntrustedContentEnvelope & Sanitizer",  
      "description": "External inputs are encapsulated and sanitized; never executed directly as raw instructions."  
    },  
    {  
      "id": "I-15",  
      "rule\_name": "Audited Break-Glass",  
      "requirement\_level": "REQUIRED",  
      "enforcement\_gatekeeper": "Break-Glass Controller & Event Journal",  
      "description": "Deterministic emergency override procedure requiring cryptographic human signature and audited BREAK\_GLASS\_OVERRIDE journal entry."  
    }  
  \],  
  "state\_machine": {  
    "initial\_state": "TECH\_RADAR\_SYNC",  
    "terminal\_states": \[  
      "CLOSED",  
      "BREAK\_GLASS\_ACTIVE"  
    \],  
    "lifecycle\_transitions": \[  
      {  
        "current\_state": "TECH\_RADAR\_SYNC",  
        "allowed\_next\_states": \["CAPABILITY\_BASELINED"\],  
        "required\_evidence": "TechRadarDelta & CapabilityManifest",  
        "actor": "CapabilityDiscoveryAgent & TechRadarAgent"  
      },  
      {  
        "current\_state": "CAPABILITY\_BASELINED",  
        "allowed\_next\_states": \["GENESIS\_MORPHING"\],  
        "required\_evidence": "ValidatedEnvironmentProfile",  
        "actor": "GenesisAgent"  
      },  
      {  
        "current\_state": "GENESIS\_MORPHING",  
        "allowed\_next\_states": \["GENESIS\_LOCKED"\],  
        "required\_evidence": "UserApprovedProfile",  
        "actor": "GenesisAgent & HumanInteractionPort"  
      },  
      {  
        "current\_state": "GENESIS\_LOCKED",  
        "allowed\_next\_states": \["INTENT\_CAPTURED"\],  
        "required\_evidence": "InitializedWorkspace & ValidatedIntentContract",  
        "actor": "Privileged Executor & IntentCompilerAgent"  
      },  
      {  
        "current\_state": "INTENT\_CAPTURED",  
        "allowed\_next\_states": \["RISK\_CLASSIFIED"\],  
        "required\_evidence": "RiskClassAssignment & GateSchedule",  
        "actor": "Risk Profile & Gate Scheduler"  
      },  
      {  
        "current\_state": "RISK\_CLASSIFIED",  
        "allowed\_next\_states": \["HANDSHAKE\_PENDING", "CONTRACT\_DRAFTING"\],  
        "required\_evidence": "CounterfactualHandshakeResult or ContractDraft",  
        "actor": "IntentCompilerAgent & ContractAgent"  
      },  
      {  
        "current\_state": "HANDSHAKE\_PENDING",  
        "allowed\_next\_states": \["CONTRACT\_DRAFTING"\],  
        "required\_evidence": "HumanApprovalReceipt",  
        "actor": "HumanInteractionPort & ContractAgent"  
      },  
      {  
        "current\_state": "CONTRACT\_DRAFTING",  
        "allowed\_next\_states": \["CONTRACT\_REVIEWED"\],  
        "required\_evidence": "ThreatModelReport & ContractDiff",  
        "actor": "ThreatModelAgent & ContractAgent"  
      },  
      {  
        "current\_state": "CONTRACT\_REVIEWED",  
        "allowed\_next\_states": \["CONTRACT\_LOCKED"\],  
        "required\_evidence": "CanonicalSpecLockFile",  
        "actor": "ContractAgent & Policy Engine"  
      },  
      {  
        "current\_state": "CONTRACT\_LOCKED",  
        "allowed\_next\_states": \["TESTS\_ARMED\_RED"\],  
        "required\_evidence": "PropertyBasedTestSet & GoldenCases",  
        "actor": "BuilderAgent & RedTeamVerifierAgent"  
      },  
      {  
        "current\_state": "TESTS\_ARMED\_RED",  
        "allowed\_next\_states": \["CHANGE\_ADMITTED"\],  
        "required\_evidence": "AdmissionPolicyPassReceipt(RedExecutionVerified\_NonZeroExit)",  
        "actor": "Admission Controller & PDP"  
      },  
      {  
        "current\_state": "CHANGE\_ADMITTED",  
        "allowed\_next\_states": \["SANDBOX\_EXECUTING"\],  
        "required\_evidence": "EphemeralSandboxAllocation",  
        "actor": "Privileged Executor"  
      },  
      {  
        "current\_state": "SANDBOX\_EXECUTING",  
        "allowed\_next\_states": \["WORKTREE\_GREEN"\],  
        "required\_evidence": "IsolatedWorktreeBuildSuccess",  
        "actor": "BuilderAgent"  
      },  
      {  
        "current\_state": "WORKTREE\_GREEN",  
        "allowed\_next\_states": \["SECURITY\_VERIFIED"\],  
        "required\_evidence": "SAST/DAST/Secret/SBOMScanPass",  
        "actor": "ThreatModelAgent & RedTeamVerifierAgent"  
      },  
      {  
        "current\_state": "SECURITY\_VERIFIED",  
        "allowed\_next\_states": \["MUTATION\_VERIFIED"\],  
        "required\_evidence": "MutationScorePass & Non-SurvivingInvariants",  
        "actor": "RedTeamVerifierAgent"  
      },  
      {  
        "current\_state": "MUTATION\_VERIFIED",  
        "allowed\_next\_states": \["PERFORMANCE\_VERIFIED"\],  
        "required\_evidence": "OTelBaselinePass & QueryCountCheck",  
        "actor": "PerformanceAgent"  
      },  
      {  
        "current\_state": "PERFORMANCE\_VERIFIED",  
        "allowed\_next\_states": \["PROOF\_ASSEMBLED"\],  
        "required\_evidence": "CompleteProofReceiptPackage",  
        "actor": "EvidenceAssemblerAgent"  
      },  
      {  
        "current\_state": "PROOF\_ASSEMBLED",  
        "allowed\_next\_states": \["HUMAN\_AUDIT\_REQUIRED", "READY\_TO\_MERGE"\],  
        "required\_evidence": "HumanAuditVerdict or AutomatedGatePass",  
        "actor": "HumanInteractionPort & Admission Controller"  
      },  
      {  
        "current\_state": "HUMAN\_AUDIT\_REQUIRED",  
        "allowed\_next\_states": \["READY\_TO\_MERGE", "INTENT\_CAPTURED"\],  
        "required\_evidence": "HumanApprovalToken or RejectionRationale",  
        "actor": "HumanInteractionPort"  
      },  
      {  
        "current\_state": "READY\_TO\_MERGE",  
        "allowed\_next\_states": \["MERGED"\],  
        "required\_evidence": "GitMergeSuccess & AppendOnlyEventRecord",  
        "actor": "Privileged Executor & Event Journal"  
      },  
      {  
        "current\_state": "MERGED",  
        "allowed\_next\_states": \["POST\_DEPLOY\_OBSERVING"\],  
        "required\_evidence": "CanaryDeploymentTelemetry",  
        "actor": "PerformanceAgent & DriftHealerAgent"  
      },  
      {  
        "current\_state": "POST\_DEPLOY\_OBSERVING",  
        "allowed\_next\_states": \["CLOSED"\],  
        "required\_evidence": "StabilityReceipt & FinalStateLock",  
        "actor": "EvidenceAssemblerAgent"  
      }  
    \],  
    "exception\_and\_circuit\_breaker\_transitions": \[  
      {  
        "from\_state": "ANY\_ACTIVE\_STATE",  
        "to\_state": "BLOCKED\_POLICY",  
        "trigger": "Policy violation or unadmitted capability call",  
        "required\_evidence": "PolicyViolationRecord",  
        "actor": "Policy Engine"  
      },  
      {  
        "from\_state": "BLOCKED\_POLICY",  
        "to\_state": "HUMAN\_AUDIT\_REQUIRED",  
        "trigger": "Policy exemption request or rule clarification",  
        "required\_evidence": "PolicyExemptionReviewPacket",  
        "actor": "HumanInteractionPort & PDP"  
      },  
      {  
        "from\_state": "ANY\_ACTIVE\_STATE",  
        "to\_state": "BUDGET\_EXHAUSTED",  
        "trigger": "Token, USD cost, or retry ceiling breached",  
        "required\_evidence": "BudgetBreachRecord",  
        "actor": "Circuit Breaker"  
      },  
      {  
        "from\_state": "BUDGET\_EXHAUSTED",  
        "to\_state": "HUMAN\_AUDIT\_REQUIRED",  
        "trigger": "Human budget increment or task scope reduction",  
        "required\_evidence": "BudgetIncrementAuthorization",  
        "actor": "HumanInteractionPort"  
      },  
      {  
        "from\_state": "ANY\_ACTIVE\_STATE",  
        "to\_state": "EVIDENCE\_INCOMPLETE",  
        "trigger": "Missing required attestation, hash, or audit receipt",  
        "required\_evidence": "MissingEvidenceAuditReport",  
        "actor": "Admission Controller"  
      },  
      {  
        "from\_state": "EVIDENCE\_INCOMPLETE",  
        "to\_state": "SANDBOX\_EXECUTING",  
        "trigger": "Targeted evidence generation remediation task",  
        "required\_evidence": "RemediationTaskEnvelope",  
        "actor": "BuilderAgent & Admission Controller"  
      },  
      {  
        "from\_state": "ANY\_ACTIVE\_STATE",  
        "to\_state": "ROLLED\_BACK",  
        "trigger": "Worktree test failure, assertion fault, or sandbox crash",  
        "required\_evidence": "FailureRecord & WorktreeCleanupReceipt",  
        "actor": "Privileged Executor"  
      },  
      {  
        "from\_state": "ROLLED\_BACK",  
        "to\_state": "INTENT\_CAPTURED",  
        "trigger": "Alternative hypothesis revision after failed proposal",  
        "required\_evidence": "RevisedHypothesisRecord",  
        "actor": "IntentCompilerAgent"  
      },  
      {  
        "from\_state": "ANY\_ACTIVE\_STATE",  
        "to\_state": "QUARANTINED",  
        "trigger": "Prompt injection attempt, untrusted input breach, or malicious payload",  
        "required\_evidence": "SecurityAnomalyReport",  
        "actor": "ThreatModelAgent"  
      },  
      {  
        "from\_state": "QUARANTINED",  
        "to\_state": "HUMAN\_AUDIT\_REQUIRED",  
        "trigger": "Security review and sanitation audit",  
        "required\_evidence": "SanitizedAuditAttestation",  
        "actor": "HumanInteractionPort & ThreatModelAgent"  
      },  
      {  
        "from\_state": "ANY\_ACTIVE\_STATE",  
        "to\_state": "BREAK\_GLASS\_ACTIVE",  
        "trigger": "Emergency human intervention override",  
        "required\_evidence": "CryptographicallySignedBreakGlassOverrideEvent",  
        "actor": "Break-Glass Controller"  
      }  
    \]  
  }  
}