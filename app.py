"""Afet Hazırlık Asistanı — Streamlit arayüzü.  Çalıştırma: streamlit run app.py"""
import copy
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
from dotenv import load_dotenv

import logic

load_dotenv()
st.set_page_config(page_title="Afet Hazırlık Asistanı", page_icon="🧭", layout="centered")

st.title("🧭 Afet Hazırlık Asistanı")
st.caption("Hanenize özel deprem hazırlık planı ve afet çantası listesi.")

sade_alani = st.container()

# ---------------- Girdi formu ----------------
with st.form("hane"):
    st.subheader("Haneniz")
    c1, c2, c3 = st.columns(3)
    yetiskin = c1.number_input("Yetişkin (13-64)", 0, 10, 2)
    cocuk = c2.number_input("Çocuk (3-12)", 0, 10, 0)
    bebek = c3.number_input("Bebek (0-2)", 0, 5, 0)
    st.markdown("#### Yaşlı bireyler")
    yasli = st.number_input("65 yaş ve üzeri kişi sayısı", 0, 10, 0)
    hareket = st.number_input("Bunlardan hareket kısıtlı olan (yukarıdaki kişilere dahil)", 0, 10, 0)
    ilac = st.checkbox("Hanede düzenli ilaç kullanan biri var (hangi ilaç olduğunu yazmanıza gerek yok)")
    evcil = st.radio("Evcil hayvan var mı?", ["Evet", "Hayır"], index=1, horizontal=True)

    st.subheader("Binanız")
    c6, c7 = st.columns(2)
    bina_yili = c6.selectbox("Yapım yılı", ["2000 öncesi", "2000-2018", "2018 sonrası", "Bilmiyorum"])
    kat = c7.selectbox("Oturduğunuz kat", ["Zemin / bahçe katı", "1-3. kat", "4. kat ve üstü"])
    catlak = st.checkbox("Binada gözle görülür çatlak veya hasar var")
    ek_not = st.text_area("Eklemek istediğiniz bir şey (isteğe bağlı)", max_chars=300,
                          placeholder="ör. Evde tekerlekli sandalye kullanan biri var, merdiven dar. (Ad, adres, sağlık bilgisi yazmayın.)")
    gonder = st.form_submit_button("Planımı hazırla", type="primary")

if gonder:
    h = logic.Hane(yetiskin=yetiskin, bebek=bebek, cocuk=cocuk, yasli=yasli, hareket_kisitli=hareket,
                   ilac=ilac, evcil="evcil hayvan" if evcil == "Evet" else "yok",
                   bina_yili=bina_yili, kat=kat, catlak=catlak, ek_not=ek_not)
    if h.toplam == 0:
        st.warning("En az bir kişi girin.")
        st.stop()
    if h.hareket_kisitli > h.toplam:
        st.warning("Hareket kısıtlı kişi sayısı, hanedeki toplam kişi sayısından fazla olamaz.")
        st.stop()
    try:
        client = logic.get_client()
        # Plan ve çanta birbirinden bağımsız: iki model çağrısı paralel yapılır, bekleme süresi yarıya iner
        with st.spinner("Plan ve çanta listesi hazırlanıyor..."), ThreadPoolExecutor(max_workers=2) as havuz:
            plan_is = havuz.submit(logic.plan_uret, client, h)
            canta_is = havuz.submit(logic.canta_uret, client, h)
            plan, canta_ham = plan_is.result(), canta_is.result()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:  # noqa: BLE001
        st.error(logic.hata_mesaji(e))
        st.stop()

    canta, _ = logic.eksikleri_tamamla(copy.deepcopy(canta_ham), h)
    st.session_state.update(h=h, plan=plan, canta=canta, sade=None)

# ---------------- Sonuçlar ----------------
if "plan" in st.session_state:
    h, plan, canta = st.session_state.h, st.session_state.plan, st.session_state.canta

    with sade_alani:
        st.subheader("Sade anlatım")
        secenekler = ["genel"] + (["çocuk"] if h.cocuk else []) + (["yaşlı"] if h.yasli else [])
        kime = st.radio("Kime anlatılsın?", secenekler, horizontal=True)
        if st.button("Sade anlat"):
            try:
                with st.spinner("Hazırlanıyor..."):
                    st.session_state.sade = logic.sade_anlat(logic.get_client(), plan, kime)
            except Exception as e:  # noqa: BLE001
                st.error(logic.hata_mesaji(e))
        if st.session_state.get("sade"):
            st.success(st.session_state.sade)

    dikkat = logic.dikkat_noktalari(h)
    if dikkat:
        st.subheader("Dikkat noktaları")
        for d in dikkat:
            st.warning(d)
        st.caption("Bu uyarılar bir mühendislik değerlendirmesi değildir; binanızın güvenliği için uzmana başvurun.")

    st.subheader("Planınız")
    st.info(plan.get("risk_ozeti", ""))

    t1, t2, t3 = st.tabs(["Deprem öncesi", "Deprem anında", "Deprem sonrası"])
    for tab, anahtar in [(t1, "oncesi"), (t2, "aninda"), (t3, "sonrasi")]:
        tab.markdown("\n".join(f"- {m}" for m in plan.get(anahtar, [])))

    if plan.get("kisiye_ozel"):
        st.subheader("Kişiye özel")
        for k in plan["kisiye_ozel"]:
            st.markdown(f"- **{k.get('kim')}**: {k.get('ne_yapilmali')}")

    st.subheader("Afet ve acil durum çantası (72 saat)")
    for k in canta.get("kategoriler", []):
        with st.expander(k.get("kategori", ""), expanded=True):
            st.markdown("\n".join(f"- {e.get('esya')} — {e.get('miktar') or '-'} *({e.get('kimin_icin') or '-'})*"
                                  for e in k.get("esyalar", [])))

    st.download_button("📄 Planı indir (yazdırılabilir)", logic.markdown_cikti(h, plan, canta),
                       file_name="afet_plani.md", mime="text/markdown")

st.divider()
st.caption("Bu araç AFAD rehberine dayanarak yapay zekâ ile plan önerir; hatalı olabilir ve resmî kurumların yerini tutmaz. "
           "Acil durumda 112'yi arayın. Adres, kimlik ya da hastalık bilgisi istenmez. Bilgileriniz bu uygulamada "
           "saklanmaz; plan oluşturmak için Google Gemini'ye gönderilir. Ek not alanına ad, adres veya sağlık bilgisi yazmayın.")
