# 🧭 Afet Hazırlık Asistanı (Disaster Preparedness Assistant)

**English summary.** A generative-AI assistant that builds a household-specific earthquake preparedness plan
and a 72-hour emergency kit list for families in Türkiye. Users enter who lives in the home (adults, children,
babies, elderly or mobility-restricted members, pets, regular medication) and building details (construction
year, floor, visible cracks). The app combines Google Gemini with the official AFAD guidance (retrieval-augmented
prompts, every line sourced from afad.gov.tr) and deterministic code checks:
building-risk warnings come from fixed rules, not the model, and any required kit item the model forgets is added
automatically. Prompting techniques: role + RAG + hidden chain-of-thought (plan), few-shot (kit list),
zero-shot (child/elderly-friendly explanation). No address, ID or health details are collected.
**SDG 11.5** (reduce deaths and people affected by disasters, focusing on vulnerable groups) and
**SDG 13.1** (strengthen resilience to natural disasters).
Run: create a virtualenv (`python3 -m venv .venv && source .venv/bin/activate`), `pip install -r requirements.txt`, put `GEMINI_API_KEY` in `.env`, `streamlit run app.py`.

---

Hane bilgilerine (kişi sayısı, bebek / çocuk / yaşlı / hareket kısıtlı birey, evcil hayvan, bina yaşı ve kat) göre
**kişiye özel deprem hazırlık planı** ve **72 saatlik afet ve acil durum çantası listesi** hazırlayan üretken yapay zekâ asistanı.

**SDG 11 — Hedef 11.5:** Afetlerden kaynaklanan ölüm ve etkilenen insan sayısını önemli ölçüde azaltmak (yoksul ve kırılgan gruplar odaklı).
**SDG 13 — Hedef 13.1:** İklimle ilgili tehlikelere ve doğal afetlere karşı dayanıklılığı ve uyum kapasitesini güçlendirmek.

## Nasıl çalışır?

| Adım | Ne yapar | Teknik | Prompt |
|---|---|---|---|
| 0 | Bina yaşı, çatlak, kat ve kırılgan birey için **kesin kurallı uyarılar** | Kod (LLM yok) | — |
| 1 | Kişisel plan: öncesi / anında / sonrası + kişiye özel | Rol + **RAG** (AFAD rehberi prompt'a eklenir) + **chain-of-thought** (`dusunce` alanı; kullanıcıya gösterilmez) | `prompts/1_plan.md` |
| 2 | Afet çantası listesi | **Few-shot** (2 örnek) + **RAG** (AFAD rehberi prompt'a eklenir) | `prompts/2_canta.md` |
| 3 | Çocuğa / yaşlıya sade anlatım | **Zero-shot** | `prompts/3_sade_anlatim.md` |
| 4 | Çantada zorunlu eşya kontrolü ve eksik tamamlama | Kod (LLM yok) | — |

Model: Google Gemini 3.5 Flash (yedek: Gemini 3.1 Flash-Lite). Temperature: plan ve çanta için 0.2 (tutarlılık), sade anlatım için 0.5.
Hız ve dayanıklılık: plan ve çanta paralel üretilir (~15-20 sn); model 25 sn içinde cevap vermezse, yoğunsa (503)
ya da günlük kotası dolduysa otomatik olarak yedek modele geçilir; aynı hane bilgisi tekrar gönderilirse sonuç önbellekten gelir.
Kaynak: `data/afad_rehber.txt` (her madde afad.gov.tr sayfalarına dayanır; kaynaklar dosyanın başında).

## Çalıştırma

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # içine GEMINI_API_KEY değerinizi yazın
streamlit run app.py
```

Ücretsiz API anahtarı: https://aistudio.google.com/apikey

## Dosyalar

- `app.py` — arayüz (Streamlit)
- `logic.py` — model çağrıları, kurallı uyarılar, çanta doğrulaması
- `prompts/` — tüm prompt'lar (`0_baseline_zero_shot.md`: ilk sürüm, uygulamada kullanılmıyor)
- `data/afad_rehber.txt` — modele verilen güvenilir kaynak
- `tests/senaryolar.md` — test senaryoları ve sonuçlar
- `tests/degerlendir.py` — senaryoları gerçek modelle çalıştırıp ölçütleri `tests/sonuclar.md`'ye yazar
- `tests/test_ui.py`, `tests/test_logic.py` — model çağrısı yapmayan testler (`python -m unittest discover tests`)
- `rapor.pdf` — proje raporu
