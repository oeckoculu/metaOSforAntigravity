# Meta-OS v1.2 As-Built Sistem Mimarisi, Değişmezleri ve Harici Yapay Zeka Başvuru Belgesi (`META_OS_EXTERNAL_CONTEXT.md`)

> **Belgenin Amacı:** Bu dosya; Meta-OS tabanlı yeni bir yazılım projesine başlarken **Google NotebookLM** defterine ve **Gemini Chat** (veya benzeri harici LLM) oturumuna sistem kaynağı olarak yüklenmek üzere deterministik olarak üretilmiştir. Sistemin anayasal sınırlarını, 15 değişmezini, 29 durumlu yaşam döngüsünü, 6 evrensel arketipini ve Day-0 hazırlık protokolünü ("Grill Me") eksiksiz açıklar.

---

## BÖLÜM 1: AS-BUILT MİMARİ VE 15 KANONİK DEĞİŞMEZ (`I-01` .. `I-15`)

Meta-OS v1.2, yapay zeka ajanlarının otonom yazılım geliştirme süreçlerini **fail-closed (varsayılan olarak reddeden)** bir anayasal çekirdekle denetleyen çift katmanlı bir işletim sistemidir.

```
+---------------------------------------------------------------------------------------+
| KATMAN A: IMMUTABLE KERNEL (Dondurulmuş Çekirdek — 97 Dosya, Merkle SHA256 Korumalı)   |
|  .antigravity/kernel/  .antigravity/policies/  .antigravity/schemas/  scripts/        |
|  Ajanlar (AGENT) bu katmanı doğrudan DEĞİŞTİREMEZ, git commit/merge/push YAPAMAZ.     |
+---------------------------------------------------------------------------------------+
                                          | Sıkı PEP/PDP Kapıları & SSH İmzalı Doğrulama
                                          v
+---------------------------------------------------------------------------------------+
| KATMAN B: USER APPLICATION & POLYMORPHIC AGENT ROOM (Kullanıcı ve Proje Alanı)         |
|  contracts/  invariants/  src/  tests/  receipts/  provenance/  docs/  infra/        |
|  6 Evrensel Arketip, Hermetik Stdlib Yürütme, İzole /tmp Git Worktree, 5-Oracle Test |
+---------------------------------------------------------------------------------------+
```

### 15 Kanonik Sistem Değişmezi (Invariants)
1. **`I-01` (Ayrıcalıklı Yürütücü Sınırı):** Ajanlar (`actor.kind == AGENT`) doğrudan git işlemleri (`commit`, `merge`, `push`, `reset`) yapamaz. Tüm birleştirmeler doğrulanmış `ProofReceipt` ile `EXECUTOR` tarafından icra edilir.
2. **`I-02` (Katman A Dokunulmazlığı):** Katman A dosyaları (`.antigravity/`, `.agents/`, `scripts/`, `SPEC_META_OS_v1.1.md`) mühürlüdür. Merkle kökü her oturumda (`./scripts/kernel_lock`) doğrulanır.
3. **`I-03` (Olay Kaynaklı Gerçeklik Kaynağı):** `.antigravity/events/run-*.jsonl` tek kesin doğruluk kaynağıdır. `state_board.json` ve kokpitler tek yönlü deterministik projeksiyonlardır.
4. **`I-04` (Önce-Kontrat Prensibi):** Kod yazılmadan önce `IntentContract` ve `spec.lock.json` kilitlenmelidir.
5. **`I-05` (Öz-Değişiklik İnsan Onayı):** Katman A veya anayasa değişikliği formal `ChangeProposal` (`self_modification: true`, `risk_class: R4`) ve SSH imzalı `HUMAN` onay token'ı gerektirir.
6. **`I-06` (Açık Risk Sınıflandırması):** Her değişiklik `R0`..`R4` risk sınıflarından birine atanır. `R2..R4` insan denetim kapısını tetikler.
7. **`I-07` (Sıfır-Token Projeksiyonu):** Obsidian kokpiti ve rehberler sıfır LLM token'ı tüketilerek doğrudan diskteki kanıtlardan üretilir.
8. **`I-08` (Fail-Closed İlkesi):** Belirsizlik, eksik kanıt veya politika ihlali durumunda sistem durur ve durumu `QUARANTINED` veya ret yapar.
9. **`I-09` (İzole Geçici Worktree Yürütmesi):** Kod değişiklikleri ana repoda değil, `/tmp` altındaki izole `git worktree` içinde test edilir.
10. **`I-10` (Deterministik Tohumlanmış Tekrar):** Testler ve değerlendirmeler `--seed` parametresi ile tekrarlanabilir olmalıdır.
11. **`I-11` (İşlemsel Yerel Giden Kutusu):** İnsan incelemeleri `.antigravity/outbox/` dizininde yayınlanır ve yalnızca insan anahtarıyla (`./scripts/outbox_ack`) onaylanır.
12. **`I-12` (Sıfır-Gizli Prensibi):** Kod, günlük veya belgelere hiçbir API anahtarı, parola veya SSH özel anahtarı sızamaz (`secrets.scan_*`).
13. **`I-13` (Kapsamlı Denetim Makbuzları):** Her faz kriptografik SHA-256 özeti ve zaman damgalı makbuzla kanıtlanır.
14. **`I-14` (Güvensiz İçerik İzolasyonu):** Harici girdiler (NotebookLM, web, kullanıcı metni) `UntrustedContentEnvelope` içine alınır ve doğrudan yürütülemez.
15. **`I-15` (Monotonik İleri-İlerleme):** Durum makinesi asla geriye sıçramaz; hata durumunda karantina veya yeniden niyet yakalama rotası izlenir.

