"""Afet Hazırlık Asistanı — Streamlit arayüzü.  Çalıştırma: streamlit run app.py"""
import copy

import streamlit as st
from dotenv import load_dotenv

import logic

load_dotenv()
st.set_page_config(page_title="Afet Hazırlık Asistanı", page_icon="🧭", layout="centered")

st.title("🧭 Afet Hazırlık Asistanı")
st.caption("Hanenize özel deprem hazırlık planı ve afet çantası listesi. "
           "SDG 11.5 ve 13.1: Afetlerde can kaybını azaltmak, dayanıklılığı artırmak.")

# ---------------- Girdi formu ----------------
with st.form("hane"):
    st.subheader("Haneniz")
    c1, c2, c3 = st.columns(3)
    yetiskin = c1.number_input("Yetişkin (13-64)", 0, 10, 2)
    cocuk = c2.number_input("Çocuk (3-12)", 0, 10, 0)
    bebek = c3.number_input("Bebek (0-2)", 0, 5, 0)
    c4, c5 = st.columns(2)
    yasli = c4.number_input("Yaşlı (65+)", 0, 10, 0)
    hareket = c5.number_input("Hareket kısıtlı birey", 0, 10, 0)
    ilac = st.checkbox("Hanede düzenli ilaç kullanan biri var (hangi ilaç olduğunu yazmanıza gerek yok)")
    evcil = st.text_input("Evcil hayvan (yoksa boş bırakın)", placeholder="ör. kedi")

    st.subheader("Binanız")
    c6, c7 = st.columns(2)
    bina_yili = c6.selectbox("Yapım yılı", ["2000 öncesi", "2000-2018", "2018 sonrası", "Bilmiyorum"])
    kat = c7.selectbox("Oturduğunuz kat", ["Zemin / bahçe katı", "1-3. kat", "4. kat ve üstü"])
    catlak = st.checkbox("Binada gözle görülür çatlak veya hasar var")
    ek_not = st.text_area("Eklemek istediğiniz bir şey (isteğe bağlı)", max_chars=300,
                          placeholder="ör. Evde tekerlekli sandalye kullanan biri var, merdiven dar.")
    gonder = st.form_submit_button("Planımı hazırla", type="primary")

if gonder:
    h = logic.Hane(yetiskin=yetiskin, bebek=bebek, cocuk=cocuk, yasli=yasli, hareket_kisitli=hareket,
                   ilac=ilac, evcil=evcil.strip() or "yok", bina_yili=bina_yili, kat=kat, catlak=catlak, ek_not=ek_not)
    if h.toplam == 0:
        st.warning("En az bir kişi girin.")
        st.stop()
    try:
        client = logic.get_client()
        with st.spinner("Plan hazırlanıyor..."):
            plan = logic.plan_uret(client, h)
        with st.spinner("Çanta listesi hazırlanıyor..."):
            canta_ham = logic.canta_uret(client, h)
    except RuntimeError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:  # noqa: BLE001
        st.error(f"Model cevabı alınamadı, tekrar deneyin. ({e})")
        st.stop()

    kapsanan, gerekli = logic.kapsama_orani(canta_ham, h)
    canta, eksikler = logic.eksikleri_tamamla(copy.deepcopy(canta_ham), h)
    st.session_state.update(h=h, plan=plan, canta=canta, eksikler=eksikler, kapsama=(kapsanan, gerekli), sade=None)

# ---------------- Sonuçlar ----------------
if "plan" in st.session_state:
    h, plan, canta = st.session_state.h, st.session_state.plan, st.session_state.canta

    dikkat = logic.dikkat_noktalari(h)
    if dikkat:
        st.subheader("Dikkat noktaları")
        for d in dikkat:
            st.warning(d)
        st.caption("Bu uyarılar bir mühendislik değerlendirmesi değildir; binanızın güvenliği için uzmana başvurun.")

    st.subheader("Planınız")
    st.info(plan.get("risk_ozeti", ""))
    with st.expander("Asistanın düşünme adımları (chain-of-thought)"):
        st.write(plan.get("dusunce", "—"))

    t1, t2, t3 = st.tabs(["Deprem öncesi", "Deprem anında", "Deprem sonrası"])
    for tab, anahtar in [(t1, "oncesi"), (t2, "aninda"), (t3, "sonrasi")]:
        tab.markdown("\n".join(f"- {m}" for m in plan.get(anahtar, [])))

    if plan.get("kisiye_ozel"):
        st.subheader("Kişiye özel")
        for k in plan["kisiye_ozel"]:
            st.markdown(f"- **{k.get('kim')}**: {k.get('ne_yapilmali')}")

    st.subheader("Afet ve acil durum çantası (72 saat)")
    kapsanan, gerekli = st.session_state.kapsama
    st.metric("Zorunlu eşya kapsaması (model)", f"{kapsanan} / {gerekli}")
    if st.session_state.eksikler:
        st.error("Model şu zorunlu eşyaları atladı; kontrol sistemi ekledi: " + ", ".join(st.session_state.eksikler))
    for k in canta.get("kategoriler", []):
        with st.expander(k.get("kategori", ""), expanded=True):
            st.markdown("\n".join(f"- {e.get('esya')} — {e.get('miktar') or '-'} *({e.get('kimin_icin') or '-'})*"
                                  for e in k.get("esyalar", [])))

    st.subheader("Sade anlatım")
    secenekler = ["genel"] + (["çocuk"] if h.cocuk else []) + (["yaşlı"] if h.yasli else [])
    kime = st.radio("Kime anlatılsın?", secenekler, horizontal=True)
    if st.button("Sade anlat"):
        with st.spinner("Hazırlanıyor..."):
            st.session_state.sade = logic.sade_anlat(logic.get_client(), plan, kime)
    if st.session_state.get("sade"):
        st.success(st.session_state.sade)

    st.download_button("📄 Planı indir (yazdırılabilir)", logic.markdown_cikti(h, plan, canta),
                       file_name="afet_plani.md", mime="text/markdown")

st.divider()
st.caption("Bu araç AFAD rehberine dayanarak yapay zekâ ile plan önerir; hatalı olabilir ve resmî kurumların yerini tutmaz. "
           "Acil durumda 112'yi arayın. Adres, kimlik ya da hastalık bilgisi istenmez; girdiğiniz bilgiler kaydedilmez.")
