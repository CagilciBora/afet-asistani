"""Arayüz akışlarını gerçek model çağrısı yapmadan doğrular."""
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import logic


class ArayuzTesti(unittest.TestCase):
    def test_plan_ve_sade_anlatim(self):
        plan = {"risk_ozeti": "Hazırlık özeti", "oncesi": ["Çantanı hazırla"],
                "aninda": ["Çök, kapan, tutun"], "sonrasi": ["Toplanma alanına git"],
                "dusunce": "GİZLİ ANALİZ", "kisiye_ozel": []}
        for secim in ("Evet", "Hayır"):
            with self.subTest(evcil=secim), \
                    patch.object(logic, "get_client", return_value=object()), \
                    patch.object(logic, "plan_uret", return_value=plan), \
                    patch.object(logic, "canta_uret", return_value={"kategoriler": []}), \
                    patch.object(logic, "sade_anlat", return_value="Sade sonuç") as sade:
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
                self.assertFalse(app.exception)
                app.radio[0].set_value(secim)
                app.number_input[1].set_value(1)
                app.number_input[3].set_value(2)
                app.button[0].click().run()
                self.assertFalse(app.exception)
                h = app.session_state.h
                self.assertEqual(h.evcil, "evcil hayvan" if secim == "Evet" else "yok")
                self.assertEqual(h.yasli, 2)
                esyalar = str(app.session_state.canta)
                self.assertIn("içme suyu", esyalar)
                self.assertEqual("evcil hayvan için mama ve su" in esyalar, secim == "Evet")
                self.assertFalse(app.metric)
                self.assertFalse(app.error)
                gorunen_metin = " ".join(str(e.value) for tur in ("markdown", "text", "info", "caption")
                                         for e in app.get(tur))
                self.assertNotIn("GİZLİ ANALİZ", gorunen_metin)
                self.assertFalse(any("düşünme" in e.label for e in app.expander))
                self.assertEqual(app.subheader[0].value, "Sade anlatım")
                self.assertEqual(app.radio[0].options, ["genel", "çocuk", "yaşlı"])
                app.radio[0].set_value("yaşlı")
                app.button[0].click().run()
                self.assertFalse(app.exception)
                self.assertEqual(sade.call_args.args[2], "yaşlı")
                self.assertEqual(app.success[0].value, "Sade sonuç")
                self.assertIn("Çantanı hazırla", logic.markdown_cikti(h, plan, app.session_state.canta))

    def test_sade_anlatima_yalnizca_sonuc_gider(self):
        with patch.object(logic, "call_llm", return_value="Sonuç") as model:
            logic.sade_anlat(object(), {"risk_ozeti": "Özet", "dusunce": "GİZLİ ANALİZ"}, "genel")
            self.assertNotIn("GİZLİ ANALİZ", model.call_args.args[2])
            self.assertIn("Özet", model.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
