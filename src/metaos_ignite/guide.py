"""Turkish Operator Handbook (docs/IGNITE_GUIDE.md) & Starter Templates Generator (DO-4 / OUT-004).

Materializes:
- docs/IGNITE_GUIDE.md (5-section Turkish step-by-step operator guide)
- docs/templates/project_manifest.template.json
- docs/templates/research_briefing.template.md
- .antigravity/genesis/templates/project_manifest.template.json
- .antigravity/genesis/templates/research_briefing.template.md
"""
import os
import sys


def _ensure_kernel_path(root):
    kpath = os.path.join(root, ".antigravity", "kernel")
    if kpath not in sys.path:
        sys.path.insert(0, kpath)


def render_ignite_guide(root, output_path="docs/IGNITE_GUIDE.md"):
    """Render docs/IGNITE_GUIDE.md and starter templates in docs/templates/ and .antigravity/genesis/templates/."""
    _ensure_kernel_path(root)
    from metaos import canonical, secrets

    manifest_template = {
        "schema_version": "1.0.0",
        "project_name": "Yeni_MetaOS_Projesi",
        "primary_archetype": "Backend_API",
        "secondary_archetypes": ["Data_ML_Pipeline"],
        "language": "python",
        "risk_class": "R2",
        "owner": "human:oeckoculu",
        "budgets": {
            "max_budget_usd": 10,
            "max_wall_clock_minutes": 60,
        },
        "notes": "primary_archetype alani 6 evrensel arketipten biri olmalidir: Backend_API, FullStack_Web, Data_ML_Pipeline, CLI_SDK, Autonomous_Agent, Embedded_IoT",
    }

    briefing_template = "\n".join([
        "# NotebookLM Arastirma Ozeti (Research Briefing Şablonu)",
        "",
        "## 1. Problem Tanimi veVizyon",
        "- Cozulmek istenen temel problem ve hedef kullanici kitlesi.",
        "",
        "## 2. Olculebilir Hedefler (Desired Outcomes)",
        "- **DO-1:** Birincil fonksiyonel cikti ve kabul olcutu.",
        "- **DO-2:** Performans, guvenlik ve dayaniklilik hedefleri.",
        "",
        "## 3. Mimari Sinirlar ve Kisitlar (Constraints & Out-of-Scope)",
        "- Kullanilacak dil/arac zinciri, yasakli bagimliliklar ve kapsam disi moduller.",
        "",
        "## 4. Kabul Kahinleri (Acceptance Oracles — 5 Zorunlu Sinif)",
        "- `CONTRACT`, `PROPERTY`, `GOLDEN`, `PERF`, `SECURITY` dogrulama senaryolari.",
        "",
    ])

    template_paths = []
    for tpl_dir_rel in ("docs/templates", ".antigravity/genesis/templates"):
        tpl_dir_abs = os.path.join(root, tpl_dir_rel)
        os.makedirs(tpl_dir_abs, exist_ok=True)
        man_abs = os.path.join(tpl_dir_abs, "project_manifest.template.json")
        with open(man_abs, "wb") as fh:
            fh.write(canonical.pretty_bytes(manifest_template))
        brf_abs = os.path.join(tpl_dir_abs, "research_briefing.template.md")
        with open(brf_abs, "wb") as fh:
            fh.write(canonical.canonical_text(briefing_template).encode("utf-8"))
        template_paths.append(os.path.relpath(man_abs, root).replace(os.sep, "/"))
        template_paths.append(os.path.relpath(brf_abs, root).replace(os.sep, "/"))

    guide_md = "\n".join([
        "# Meta-OS Universal Day-0 Ignite & Obsidian Kokpit Başucu Rehberi (`IGNITE_GUIDE.md`)",
        "",
        "Bu kılavuz, `metaOSforAntigravity` şablon deposunu klonlayarak yeni bir yazılım projesini **NotebookLM**, **Antigravity** ve **Obsidian** üçlüsüyle sıfırdan başlatmak ve yönetmek için hazırlanmış adım adım kontrol listesidir.",
        "",
        "---",
        "",
        "## Bölüm 1: GitHub Template Klonlama & Çekirdek Kilit Doğrulaması",
        "",
        "Yeni bir projeye başlarken şablon depoyu klonlayın ve Katman A (Immutable Kernel) bütünlüğünü doğrulayın:",
        "",
        "```bash",
        "git clone <metaOS-template-repo-url> yeni-proje-adi",
        "cd yeni-proje-adi",
        "./scripts/kernel_lock",
        "./scripts/kernel_selftest",
        "./scripts/pep_session_start",
        "```",
        "",
        "- `./scripts/kernel_lock`: `valid: true` ve `total_locked_files: 97` (`merkle_root_sha256: sha256:fdc68cb03c9b1b5fd3e0648ea6b46ab0b6b9935a0ad2849fee91116975717aed`) döndürmelidir.",
        "- `./scripts/kernel_selftest`: `overall_valid: true` döndürmelidir.",
        "",
        "---",
        "",
        "## Bölüm 2: NotebookLM Araştırma Sentezi & Kopyala-Yapıştır Prompt Şablonu",
        "",
        "Projeye ait makaleleri, API dokümanlarını, RFC'leri ve rakip analizlerini **Google NotebookLM**'e yükleyin ve aşağıdaki kopyala-yapıştır promptunu çalıştırın:",
        "",
        "```text",
        "Yüklediğim tüm kaynakları sentezleyerek Meta-OS v1.2.0 Day-0 ateşlemesi için aşağıdaki 4 başlıkta",
        "yapısal bir Markdown araştırma özeti (research_briefing.md) üret:",
        "1. Problem Tanımı ve Mimari Vizyon (somut darboğazlar ve hedef sistem sınırı)",
        "2. Ölçülebilir Hedefler (DO-1..DO-4 formatında doğrulanabilir çıktılar ve metrikler)",
        "3. Mimari Kısıtlar, Bütçeler ve Kapsam Dışı Alanlar (dil, gecikme bütçesi, güvenlik sınırları)",
        "4. 5 Zorunlu Kabul Kahini (CONTRACT, PROPERTY, GOLDEN, PERF, SECURITY test senaryoları)",
        "Not: Çıktıda hiçbir gerçek API anahtarı, parola veya gizli anahtar (I-12) yer almamalıdır.",
        "```",
        "",
        "---",
        "",
        "## Bölüm 3: Dosya Yerleşimi & 6 Evrensel Arketip Seçim Tablosu",
        "",
        "1. `docs/templates/research_briefing.template.md` şablonunu baz alarak NotebookLM çıktısını `.antigravity/genesis/research_briefing.md` dosyasına kaydedin.",
        "2. `docs/templates/project_manifest.template.json` şablonunu `.antigravity/genesis/project_manifest.json` olarak kopyalayın ve projenize uygun arketipi seçin:",
        "",
        "| Arketip ID (`primary_archetype`) | Kullanım Senaryosu | Polimorfik Güvenlik & Performans Kapıları (`V12-03`) |",
        "| :--- | :--- | :--- |",
        "| `Backend_API` | REST/gRPC mikroservisler, veritabanı odaklı API sistemleri | OpenAPI AuthZ matrisi, p99 gecikme (`150ms`) & N+1 sorgu denetimi |",
        "| `FullStack_Web` | Modern web uygulamaları, BFF + UI durum makineleri | CSP/DOM XSS & CSRF denetimi, Core Web Vitals (`LCP < 2000ms`) |",
        "| `Data_ML_Pipeline` | Veri ambarı, ETL/ELT, özellik mağazası ve ML boru hatları | PII sızıntı & veri zehirlenmesi taraması, satır/sn throughput (`10k/s`) |",
        "| `CLI_SDK` | Komut satırı araçları, hermetik dil kütüphaneleri ve SDK'lar | AST tehlikeli çağrı denetimi, hermetik SBOM, soğuk başlatma (`< 250ms`) |",
        "| `Autonomous_Agent` | Çoklu ajan orkestratörleri, araç kullanan otonom çalışma zamanları | `I-14` zarf denetimi, CapabilityToken kapsam kontrolü, adım gecikmesi |",
        "| `Embedded_IoT` | Firmware, RTOS görevleri, donanım soyutlama katmanı (HAL) | Yığın/bellek sınır denetimi, imzalı önyükleme, WCET (`< 500us`) |",
        "",
        "---",
        "",
        "## Bölüm 4: Antigravity Day-0 Ateşleme Promptu & CLI Komutları",
        "",
        "Dosyaları yerleştirdikten sonra terminalden tek komutla yeni proje günlüğünü başlatabilir veya doğrulama boru hattını çalıştırabilirsiniz (`./scripts/ignite` ve `./scripts/worktree_exec` işlevlerinin birleşik CLI karşılığı):",
        "",
        "```bash",
        "# 1. Yeni klonlanan depoda temiz run-0001.jsonl ve IntentContract başlatma:",
        "python3 -m src.metaos_ignite.cli init-new-project --run-id run-0001",
        "",
        "# 2. NotebookLM girdilerini I-14 zarfından geçirip kontrat ve profil derleme:",
        "python3 -m src.metaos_ignite.cli compile",
        "",
        "# 3. Triple RED (V12-05) veya İzole Worktree GREEN (LC-13) doğrulaması:",
        "python3 -m src.metaos_ignite.cli verify-green --seed 42",
        "",
        "# 4. Ed25519 imzalı ProofReceipt üretimi ve Obsidian kokpit projeksiyonu:",
        "python3 -m src.metaos_ignite.cli assemble-proof --run-id run-0000",
        "python3 -m src.metaos_ignite.cli project-cockpit",
        "```",
        "",
        "**Antigravity IDE İçinde Kullanılacak Standart Day-0 Ateşleme Promptu:**",
        "",
        "```text",
        "Kök dizindeki SPEC_META_OS_v1.1.md anayasasını, .antigravity/genesis/project_manifest.json",
        "ve .antigravity/genesis/research_briefing.md dosyalarını oku.",
        "1. python3 -m src.metaos_ignite.cli compile komutunu çalıştırarak I-14 zarfını ve IntentContract'ı üret.",
        "2. LC-04..LC-11 kapılarını işletip spec.lock.json kilidini ve V12-05 Triple RED testlerini doğrula.",
        "3. İzole /tmp git worktree içinde (LC-12..LC-17) kodu gerçekleyip tüm kapıları GREEN yap ve",
        "   python3 -m src.metaos_ignite.cli project-cockpit ile Obsidian kokpitini güncelle.",
        "```",
        "",
        "---",
        "",
        "## Bölüm 5: Obsidian Kokpit Kurulumu & Canlı İzleme (`docs/cockpit/`)",
        "",
        "1. **Obsidian** uygulamasını açın -> **Open folder as vault** seçeneğiyle proje kök dizinini (veya doğrudan `docs/cockpit/` klasörünü) açın.",
        "2. `docs/cockpit/` altında sıfır LLM token'ı (`I-07`) ile üretilen 4 canlı görünümü inceleyin:",
        "   - `DASHBOARD.md`: Mevcut durum (`current_state`), aktif arketip, risk sınıfı ve Sütun 9.2 Meta-Metrics karnesi.",
        "   - `STATE_GRAPH.md`: `LC-01..LC-22A` durum makinesinin ziyaret edilen ve aktif düğümlerini renklendiren Mermaid akış diyagramı.",
        "   - `DECISION_QUEUE.md`: `.antigravity/outbox/` içindeki insan onay kapıları (`HANDSHAKE_REVIEW`, `HUMAN_AUDIT_REVIEW`) ve dizi diyagramı.",
        "   - `EVIDENCE_LEDGER.md`: `research_briefing.md` -> `IntentContract` -> `spec.lock.json` -> `ProofReceipt` kriptografik kanıt soyağacı.",
        "3. **Graph View Ayarı:** Obsidian sol menüsünden **Open graph view** (`Cmd+G`) açarak `[[DASHBOARD]]`, `[[STATE_GRAPH]]`, `[[DECISION_QUEUE]]` ve `[[EVIDENCE_LEDGER]]` arasındaki canlı `[[wikilink]]` topolojisini izleyin.",
        "",
    ])

    guide_abs = os.path.join(root, output_path) if not os.path.isabs(output_path) else output_path
    os.makedirs(os.path.dirname(guide_abs), exist_ok=True)
    canonical_guide = canonical.canonical_text(guide_md)
    with open(guide_abs, "wb") as fh:
        fh.write(canonical_guide.encode("utf-8"))

    hits = secrets.scan_text(canonical_guide)
    if hits:
        raise RuntimeError("I-12 secret detected in IGNITE_GUIDE.md: %r" % (hits,))

    return {
        "valid": True,
        "guide_path": os.path.relpath(guide_abs, root).replace(os.sep, "/"),
        "guide_sha256": canonical.file_sha256(guide_abs),
        "templates": sorted(template_paths),
    }