### Anayasal Düzeltmeler (`C-1..C-8`) ve v1.2 Ekleri (`V12-01..V12-06`)
- **`C-1` (Kaynak-Kapsamlı Rota Denetimi):** `HUMAN_AUDIT_REQUIRED` kapısına yalnızca `PROOF_ASSEMBLED` aşamasından tam kanıt paketiyle gelen işler geçebilir.
- **`C-6` / `LC-04`:** `GENESIS_LOCKED` -> `INTENT_CAPTURED` geçişi hem `InitializedWorkspace` hem de doğrulanmış `IntentContract` gerektirir.
- **`V12-05` (Üçlü RED Test Kahini):** Test başarısızlığı yalnızca sözdizimi geçerliyken (`CompilationSuccess == true`), test koşulmuşken (`RuntimeExecution == EXECUTED`) ve çıkış kodu sıfırdan farklıyken (`TestExitCode != 0`) kabul edilir. Derleme hatası asla RED sayılamaz.
- **`V12-06` (Karantina İzolasyonu):** `QUARANTINED` tespiti yapılan iş doğrudan birleştirilemez; insan müdahalesiyle temizlenip `INTENT_CAPTURED` aşamasına dönmelidir.

---

## BÖLÜM 2: 29 DURUMLU YAŞAM DÖNGÜSÜ, RİSK SINIFLARI VE KABUL KAHİNLERİ

### 29 Durumlu Yaşam Döngüsü (`LC-01` .. `LC-22A`)
```
GENESIS_LOCKED -> INTENT_CAPTURED -> RISK_CLASSIFIED
                      |                       |
                      | (R0/R1)               v (R2..R4)
                      |                  HANDSHAKE_PENDING
                      |                       | (Human Approval)
                      v                       v
               CONTRACT_DRAFTING -> CONTRACT_REVIEWED -> TESTS_ARMED_RED
                                                              | (V12-05 Triple RED)
                                                              v
                                                       CHANGE_ADMITTED
                                                              |
                                                              v
SANDBOX_EXECUTING -> WORKTREE_GREEN -> MUTATION_TESTED -> STATIC_ANALYSIS_PASSED
                                                              |
                                                              v
POST_DEPLOY_OBSERVING <- MERGED <- READY_TO_MERGE <- PROOF_ASSEMBLED <- PERFORMANCE_VERIFIED
        |                                ^                 |
        v                                | (R0/R1 LC-18B)  v (R2..R4 LC-18A)
     CLOSED                              +---------- HUMAN_AUDIT_REQUIRED (SSH-Signed Token)
```

### Risk Sınıfları (`R0` .. `R4`)
- **`R0` (Önemsiz/Yazım Hatası):** Dokümantasyon, açıklama satırları, kod dışı düzeltmeler. İnsan kapısı gerektirmez (`LC-06B`, `LC-18B` otomatik).
- **`R1` (Dahili Kırılmayan Geliştirme):** Dahili fonksiyonlar, performans optimizasyonları, test genişletmeleri. `fast-track` ile tek komutta tamamlanır (`LC-18B`).
- **`R2` (Standart Özellik / API Eklenmesi):** Yeni API uç noktaları, modül implementasyonları. `HANDSHAKE_REVIEW` ve `HUMAN_AUDIT_REVIEW` zorunludur.
- **`R3` (Kritik / Mimari / Şema Değişikliği):** Veritabanı şeması, yetkilendirme modeli veya kriptografi değişiklikleri. Çoklu insan onayı gerektirir.
- **`R4` (Anayasal / Katman A Öz-Değişikliği):** `.antigravity/`, `scripts/` veya `SPEC_META_OS_v1.1.md` değişikliği. Merkle kilidi yenilenir ve SSH imzası şarttır.

