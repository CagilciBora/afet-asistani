"""Afet Hazırlık Asistanı — model çağrıları ve kodla yapılan güvenlik kontrolleri.
Arayüz app.py'de; burada sadece iş mantığı var."""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

MODEL = "gemini-2.5-flash"
ROOT = Path(__file__).parent


@dataclass
class Hane:
    yetiskin: int = 1
    bebek: int = 0          # 0-2 yaş
    cocuk: int = 0          # 3-12 yaş
    yasli: int = 0          # 65+
    hareket_kisitli: int = 0
    ilac: bool = False      # düzenli ilaç kullanan var mı (hangi ilaç / hastalık SORULMAZ)
    evcil: str = "yok"
    bina_yili: str = "Bilmiyorum"   # "2000 öncesi" | "2000-2018" | "2018 sonrası" | "Bilmiyorum"
    kat: str = "1-3. kat"           # "Zemin / bahçe katı" | "1-3. kat" | "4. kat ve üstü"
    catlak: bool = False            # binada gözle görülür çatlak / hasar
    ek_not: str = ""

    @property
    def toplam(self) -> int:
        return self.yetiskin + self.bebek + self.cocuk + self.yasli


def tr_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower().strip()


def oku(yol: str) -> str:
    return (ROOT / yol).read_text(encoding="utf-8")


# ---------------- Kodla belirlenen dikkat noktaları (deterministik) ----------------

def dikkat_noktalari(h: Hane) -> list[str]:
    """Kesin kurallarla verilen uyarılar. Bunları modele değil koda bıraktık."""
    d = []
    if h.bina_yili == "2000 öncesi":
        d.append("Bina 2000 öncesi yapılmış. Depreme dayanıklılığı için yetkili kurum/uzman incelemesi önerilir.")
    if h.bina_yili == "Bilmiyorum":
        d.append("Binanın yapım yılı bilinmiyor; tapu veya belediyeden öğrenilmesi önerilir.")
    if h.catlak:
        d.append("Binada çatlak/hasar gözlemlenmiş. Uzman incelemesi önceliklidir.")
    if h.kat == "4. kat ve üstü":
        d.append("Üst kat: deprem anında merdivene/balkona koşmayın, sarsıntı bitince merdivenle inin.")
    if h.bebek or h.yasli or h.hareket_kisitli:
        d.append("Hanede tahliyede yardıma ihtiyaç duyabilecek birey var; kimin kime yardım edeceği önceden belirlenmeli.")
    return d


# ---------------- Model çağrısı ----------------

def get_client():
    from google import genai
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY bulunamadı. .env dosyasına ekleyin.")
    return genai.Client(api_key=key)


def call_llm(client, system: str, user: str, temperature: float, as_json: bool = True):
    from google.genai import types
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        response_mime_type="application/json" if as_json else "text/plain",
    )
    r = client.models.generate_content(model=MODEL, contents=user, config=cfg)
    return json.loads(r.text) if as_json else r.text


def hane_metni(h: Hane) -> str:
    return (f"Hane: {h.yetiskin} yetişkin. Bebek: {h.bebek}, çocuk: {h.cocuk}, yaşlı: {h.yasli}, "
            f"hareket kısıtlı: {h.hareket_kisitli}. Düzenli ilaç: {'evet' if h.ilac else 'hayır'}. "
            f"Evcil hayvan: {h.evcil or 'yok'}. Bina yapım yılı: {h.bina_yili}. Kat: {h.kat}. "
            f"Binada çatlak/hasar: {'var' if h.catlak else 'yok'}.")


# ADIM 1 — Kişisel plan: rol + RAG (AFAD rehberi prompt'a eklenir)
def plan_uret(client, h: Hane) -> dict:
    user = (f"AFAD REHBERİ:\n{oku('data/afad_rehber.txt')}\n\n"
            f"HANE BİLGİSİ:\n{hane_metni(h)}\n\n"
            "DİKKAT NOKTALARI:\n" + "\n".join(f"- {x}" for x in dikkat_noktalari(h) or ["yok"]) + "\n\n"
            f"EK NOT (kullanıcıdan): {h.ek_not[:300] or 'yok'}")
    return call_llm(client, oku("prompts/1_plan.md"), user, temperature=0.2)


# ADIM 2 — Çanta listesi: few-shot
def canta_uret(client, h: Hane) -> dict:
    user = f"Girdi: {hane_metni(h)}\nÇıktı:"
    return call_llm(client, oku("prompts/2_canta.md"), user, temperature=0.2)


# ADIM 3 — Sade anlatım: zero-shot
def sade_anlat(client, plan: dict, kime: str) -> str:
    sonuc = {k: plan[k] for k in ("risk_ozeti", "oncesi", "aninda", "sonrasi", "kisiye_ozel") if k in plan}
    user = f"KİŞİ: {kime}\n\nPLAN:\n{json.dumps(sonuc, ensure_ascii=False)}"
    return call_llm(client, oku("prompts/3_sade_anlatim.md"), user, temperature=0.5, as_json=False)


