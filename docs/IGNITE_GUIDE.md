# Meta-OS Universal Day-0 Ignite & Obsidian Kokpit Başucu Rehberi (`IGNITE_GUIDE.md`)

Bu kılavuz, `metaOSforAntigravity` şablon deposunu klonlayarak yeni bir yazılım projesini **NotebookLM**, **Antigravity** ve **Obsidian** üçlüsüyle sıfırdan başlatmak, doğrulamak ve yönetmek için hazırlanmış 5 aşamalı operasyonel kontrol listesidir.

---

## AŞAMA 1: KEŞİF STÜDYOSU (NotebookLM + Gemini Chat "Grill Me")

Yeni bir projeye başlamadan önce tüm mimari kararları ve kontrat gereksinimlerini harici yapay zeka ile netleştirin:

1. **Kaynak Yükleme:** `docs/META_OS_EXTERNAL_CONTEXT.md` dosyasını ve projenize ait makale/RFC dokümanlarını **Google NotebookLM** defterinize yükleyin.
2. **Gemini Chat Oturumu:** Gemini Chat (veya harici LLM) oturumunuza NotebookLM defterini bağlayın.
3. **Mülakat Başlatma Promptu:** Aşağıdaki promptu kopyalayıp Gemini Chat'e gönderin:

```text
Yüklediğim META_OS_EXTERNAL_CONTEXT.md belgesini ve proje dokümanlarımı kaynak al.
Meta-OS v1.2 kuralları uyarınca benimle interaktif bir 'Grill Me' mimari mülakatı başlat.
Her turda en fazla 2-3 odaklanmış soru sorarak problem tanımını, DO-1..DO-4 hedeflerini,
6 arketipten hangisini seçeceğimizi ve risk sınıfını (R0..R4) netleştir.
Mutabık kaldığımız an, .antigravity/genesis/project_manifest.json ve
.antigravity/genesis/research_briefing.md dosyalarını hatasız üret.
```

4. **Dosyaları Kaydetme:** Mülakat sonunda üretilen çıktıları projenizin şu konumlarına kaydedin:
   - `.antigravity/genesis/project_manifest.json`
   - `.antigravity/genesis/research_briefing.md`

---

## AŞAMA 2: GITHUB TEMPLATE KLONLAMA & PROJE SIFIRLAMA

GitHub üzerinde bu repoyu **"Use this template"** seçeneğiyle yeni bir depoya klonlayın ve Katman A kilit bütünlüğünü doğrulayın:

```bash
git clone <yeni-repo-url> yeni-proje-adi
cd yeni-proje-adi

# Katman A Merkle Kilidi ve Self-Test Doğrulaması (97 kilitli dosya)
./scripts/kernel_lock
./scripts/kernel_selftest
./scripts/pep_session_start
```

- `./scripts/kernel_lock`: `valid: true` ve `total_locked_files: 97` (`sha256:fdc68cb03c9b1b5fd3e0648ea6b46ab0b6b9935a0ad2849fee91116975717aed`) çıktısı vermelidir.
- Aşama 1'de ürettiğiniz `project_manifest.json` ve `research_briefing.md` dosyalarını `.antigravity/genesis/` altına kopyalayın.
- Projenizi seçtiğiniz arketip ile temiz `run-0001` günlüğünde başlatın:

```bash
python3 -m src.metaos_ignite.cli init-new-project --run-id run-0001 --archetype Backend_API --language python
```

---

## AŞAMA 3: ANTIGRAVITY IDE İLE DAY-0 ATEŞLEME & MODEL YÖNLENDİRME

Antigravity IDE içinde projeyi açın ve ajana aşağıdaki hazır Day-0 ateşleme istemini gönderin:

```text
Kök dizindeki SPEC_META_OS_v1.1.md anayasasını, .antigravity/genesis/project_manifest.json
ve .antigravity/genesis/research_briefing.md dosyalarını oku.
1. python3 -m src.metaos_ignite.cli compile komutunu çalıştırarak I-14 zarfını ve IntentContract'ı üret.
2. LC-04..LC-11 kapılarını işletip spec.lock.json kilidini ve V12-05 Triple RED testlerini doğrula.
3. İzole /tmp git worktree içinde (LC-12..LC-17) kodu gerçekleyip tüm kapıları GREEN yap ve
   python3 -m src.metaos_ignite.cli project-cockpit ile Obsidian kokpitini güncelle.
```

### Yetkinlik Tabanlı Model Yönlendirme Matrisi (Capability-Based Routing)

| Katman / Görev Tipi | Model Sınıfı (Örnek Modeller) | Kullanım Alanı ve Nedenleri |
| :--- | :--- | :--- |
| **Tier-1: Deep Reasoning & Architecture** | Gemini 2.5/3 Pro, Claude 3.7 Sonnet Thinking, o3-mini | Day-0 niyet kontratı sentezi, tehdit modelleme, güvenlik sınırları, karmaşık mantıksal hata ayıklama. |
| **Tier-2: Fast Coding & Iteration** | Gemini 3.8 Flash, Claude 3.5 Sonnet, GPT-4o | İzole worktree içinde kod yazımı, test geliştirme, fonksiyon implementasyonları. |
| **Tier-0: Deterministic Projection** | Yerel Stdlib Python CLI (0 LLM Token) | Merkle kilidi denetimi, Obsidian kokpiti projeksiyonu, durum geçişleri, `./scripts/ignite` ve `./scripts/worktree_exec` komutları. |

---

## AŞAMA 4: DÜŞÜK RİSKLİ (`R0`/`R1`) HIZLI İCRA (`fast-track`)

Yazım düzeltmeleri, dahili optimizasyonlar veya test eklemeleri gibi insan onayı gerektirmeyen (`R0` veya `R1`) küçük işler için tek komutlu `fast-track` boru hattını kullanabilirsiniz:

```bash
# R1 risk sınıfı için izole sandbox'ta test koş, kanıt üret ve kokpiti güncelle:
python3 -m src.metaos_ignite.cli fast-track --risk R1
# veya Makefile üzerinden:
make fast-track
```

- Bu boru hattı `LC-06A` ve `LC-18B` kanonik rotalarını kullanarak insan onay kapılarını (`HUMAN_AUDIT_REQUIRED`) otomatik geçer.
- Tüm 5-oracle testlerini koşar, SBOM ve performans kontrollerini doğrular, `ProofReceipt` üretir ve Obsidian kokpitini tek çağrıda günceller.

---

## AŞAMA 5: OBSIDIAN CANLI KOKPİT İZLEME (`docs/cockpit/`)

1. **Vault Açma:** **Obsidian** uygulamasını açın -> **Open folder as vault** seçeneğiyle proje kök dizinini açın.
2. **Graph View Filtresi:** Obsidian sol menüsünden **Open graph view** (`Cmd+G`) açın. Sağ üstteki arama filtresine `-path:.git` yazarak temiz grafik bağlantılarını görüntüleyin.
3. **4 Canlı Görünüm:**
   - `docs/cockpit/DASHBOARD.md`: Mevcut durum (`current_state`), aktif arketip, risk sınıfı ve canlı sayaçlar.
   - `docs/cockpit/STATE_GRAPH.md`: `LC-01..LC-22A` durum makinesinin Mermaid akış şeması (aktif durum yeşil vurgulu).
   - `docs/cockpit/DECISION_QUEUE.md`: `.antigravity/outbox/` içindeki insan inceleme kapıları ve durum dizisi.
   - `docs/cockpit/EVIDENCE_LEDGER.md`: Kontrat, kilit ve test makbuzlarının SHA-256 kriptografik soyağacı.