### 5 Zorunlu Kabul Kahini (Acceptance Oracles)
Her `IntentContract`, değişikliklerin doğrulanması için 5 sınıftan en az birer test kahini bağlamalıdır:
1. **`CONTRACT` (`ORC-001`):** JSON Schema, OpenAPI veya tip kontratı doğrulaması (`schema.Validator`).
2. **`PROPERTY` (`ORC-002`):** Tohumlanmış kombinatoryal ve değişmezlik testleri (`property_strategies`).
3. **`GOLDEN` (`ORC-003`):** Beklenen altın çıktılarla birebir deterministik eşleşme denetimi.
4. **`PERF` (`ORC-004`):** Milisaniye veya bellek bütçesi (p99 latency, heap limit, cold-start) denetimi.
5. **`SECURITY` (`ORC-005`):** AST statik güvenlik analizi, `I-12` gizli anahtar taraması ve `I-14` zarf izolasyonu.

---

## BÖLÜM 3: 6 EVRENSEL ARKETİP VE ARAÇ ZİNCİRİ MATRİSİ (`archetypes.py`)

Meta-OS Katman B, her türlü yazılım projesini dil-bağımsız olarak bağlayan 6 evrensel arketip sağlar:

| Arketip ID | Kullanım Senaryosu | Varsayılan Dizinler | Polimorfik Kapılar & Metrik Bütçeleri (`V12-03`) |
| :--- | :--- | :--- | :--- |
| `Backend_API` | REST/gRPC mikroservisler, API sunucuları | `contracts/openapi`, `src/service`, `tests/integration` | OpenAPI AuthZ, p99 gecikme <= `150ms`, maks 4 DB sorgusu/istek |
| `FullStack_Web` | Modern web uygulamaları, BFF + UI | `contracts/ui_state`, `src/web`, `src/api`, `tests/e2e` | CSP/DOM XSS & CSRF denetimi, Core Web Vitals (`LCP < 2000ms`) |
| `Data_ML_Pipeline` | Veri ambarı, ETL/ELT, ML boru hatları | `contracts/data_schema`, `src/pipeline`, `tests/data` | PII sızıntı & zehirlenme taraması, verim >= `10k satır/sn` |
| `CLI_SDK` | Komut satırı araçları, SDK'lar, kütüphaneler | `contracts/cli_spec`, `src/cli`, `tests/cli` | AST tehlikeli çağrı denetimi, hermetik SBOM, soğuk başlatma < `250ms` |
| `Autonomous_Agent` | Çoklu ajan sistemleri, araç kullanan ajanlar | `contracts/agent_caps`, `src/agents`, `tests/agent_eval` | `I-14` zarf denetimi, CapabilityToken denetimi, adım gecikmesi < `500ms` |
| `Embedded_IoT` | Firmware, RTOS görevleri, HAL | `contracts/hal_spec`, `src/firmware`, `tests/hardware_mock` | Yığın/bellek limit denetimi, imzalı önyükleme, WCET < `500us` |

- **Desteklenen Diller:** `python`, `typescript`, `go`, `rust`, `generic`.
- **Kanonik Kanıt Tipleri:** `ArchetypeSecurityScanProof`, `ArchetypePerformanceScanProof`.

---

## BÖLÜM 4: BİREBİR GİRDİ ŞABLONLARI (EXACT INPUT TEMPLATES)

Meta-OS derleyicisinin (`compiler.py`) Day-0 ateşlemesinde kabul ettiği iki kanonik dosya formatı:

### 1. `.antigravity/genesis/project_manifest.json`
```json
{
  "schema_version": "1.0.0",
  "project_name": "Proje_Adi_Buraya",
  "primary_archetype": "Backend_API",
  "secondary_archetypes": ["Data_ML_Pipeline"],
  "language": "python",
  "risk_class": "R2",
  "owner": "human:oeckoculu",
  "budgets": {
    "max_budget_usd": 10,
    "max_wall_clock_minutes": 60
  },
  "notes": "primary_archetype: Backend_API, FullStack_Web, Data_ML_Pipeline, CLI_SDK, Autonomous_Agent, Embedded_IoT seçeneklerinden biri olmalıdır."
}
```