# ---------------- Kodla doğrulama: çantada zorunlu eşyalar var mı? ----------------

# (gösterilecek ad, eşleşme kelimeleri)
TEMEL_ESYALAR = [
    ("içme suyu", ["su"]),
    ("dayanıklı gıda", ["konserve", "kuru meyve", "gıda", "pekmez", "bisküvi", "yiyecek"]),
    ("belge fotokopileri", ["fotokopi", "belge", "kimlik"]),
    ("ilk yardım çantası", ["ilk yardım"]),
    ("düdük", ["düdük"]),
    ("el feneri", ["fener"]),
    ("yedek pil", ["pil"]),
    ("pilli radyo", ["radyo"]),
    ("battaniye / uyku tulumu", ["battaniye", "uyku tulumu"]),
    ("hijyen malzemeleri", ["sabun", "ıslak mendil", "dezenfektan", "tuvalet"]),
]


def kosullu_esyalar(h: Hane) -> list[tuple[str, list[str]]]:
    k = []
    if h.bebek:
        k += [("bebek maması", ["mama"]), ("bebek bezi", ["bez"])]
    if h.ilac:
        k += [("düzenli ilaçlar ve reçete kopyası", ["ilaç"])]
    if h.yasli:
        k += [("yedek gözlük / yardımcı araçlar", ["gözlük", "baston", "işitme"])]
    if h.evcil and tr_lower(h.evcil) != "yok":
        k += [(f"{h.evcil} için mama ve su", ["mama"]), (f"{h.evcil} taşıma çantası / tasma", ["taşıma", "tasma"])]
    return k


def _esya_metni(canta: dict) -> str:
    return " | ".join(tr_lower(e.get("esya", "")) for k in canta.get("kategoriler", []) for e in k.get("esyalar", []))


def _var_mi(metin: str, kelimeler: list[str]) -> bool:
    for kw in kelimeler:
        kw = tr_lower(kw)
        if len(kw) <= 3:  # "su", "pil", "bez" gibi kısa kelimeler: tam kelime ya da yaygın ek ("suyu", "piller", "bezi")
            ekler = ["", "yu", "u", "ı", "i", "ü", "lar", "ler", "ları", "leri"]
            if any(tok in {kw + e for e in ekler} for tok in re.findall(r"\w+", metin)):
                return True
        elif kw in metin:
            return True
    return False


def eksikleri_tamamla(canta: dict, h: Hane) -> tuple[dict, list[str]]:
    """Modelin unuttuğu zorunlu eşyaları bulur ve 'Kontrolle eklenenler' kategorisine ekler."""
    metin = _esya_metni(canta)
    eksik = [ad for ad, kws in TEMEL_ESYALAR + kosullu_esyalar(h) if not _var_mi(metin, kws)]
    if eksik:
        canta.setdefault("kategoriler", []).append({
            "kategori": "Ek ihtiyaçlar",
            "esyalar": [{"esya": e, "miktar": "-", "kimin_icin": "-"} for e in eksik],
        })
    return canta, eksik


def kapsama_orani(canta_once: dict, h: Hane) -> tuple[int, int]:
    """Etki/kalite ölçütü: model zorunlu eşyaların kaçını kendisi listeledi?"""
    metin = _esya_metni(canta_once)
    gerekli = TEMEL_ESYALAR + kosullu_esyalar(h)
    return sum(_var_mi(metin, kws) for _, kws in gerekli), len(gerekli)


def markdown_cikti(h: Hane, plan: dict, canta: dict) -> str:
    """İndirilebilir / yazdırılabilir plan."""
    s = [f"# Hane Afet Hazırlık Planı\n\n{plan.get('risk_ozeti', '')}\n"]
    for baslik, anahtar in [("Deprem öncesi", "oncesi"), ("Deprem anında", "aninda"), ("Deprem sonrası", "sonrasi")]:
        s.append(f"## {baslik}\n" + "\n".join(f"- [ ] {m}" for m in plan.get(anahtar, [])))
    if plan.get("kisiye_ozel"):
        s.append("## Kişiye özel\n" + "\n".join(f"- **{k.get('kim')}**: {k.get('ne_yapilmali')}" for k in plan["kisiye_ozel"]))
    s.append("## Afet ve acil durum çantası")
    for k in canta.get("kategoriler", []):
        s.append(f"### {k.get('kategori')}\n" + "\n".join(f"- [ ] {e.get('esya')} ({e.get('miktar') or '-'})" for e in k.get("esyalar", [])))
    s.append("\n---\nAcil durum: 112. Bu plan yapay zekâ ile hazırlanmıştır; AFAD'ın resmî rehberiyle karşılaştırın.")
    return "\n\n".join(s)
