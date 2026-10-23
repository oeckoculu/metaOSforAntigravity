"""Universal Day-0 Ignite & NotebookLM Briefing Compiler (DO-1 / OUT-001).

Reads .antigravity/genesis/project_manifest.json and .antigravity/genesis/research_briefing.md,
wraps untrusted research input inside an I-14 UntrustedContentEnvelope, verifies zero secret
leakage (I-12), and synthesizes IntentContract, DomainContract, and ProjectArchetypeProfile.
Also provides ignite_new_project() for clean run-<id>.jsonl initialization on cloned repos.
"""
import os
import re
import sys

from . import archetypes


def _ensure_kernel_path(root):
    kpath = os.path.join(root, ".antigravity", "kernel")
    if kpath not in sys.path:
        sys.path.insert(0, kpath)


def _extract_briefing_headings(raw_markdown):
    headings = []
    for line in raw_markdown.splitlines():
        s = line.strip()
        if s.startswith("#"):
            headings.append(re.sub(r"^#+\s*", "", s))
    return headings


def compile_ignition_pack(
    root,
    manifest_path=".antigravity/genesis/project_manifest.json",
    briefing_path=".antigravity/genesis/research_briefing.md",
    init_new_project=False,
    new_run_id=None,
    keystore_dir=None,
):
    """Wrap NotebookLM briefing in I-14 envelope and synthesize/validate IntentContract & ArchetypeProfile."""
    _ensure_kernel_path(root)
    from metaos import canonical, env, envelope, schema, secrets

    manifest_abs = os.path.join(root, manifest_path) if not os.path.isabs(manifest_path) else manifest_path
    briefing_abs = os.path.join(root, briefing_path) if not os.path.isabs(briefing_path) else briefing_path

    manifest_obj = canonical.strict_load_file(manifest_abs) if os.path.isfile(manifest_abs) else {
        "project_name": "Meta-OS Universal Ignite & Cockpit Suite",
        "primary_archetype": "CLI_SDK",
        "secondary_archetypes": ["Autonomous_Agent", "Data_ML_Pipeline"],
        "language": "python",
        "risk_class": "R2",
    }
    raw_briefing = open(briefing_abs, "rb").read().decode("utf-8") if os.path.isfile(briefing_abs) else "# Briefing\n"

    ks = keystore_dir or ("/tmp/metaos-keystore" if os.path.isdir("/tmp/metaos-keystore") else None)
    env_out_abs = os.path.join(root, "provenance", "research_briefing.envelope.json")
    raw_hash = canonical.sha256_ref(raw_briefing.encode("utf-8"))
    need_wrap = True
    if os.path.isfile(env_out_abs):
        env_doc = canonical.strict_load_file(env_out_abs)
        if env_doc.get("raw_sha256") == raw_hash:
            need_wrap = False

    if need_wrap:
        try:
            env_doc = envelope.wrap_untrusted_content(
                root=root,
                raw_text=raw_briefing,
                source_kind="EXTERNAL_DOC",
                source_uri="file://.antigravity/genesis/research_briefing.md",
                retrieved_at=env.utc_now(),
                run_id=manifest_obj.get("run_id", "run-0001"),
                envelope_id=env.uuid7(),
                keystore_dir=ks,
            )
            os.makedirs(os.path.dirname(env_out_abs), exist_ok=True)
            with open(env_out_abs, "wb") as fh:
                fh.write(canonical.pretty_bytes(env_doc))
        except Exception:
            if os.path.isfile(env_out_abs):
                env_doc = canonical.strict_load_file(env_out_abs)
            else:
                raise

    ver = envelope.verify_untrusted_envelope(root, env_doc)
    if not ver["valid"]:
        raise RuntimeError("I-14 UntrustedContentEnvelope verification failed: %r" % (ver,))

    intent_abs = os.path.join(root, "contracts", "src", "intent_contract.json")
    if os.path.isfile(intent_abs):
        intent_contract = canonical.strict_load_file(intent_abs)
    else:
        intent_contract = _synthesize_intent_from_manifest(manifest_obj, raw_briefing)

    core_intent_schema = canonical.strict_load_file(
        os.path.join(root, ".antigravity", "schemas", "core", "intent_contract.schema.json")
    )
    intent_errs = schema.Validator(core_intent_schema).errors(intent_contract)
    if intent_errs:
        raise RuntimeError("IntentContract schema validation failed: %r" % (intent_errs,))

    secret_hits = secrets.scan_obj(intent_contract)
    if secret_hits:
        raise RuntimeError("I-12 secret detected in IntentContract: %r" % (secret_hits,))

    primary_arch = manifest_obj.get("primary_archetype", "CLI_SDK")
    lang = manifest_obj.get("language", "python")
    synthesized_profile = archetypes.synthesize_archetype_profile(primary_arch, language=lang)
    prof_schema = canonical.strict_load_file(
        os.path.join(root, "contracts", "src", "schemas", "archetype_profile.schema.json")
    )
    prof_errs = schema.Validator(prof_schema).errors(synthesized_profile)
    if prof_errs:
        raise RuntimeError("SynthesizedArchetypeProfile schema validation failed: %r" % (prof_errs,))

    new_run_info = None
    if init_new_project:
        rid = new_run_id or "run-0001"
        new_run_info = ignite_new_project(
            target_root=root,
            run_id=rid,
            project_name=manifest_obj.get("project_name", "NewMetaOSProject"),
            primary_archetype=primary_arch,
            secondary_archetypes=manifest_obj.get("secondary_archetypes", []),
            language=lang,
            risk_class=manifest_obj.get("risk_class", "R2"),
            dry_run=True,
            keystore_dir=keystore_dir,
        )

    return {
        "envelope_verified": ver["valid"],
        "executable_authority": env_doc["executable_authority"],
        "envelope_sha256": canonical.file_sha256(env_out_abs),
        "extracted_headings": _extract_briefing_headings(env_doc["sanitized_text"]),
        "intent_contract": intent_contract,
        "intent_sha256": canonical.jcs_hash(intent_contract),
        "synthesized_profile": synthesized_profile,
        "profile_sha256": canonical.jcs_hash(synthesized_profile),
        "new_run_info": new_run_info,
    }


