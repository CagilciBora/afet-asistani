# Değerlendirme sonuçları

`python tests/degerlendir.py` ile üretildi (1/10 senaryo). Ham çıktılar: `tests/ciktilar/`.

| # | Senaryo | Model | Kapsama (model) | Kodla eklenen eşyalar | Kişiye özel | CoT (dusunce) | Şüpheli ifade |
|---|---|---|---|---|---|---|---|
| 1 | 1 yetişkin | `gemini-3.5-flash` | 12/12 | — | ✅ (grup yok) | ✅ | — |

## Özet
- Ortalama zorunlu eşya kapsaması (kod kontrolünden önce): **%100**
- Kırılgan grupların hepsine kişiye özel madde verilen senaryo: **1/1**
- Şüpheli ifade işareti: **0** (her işareti `tests/ciktilar/` içinde elle kontrol edin; örn. "binanız sağlam mı bilinmez" gibi doğru bir cümle de işaretlenebilir)

Not: Kapsama, modelin kendi başına listelediği zorunlu eşya oranıdır; eksikler uygulamada kodla 'Ek ihtiyaçlar' bölümüne eklenir, yani kullanıcı her durumda tam listeyi görür.