### 2. `.antigravity/genesis/research_briefing.md`
```markdown
# NotebookLM Arastirma Ozeti (Research Briefing)

## 1. Problem Tanimi ve Vizyon
- Cozulmek istenen somut problem, hedef sistem siniri ve ana kullanici senaryosu.

## 2. Olculebilir Hedefler (Desired Outcomes)
- **DO-1:** Birincil fonksiyonel cikti ve basari olcutu.
- **DO-2:** Performans, gecikme ve bellek butcesi hedefleri.
- **DO-3:** Guvenlik, gizlilik ve PII/secret sizdirmazlik hedefleri.
- **DO-4:** Dokumantasyon, kullanici rehberi ve kokpit gorunumleri.

## 3. Mimari Sinirlar ve Kisitlar (Constraints & Out-of-Scope)
- Kullanilacak programlama dili ve arac zinciri (ornek: stdlib-only python3).
- Yasakli paketler, izin verilmeyen harici servisler ve kapsam disi moduller.
- Butce siniri: maks 10 USD, maks 60 dakika.

## 4. Kabul Kahinleri (Acceptance Oracles — 5 Zorunlu Sinif)
- `CONTRACT` (`ORC-001`): Kontrat ve sema dogrulama komutu.
- `PROPERTY` (`ORC-002`): Rastgele tohumlu ozellik ve degismezlik testi.
- `GOLDEN` (`ORC-003`): Altin ornek ve deterministik cikti dogrulamasi.
- `PERF` (`ORC-004`): Calisma zamani veya gecikme butcesi testi.
- `SECURITY` (`ORC-005`): Guvenlik, AST ve gizli anahtar sizinti taramasi.
```

---

## BÖLÜM 5: HARİCİ YAPAY ZEKA İÇİN "GRILL ME & DOSYA ÜRETİM PROTOKOLÜ"

Bu belgeyi referans alan harici bir AI asistanı (Gemini Chat, NotebookLM, Claude veya benzeri), kullanıcı "Yeni bir projeye başlamak istiyorum" dediğinde aşağıdaki operasyonel protokolü işletmelidir:

### Harici AI Sistem Rolü ve Davranış Kuralları
1. **Rol:** Sen Meta-OS v1.2 anayasasını (`SPEC_META_OS_v1.1.md`) ve Katman B polimorfik kurallarını savunan, titiz ve deneyimli bir **Kıdemli Sistem Mimarı (Staff Principal Architect)** rolündesin.
2. **Tek Seferde Yalnızca 2-3 Soru Sor ("Grill Me"):** Kullanıcıyı soru yağmuruna tutma. Her turda en fazla 2-3 kritik ve seçenekli mimari soru yönelterek tasarım ağacının dallarını sırayla kapat:
   - **Tur 1 (Kapsam & Arketip):** Ne inşa etmek istiyorsun? 6 evrensel arketipten hangisi birincil (`primary_archetype`), hangisi ikincil? Hedef dil ve platform ne?
   - **Tur 2 (Hedefler & Metrikler):** `DO-1..DO-4` seviyesinde ölçülebilir çıktılar neler? Gecikme bütçesi (ms), throughput veya bellek kısıtın var mı?
   - **Tur 3 (Risk & Güvenlik):** Değişikliğin risk sınıfı ne (`R0..R4`)? PII, gizli anahtar veya veritabanı şemasına temas ediyor mu?
3. **Tavsiye Edilen Seçeneği Belirt:** Soruları yöneltirken her zaman `(Tavsiye Edilen)` etiketiyle güçlü bir mühendislik tercihi öner.
4. **Nihai Çıktıyı Eksiksiz Kod Blokları Olarak Sun:** Kullanıcıyla tasarımda tam mutabakat sağlandıktan sonra, başka hiçbir açıklama yapmadan doğrudan kopyalanıp yapıştırılacak şu iki bloğu üret:
   - `.antigravity/genesis/project_manifest.json` (Bölüm 4'teki şemaya %100 uyumlu JSON)
   - `.antigravity/genesis/research_briefing.md` (Bölüm 4'teki 4 zorunlu başlığı içeren Markdown)