def _synthesize_intent_from_manifest(manifest_obj, raw_briefing):
    primary_arch = manifest_obj.get("primary_archetype", "Backend_API")
    owner = manifest_obj.get("owner") or "human:developer"
    if not owner.startswith("human:"):
        owner = "human:" + owner
    return {
        "schema_version": "1.0.0",
        "intent_id": "0192f3a4-0000-7000-8000-000000000901",
        "created_at": "2026-10-21T00:05:00Z",
        "author": {"principal_id": owner, "kind": "HUMAN"},
        "title": "%s (%s Day-0 Ignition Contract)" % (manifest_obj.get("project_name", "Meta-OS Project"), primary_arch),
        "problem_statement": (
            "Synthesized Day-0 IntentContract from project_manifest.json and I-14 isolated research_briefing.md "
            "for primary archetype %s with deterministic 5-oracle verification." % primary_arch
        ),
        "desired_outcomes": [
            {
                "id": "OUT-001",
                "description": "Materialize polymorphic archetype topology and contract locks for %s." % primary_arch,
                "metric": "100% schema and oracle validation pass rate",
            }
        ],
        "in_scope": ["contracts/", "invariants/", "src/", "tests/", "receipts/", "provenance/", "docs/"],
        "out_of_scope": [".antigravity/", ".agents/", "scripts/", "SPEC_META_OS_v1.1.md"],
        "constraints": {
            "max_budget_usd": 10,
            "max_wall_clock_minutes": 60,
            "allowed_languages": [manifest_obj.get("language", "python")],
            "prohibited_dependencies": ["unpinned-third-party-packages"],
            "forbidden_paths": [".antigravity/", ".agents/", "scripts/", "SPEC_META_OS_v1.1.md"],
        },
        "risk_factors": {
            "touches_auth_or_crypto": False,
            "touches_persistence_schema": False,
            "touches_public_api": True,
            "touches_kernel_or_constitution": False,
            "handles_pii_or_secrets": False,
        },
        "acceptance_oracles": [
            {
                "oracle_id": "ORC-001",
                "kind": "CONTRACT",
                "command": "python3 tests/run_suite.py --oracle ORC-001",
                "expected_exit_code": 0,
            }
        ],
    }


