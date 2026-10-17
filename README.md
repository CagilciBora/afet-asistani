# 🧭 Afet Hazırlık Asistanı (Disaster Preparedness Assistant)

Hane bilgilerine (kişi sayısı, bebek / çocuk / yaşlı / hareket kısıtlı birey, evcil hayvan, bina yaşı ve kat) göre
**kişiye özel deprem hazırlık planı** ve **72 saatlik afet ve acil durum çantası listesi** hazırlayan üretken yapay zekâ asistanı.

**SDG 11 — Hedef 11.5:** Afetlerden kaynaklanan ölüm ve etkilenen insan sayısını önemli ölçüde azaltmak (yoksul ve kırılgan gruplar odaklı).
**SDG 13 — Hedef 13.1:** İklimle ilgili tehlikelere ve doğal afetlere karşı dayanıklılığı ve uyum kapasitesini güçlendirmek.

## Nasıl çalışır?

| Adım | Ne yapar | Teknik | Prompt |
|---|---|---|---|
| 0 | Bina yaşı, çatlak, kat ve kırılgan birey için **kesin kurallı uyarılar** | Kod (LLM yok) | — |
| 1 | Kişisel plan: öncesi / anında / sonrası + kişiye özel | Rol + **RAG** (AFAD rehberi prompt'a eklenir) | `prompts/1_plan.md` |
| 2 | Afet çantası listesi | **Few-shot** (2 örnek) + **RAG** (AFAD rehberi prompt'a eklenir) | `prompts/2_canta.md` |
| 3 | Çocuğa / yaşlıya sade anlatım | **Zero-shot** | `prompts/3_sade_anlatim.md` |
| 4 | Çantada zorunlu eşya kontrolü ve eksik tamamlama | Kod (LLM yok) | — |

Model: Google Gemini 3.8 Flash. Temperature: plan ve çanta için 0.2 (tutarlılık), sade anlatım için 0.5.
Kaynak: `data/afad_rehber.txt` (her madde afad.gov.tr sayfalarına dayanır; kaynaklar dosyanın başında).

## Çalıştırma

```bash
pip install -r requirements.txt
cp .env.example .env        # içine GEMINI_API_KEY değerinizi yazın
streamlit run app.py
```

Ücretsiz API anahtarı: https://aistudio.google.com/apikey

## Dosyalar

- `app.py` — arayüz (Streamlit)
- `logic.py` — model çağrıları, kurallı uyarılar, çanta doğrulaması
- `prompts/` — tüm prompt'lar
- `data/afad_rehber.txt` — modele verilen güvenilir kaynak
- `tests/senaryolar.md` — test senaryoları ve sonuçlar
- `rapor.pdf` — proje raporu
