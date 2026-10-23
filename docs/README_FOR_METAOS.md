# Meta-OS v1.2: Polymorphic AI-Native Project Operating System

[![Meta-OS CI Harness](https://github.com/oeckoculu/metaOS/actions/workflows/metaos_ci.yml/badge.svg)](https://github.com/oeckoculu/metaOS/actions/workflows/metaos_ci.yml)
[![Kernel Lock](https://img.shields.io/badge/Kernel_Lock-97_Files_Verified-success)](.antigravity/genesis/kernel_lock.json)
[![Stdlib Only](https://img.shields.io/badge/Dependencies-Zero_Third_Party_(Stdlib_Only)-blue)](#hermetik-calisma-prensipleri)
[![Obsidian Cockpit](https://img.shields.io/badge/Obsidian-Zero_Token_Graph_View-purple)](docs/cockpit/)

**Meta-OS**, otonom yapay zeka ajanlarının (Antigravity, Gemini, Claude, OpenAI) yazılım geliştirme süreçlerini **fail-closed (varsayılan olarak engelleyen)** bir anayasal çekirdekle denetleyen, her türlü yeni projeyi (Web, Backend API, Veri/ML, CLI/SDK, Otonom Ajan, IoT) tek komutla başlatan ve tüm süreci **Obsidian** üzerinde canlı bir kokpitle görselleştiren polimorfik bir **Yapay Zeka Yerel Proje İşletim Sistemidir (AI-Native Project OS)**.

---

## 🏛️ Mimari Felsefe: Çift Katmanlı Tasarım (Dual-Layer Topology)

Meta-OS, ajanların sistem sınırlarını aşmasını ve depoyu bozmasını matematiksel ve kriptografik kesinlikle engelleyen iki katmandan oluşur:

```
+---------------------------------------------------------------------------------------+
| KATMAN A: IMMUTABLE KERNEL (Dondurulmuş Çekirdek — 97 Dosya, Merkle SHA256 Korumalı)   |
|  .antigravity/kernel/  .antigravity/policies/  .antigravity/schemas/  scripts/        |
|  * Ajanlar (AGENT) bu katmanı doğrudan DEĞİŞTİREMEZ, üzerine yazamaz.                 |
|  * git commit/merge/push/reset komutlarını ajanlar doğrudan ÇALIŞTIRAMAZ (I-01).     |
|  * Merkle Kökü: sha256:fdc68cb03c9b1b5fd3e0648ea6b46ab0b6b9935a0ad2849fee91116975717aed |
+---------------------------------------------------------------------------------------+
                                          |
                                          | Sıkı PEP/PDP Kapıları & SSH İmzalı Doğrulama
                                          v
+---------------------------------------------------------------------------------------+
| KATMAN B: USER APPLICATION & POLYMORPHIC AGENT ROOM (Kullanıcı ve Proje Odası)         |
|  contracts/  invariants/  src/  tests/  receipts/  provenance/  docs/  infra/        |
|  * 6 Evrensel Arketip (Backend API, Web, Data/ML, CLI, Agent, IoT)                    |
|  * İzole /tmp Git Worktree İçinde Test ve Derleme (I-09)                             |
|  * V12-05 Üçlü RED Test Kahini & 5 Kabul Kahini (Contract, Property, Golden, Perf, Sec)|
|  * Sıfır LLM Token'ı tüketen Canlı Obsidian Vault Projeksiyonu (I-07)                 |
+---------------------------------------------------------------------------------------+
```

---

## 🔒 15 Kanonik Sistem Değişmezi (Invariants)

1. **`I-01` (Ayrıcalıklı Yürütücü Sınırı):** Ajanlar doğrudan git işlemleri yapamaz. Yalnızca doğrulanmış kanıtlarla `EXECUTOR` birleştirme yapabilir.
2. **`I-02` (Katman A Dokunulmazlığı):** 97 çekirdek dosyası mühürlüdür; Merkle kökü her oturumda (`./scripts/kernel_lock`) doğrulanır.
3. **`I-03` (Olay Kaynaklı Gerçeklik Kaynağı):** `.antigravity/events/run-*.jsonl` tek gerçeklik kaynağıdır. `state_board.json` tek yönlü projeksiyondur.
4. **`I-04` (Önce-Kontrat İlkesi):** Kod yazılmadan önce `IntentContract` ve `spec.lock.json` dondurulmalıdır.
5. **`I-05` (Öz-Değişiklik İnsan Onayı):** Katman A değişikliği SSH-ed25519 imzalı insan onay token'ı (`HumanApprovalToken`) gerektirir.
6. **`I-06` (Açık Risk Sınıflandırması):** Her iş `R0`..`R4` risk sınıflarından birine atanır; `R2..R4` insan denetim kapısını tetikler.
7. **`I-07` (Sıfır-Token Projeksiyonu):** Obsidian kokpiti ve rehberler sıfır LLM token'ı harcanarak diskten üretilir.
8. **`I-08` (Fail-Closed İlkesi):** Belirsizlik veya ihlal anında sistem çalışmayı durdurur (`QUARANTINED`).
9. **`I-09` (İzole Geçici Worktree Yürütmesi):** Kod değişiklikleri ana repoda değil, `/tmp` altındaki izole `git worktree` içinde test edilir.
10. **`I-10` (Deterministik Tohumlanmış Tekrar):** Tüm testler `--seed` parametresiyle tekrarlanabilir olmalıdır.
11. **`I-11` (İşlemsel Yerel Giden Kutusu):** İnsan onay talepleri `.antigravity/outbox/` dizininde yayınlanır.
12. **`I-12` (Sıfır-Gizli Prensibi):** Günlüklere veya belgelere hiçbir parola veya API anahtarı sızamaz (`secrets.scan_*`).
13. **`I-13` (Kapsamlı Denetim Makbuzları):** Her faz kriptografik SHA-256 zaman damgalı makbuzla kanıtlanır.
14. **`I-14` (Güvensiz İçerik İzolasyonu):** Harici girdiler (NotebookLM, web) `UntrustedContentEnvelope` içine alınır ve doğrudan yürütülemez.
15. **`I-15` (Monotonik İleri-İlerleme):** Durum makinesi asla geriye sıçramaz.

---

## ⚡ 3 Dakikada Hızlı Başlangıç (Quickstart)

```bash
# 1. Depoyu klonlayın ve anayasal bütünlüğü doğrulayın
git clone https://github.com/oeckoculu/metaOS.git yeni-projem
cd yeni-projem
make verify
```

### Adım 1: Keşif Stüdyosu (NotebookLM + Gemini Chat)
- [`docs/META_OS_EXTERNAL_CONTEXT.md`](docs/META_OS_EXTERNAL_CONTEXT.md) dosyasını **Google NotebookLM** defterinize yükleyin.
- Gemini Chat oturumunda NotebookLM defterinizi bağlayın ve şu mülakat promptunu gönderin:
  > *"META_OS_EXTERNAL_CONTEXT.md belgesini baz alarak benimle interaktif bir 'Grill Me' mimari mülakatı başlat. Her turda en fazla 2-3 soru sorarak problem tanımını, DO-1..DO-4 hedeflerini, 6 arketipten hangisini seçeceğimizi ve risk sınıfını (R0..R4) netleştir. Mutabık kaldığımız an project_manifest.json ve research_briefing.md dosyalarını üret."*
- Üretilen çıktıları `.antigravity/genesis/project_manifest.json` ve `.antigravity/genesis/research_briefing.md` olarak kaydedin.

### Adım 2: Projeyi Yeni Arketip ile Başlatma
```bash
# Tek komutla temiz Day-0 başlatma (Tavsiye Edilen):
make init ARCHETYPE=Backend_API LANG=python NAME=yeni_projem

# Veya doğrudan CLI parametreleri ile:
python3 -m src.metaos_ignite.cli init-new-project --run-id run-0001 --archetype Backend_API --language python
```

### Adım 3: Antigravity IDE ile Day-0 Ateşleme
Antigravity IDE içinde projeyi açın ve ajana şu promptu gönderin:
> *"SPEC_META_OS_v1.1.md anayasasını ve .antigravity/genesis/ dosyalarını oku. `python3 -m src.metaos_ignite.cli compile` çalıştırarak IntentContract'ı derle, V12-05 Triple RED testlerini doğrula, izole /tmp git worktree içinde kodu implemente et ve kokpiti güncelle."*

### Adım 4: Düşük Riskli Geliştirmeler İçin `fast-track`
Küçük düzeltmeler, test eklemeleri ve dahili refactor (`R0`/`R1`) işleri için insan kapısına takılmadan tek komutla test ve kokpit güncellemesi yapın:
```bash
make fast-track
# veya doğrudan CLI ile:
python3 -m src.metaos_ignite.cli fast-track --risk R1
```

### Adım 5: Obsidian Canlı Kokpiti Açma
1. **Obsidian** uygulamasında **Open folder as vault** diyerek proje kök dizinini açın.
2. `Cmd+G` ile Graph View açın ve arama filtresine `-path:.git` yazın.
3. Canlı görünümleri izleyin:
   - [`docs/cockpit/DASHBOARD.md`](docs/cockpit/DASHBOARD.md) (Canlı metrikler ve durum panosu)
   - [`docs/cockpit/STATE_GRAPH.md`](docs/cockpit/STATE_GRAPH.md) (Mermaid 29-durumlu akış diyagramı)
   - [`docs/cockpit/DECISION_QUEUE.md`](docs/cockpit/DECISION_QUEUE.md) (Giden kutusu karar sırası)
   - [`docs/cockpit/EVIDENCE_LEDGER.md`](docs/cockpit/EVIDENCE_LEDGER.md) (Kriptografik SHA-256 kanıt soyağacı)

---

## 🎯 6 Evrensel Arketip Matrisi

| Arketip ID | Kullanım Senaryosu | Varsayılan Dizinler | Polimorfik Kapılar & Metrik Bütçeleri (`V12-03`) |
| :--- | :--- | :--- | :--- |
| `Backend_API` | REST/gRPC mikroservisler, API sistemleri | `contracts/openapi`, `src/service`, `tests/integration` | OpenAPI AuthZ, p99 gecikme <= `150ms`, maks 4 DB sorgusu/istek |
| `FullStack_Web` | Web uygulamaları, BFF + UI | `contracts/ui_state`, `src/web`, `src/api`, `tests/e2e` | CSP/DOM XSS & CSRF denetimi, Core Web Vitals (`LCP < 2000ms`) |
| `Data_ML_Pipeline` | Veri ambarı, ETL/ELT, ML boru hatları | `contracts/data_schema`, `src/pipeline`, `tests/data` | PII sızıntı & zehirlenme taraması, verim >= `10k satır/sn` |
| `CLI_SDK` | Komut satırı araçları, SDK'lar | `contracts/cli_spec`, `src/cli`, `tests/cli` | AST tehlikeli çağrı denetimi, hermetik SBOM, soğuk başlatma < `250ms` |
| `Autonomous_Agent` | Çoklu ajan sistemleri, araç kullanımı | `contracts/agent_caps`, `src/agents`, `tests/agent_eval` | `I-14` zarf denetimi, CapabilityToken denetimi, adım gecikmesi < `500ms` |
| `Embedded_IoT` | Firmware, RTOS görevleri, HAL | `contracts/hal_spec`, `src/firmware`, `tests/hardware_mock` | Yığın/bellek limit denetimi, imzalı önyükleme, WCET < `500us` |

---

## 🧠 Yetkinlik Tabanlı Model Yönlendirme (Capability-Based Routing)

| Katman / Görev Tipi | Model Sınıfı | Kullanım Alanı ve Görevler |
| :--- | :--- | :--- |
| **Tier-1: Deep Reasoning & Architecture** | Gemini 2.5/3 Pro, Claude 3.7 Sonnet Thinking, o3-mini | Day-0 niyet kontratı sentezi, tehdit modelleme, anayasal güvenlik sınırları, kök neden analizi. |
| **Tier-2: Fast Coding & Iteration** | Gemini 3.8 Flash, Claude 3.5 Sonnet, GPT-4o | İzole worktree içinde kod yazımı, test geliştirme, fonksiyon implementasyonları. |
| **Tier-0: Deterministic Projection** | Yerel Stdlib Python CLI (0 LLM Token) | Merkle kilidi denetimi, Obsidian kokpiti projeksiyonu, durum geçişleri (`make verify`, `make cockpit`). |

---

## 🛠️ Operasyonel Komutlar (`Makefile`)

| Hedef | Açıklama |
| :--- | :--- |
| `make init` | Yeni bir projeyi seçilen arketip ve dil ile temiz `run-0001` günlüğünde başlatır (örn: `make init ARCHETYPE=Backend_API LANG=python`). |
| `make status` | Mevcut durum makinesi aşamasını (`current_state`) ve aktif olay günlüğü kimliğini anında gösterir. |
| `make verify` | 97 Katman A dosyasının Merkle kilidini, kernel self-test'ini, event journal'ını ve PEP politikasını doğrular. |
| `make test` | 5-Oracle test süitini (`tests/run_suite.py`) tohumlanmış (`--seed 42`) yeşil doğrulama modunda çalıştırır. |
| `make fast-track` | Düşük riskli (`R1`) değişiklikler için izole sandbox testini, kanıt paketini ve kokpiti tek adımda günceller. |
| `make cockpit` | Sıfır token (`I-07`) ile Obsidian kokpit dosyalarını diske projekte eder. |
| `make guide` | Başucu rehberi (`IGNITE_GUIDE.md`) ve harici bağlam belgesini (`META_OS_EXTERNAL_CONTEXT.md`) yeniden üretir. |
| `make all` | Doğrulama, test, rehber ve kokpit hedeflerini sırayla uçtan uca çalıştırır. |

---

## 📚 Dokümantasyon ve Referanslar

- [📖 `docs/IGNITE_GUIDE.md`](docs/IGNITE_GUIDE.md): 5 aşamalı Türkçe Day-0 operasyon kılavuzu.
- [🧠 `docs/META_OS_EXTERNAL_CONTEXT.md`](docs/META_OS_EXTERNAL_CONTEXT.md): NotebookLM ve Gemini Chat için tek parça As-Built sistem başvuru belgesi.
- [📊 `docs/cockpit/`](docs/cockpit/): Obsidian Graph View canlı kokpit dizini.
- [📜 `SPEC_META_OS_v1.1.md`](SPEC_META_OS_v1.1.md): Meta-OS Değişmez Çekirdek Anayasası.

---

## 🛡️ Güvenlik & Gizlilik İlkeleri

- **Sıfır Dış Bağımlılık (Stdlib-Only):** Katman A ve Katman B araçları sıfır harici `pip` paketi (`stdlib-only` Python 3, `make`, `git`, `ssh-keygen`) ile çalışır; tedarik zinciri saldırılarına kapalıdır.
- **Sıfır Gizli Bilgi (Zero-Secret):** Tüm dosyalar ve olay günlükleri `I-12` uyarınca otomatik gizli bilgi taramasından (`secrets.scan_*`) geçirilir. Hiçbir özel anahtar veya API token'ı depolanmaz.

---
*Meta-OS v1.2 — Architected & Engineered with Fail-Closed Disciplinary Rigor.*