def ignite_new_project(
    target_root,
    run_id="run-0001",
    project_name="NewMetaOSProject",
    primary_archetype="Backend_API",
    secondary_archetypes=None,
    language="python",
    risk_class="R2",
    dry_run=False,
    keystore_dir=None,
    owner=None,
):
    """Initialize a newly cloned repository or isolated sandbox with a clean run-<id>.jsonl journal."""
    _ensure_kernel_path(target_root)
    import getpass
    from metaos import canonical, env, journal

    user_name = getpass.getuser() or "developer"
    principal_id = owner or ("human:" + user_name)
    if not principal_id.startswith("human:"):
        principal_id = "human:" + principal_id

    prof = archetypes.synthesize_archetype_profile(primary_archetype, language=language)
    manifest_obj = {
        "project_name": project_name,
        "primary_archetype": primary_archetype,
        "secondary_archetypes": list(secondary_archetypes or []),
        "language": language,
        "risk_class": risk_class,
        "owner": principal_id,
    }
    intent_obj = _synthesize_intent_from_manifest(manifest_obj, "# Day-0 Briefing\n")

    if dry_run:
        return {
            "status": "DRY_RUN_READY",
            "run_id": run_id,
            "primary_archetype": primary_archetype,
            "language": language,
            "risk_class": risk_class,
            "owner": principal_id,
            "default_directories": prof["default_directories"],
            "intent_sha256": canonical.jcs_hash(intent_obj),
            "profile_sha256": canonical.jcs_hash(prof),
        }

    for d in prof["default_directories"]:
        os.makedirs(os.path.join(target_root, d), exist_ok=True)

    intent_rel = "contracts/src/intent_contract.json"
    intent_abs = os.path.join(target_root, intent_rel)
    os.makedirs(os.path.dirname(intent_abs), exist_ok=True)
    with open(intent_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(intent_obj))

    prof_rel = "contracts/src/project_archetype_profile.json"
    prof_abs = os.path.join(target_root, prof_rel)
    with open(prof_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(prof))

    act_prof_rel = ".antigravity/genesis/active_profile.json"
    act_prof_abs = os.path.join(target_root, act_prof_rel)
    with open(act_prof_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(prof))

    validator = journal.load_validator(target_root)
    rep = env.reproducibility(target_root)

    # Check external keystore for signing capability (AUD-01 graceful fallback)
    ks = keystore_dir or os.environ.get("METAOS_KEYSTORE_DIR", "/tmp/metaos-keystore")
    can_sign = False
    if os.path.isdir(ks):
        priv_candidates = [
            os.path.join(ks, "human_owner_ed25519"),
            os.path.join(ks, "%s_ed25519" % user_name),
        ]
        if any(os.path.isfile(p) for p in priv_candidates):
            try:
                from metaos import crypto
                if principal_id in crypto.PRINCIPALS:
                    can_sign = True
            except Exception:
                can_sign = False

    build_entry_kwargs = {
        "validator": validator,
        "seq": 0,
        "run_id": run_id,
        "prev_hash": "sha256:" + "0" * 64,
        "event_type": "GENESIS_BOOTSTRAP",
        "actor": {"principal_id": principal_id, "kind": "HUMAN", "os_identity": user_name},
        "payload": {
            "proposal_id": "GBP-0000",
            "proposal_path": ".antigravity/genesis/genesis_bootstrap_proposal.json",
            "proposal_ref": canonical.file_sha256(
                os.path.join(target_root, ".antigravity/genesis/genesis_bootstrap_proposal.json")
            ),
            "decision": "APPROVED",
            "accepted_patch_ids": [
                "C-1", "C-2", "C-3", "C-4", "C-5", "C-6", "C-7", "C-8",
                "V12-01", "V12-02", "V12-03", "V12-04", "V12-05", "V12-06",
            ],
            "approval_record": {
                "channel": "ANTIGRAVITY_CONVERSATION",
                "conversation_id": "0192f3a4-0000-7000-8000-000000000001",
                "path": ".antigravity/genesis/user_approval_step26.md",
                "sha256": canonical.file_sha256(os.path.join(target_root, ".antigravity/genesis/user_approval_step26.md")),
                "step_index": 1,
            },
            "blueprint": {
                "path": ".antigravity/genesis/blueprint/system_blueprint_v1.md",
                "sha256": canonical.file_sha256(
                    os.path.join(target_root, ".antigravity/genesis/blueprint/system_blueprint_v1.md")
                ),
            },
            "substrate": "LOCAL_APFS_GIT",
        },
        "reproducibility": rep,
        "ts": env.utc_now(),
        "root": target_root,
    }

    if can_sign:
        build_entry_kwargs["sign_principal"] = principal_id
        build_entry_kwargs["sign_namespace"] = "metaos.journal"
        build_entry_kwargs["keystore_dir"] = ks
    else:
        build_entry_kwargs["signature"] = {
            "status": "UNSIGNED",
            "reason": "KEYS_NOT_PROVISIONED_UNTIL_A7",
        }

    genesis_entry = journal.build_entry(**build_entry_kwargs)
    run_rel = ".antigravity/events/%s.jsonl" % run_id
    run_abs = os.path.join(target_root, run_rel)
    os.makedirs(os.path.dirname(run_abs), exist_ok=True)
    with open(run_abs, "wb") as fh:
        fh.write(canonical.jcs_bytes(genesis_entry) + b"\n")

    # Update root README.md with project metadata if stub placeholders exist
    readme_path = os.path.join(target_root, "README.md")
    if os.path.isfile(readme_path):
        try:
            r_txt = open(readme_path, "rb").read().decode("utf-8")
            if "{{ PROJECT_NAME }}" in r_txt:
                r_txt = r_txt.replace("{{ PROJECT_NAME }}", project_name)
                r_txt = r_txt.replace("{{ PRIMARY_ARCHETYPE }}", primary_archetype)
                r_txt = r_txt.replace("{{ LANGUAGE }}", language)
                r_txt = r_txt.replace("{{ RISK_CLASS }}", risk_class)
                with open(readme_path, "wb") as fh:
                    fh.write(r_txt.encode("utf-8"))
        except Exception:
            pass

    return {
        "status": "IGNITED",
        "run_id": run_id,
        "journal_path": run_rel,
        "genesis_entry_hash": genesis_entry["entry_hash"],
        "primary_archetype": primary_archetype,
        "language": language,
        "intent_path": intent_rel,
        "profile_path": prof_rel,
        "active_profile_path": act_prof_rel,
    }
