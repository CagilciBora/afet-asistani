"""Kodla yapılan çanta kontrolünün birim testleri (model çağrısı yok)."""
import os
import unittest
from unittest.mock import patch

import logic


def canta(*esyalar):
    return {"kategoriler": [{"kategori": "Test", "esyalar": [{"esya": e} for e in esyalar]}]}


class CantaKontrolu(unittest.TestCase):
    def test_bebek_mamasi_evcil_hayvan_mamasi_sayilmaz(self):
        h = logic.Hane(yetiskin=2, bebek=1, evcil="evcil hayvan")
        _, eksik = logic.eksikleri_tamamla(canta("bebek maması"), h)
        self.assertIn("evcil hayvan için mama ve su", eksik)
        self.assertNotIn("bebek maması", eksik)

    def test_kedi_mamasi_bebek_mamasi_sayilmaz(self):
        h = logic.Hane(yetiskin=2, bebek=1, evcil="evcil hayvan")
        _, eksik = logic.eksikleri_tamamla(canta("kedi maması"), h)
        self.assertIn("bebek maması", eksik)
        self.assertNotIn("evcil hayvan için mama ve su", eksik)

    def test_hareket_kisitli_yas_gruplarina_dahil(self):
        h = logic.Hane(yetiskin=0, yasli=1, hareket_kisitli=1)
        self.assertEqual(h.toplam, 1)
        self.assertIn("bunlardan hareket kısıtlı: 1", logic.hane_metni(h))


class SahteModel:
    """Sırayla verilen hataları fırlatan, sonra cevap dönen sahte Gemini istemcisi."""

    def __init__(self, *hatalar):
        self.hatalar, self.cagrilar = list(hatalar), []
        self.models = self

    def generate_content(self, model, contents, config):
        self.cagrilar.append(model)
        if self.hatalar:
            hata = self.hatalar.pop(0)
            if hata == "BOZUK_JSON":
                return type("Cevap", (), {"text": '{"ok": true'})()
            raise RuntimeError(hata)
        return type("Cevap", (), {"text": '{"ok": true}'})()


@patch.object(logic.time, "sleep")
@patch.dict(os.environ, {"GEMINI_MODEL": "ana", "GEMINI_YEDEK_MODEL": "yedek"})
class ModelCagrisi(unittest.TestCase):
    def test_503_tekrar_denenir(self, _):
        client = SahteModel("503 UNAVAILABLE")
        self.assertEqual(logic.call_llm(client, "s", "u", 0), {"ok": True})
        self.assertEqual(client.cagrilar, ["ana", "ana"])

    def test_yogunluk_surerse_yedek_modele_gecilir(self, _):
        client = SahteModel(*["503 UNAVAILABLE"] * 3)
        self.assertEqual(logic.call_llm(client, "s", "u", 0), {"ok": True})
        self.assertEqual(client.cagrilar, ["ana"] * 3 + ["yedek"])

    def test_gunluk_kota_dolunca_beklemeden_yedege_gecilir(self, _):
        client = SahteModel("429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier")
        logic.call_llm(client, "s", "u", 0)
        self.assertEqual(client.cagrilar, ["ana", "yedek"])

    def test_zaman_asiminda_beklemeden_yedege_gecilir(self, _):
        client = SahteModel("504 DEADLINE_EXCEEDED")
        logic.call_llm(client, "s", "u", 0)
        self.assertEqual(client.cagrilar, ["ana", "yedek"])

    def test_yedek_bos_ise_kapali(self, _):
        client = SahteModel(*["503 UNAVAILABLE"] * 3)
        with patch.dict(os.environ, {"GEMINI_YEDEK_MODEL": ""}), self.assertRaises(RuntimeError):
            logic.call_llm(client, "s", "u", 0)
        self.assertEqual(client.cagrilar, ["ana"] * 3)

    def test_bozuk_json_tekrar_denenir(self, _):
        client = SahteModel("BOZUK_JSON")
        self.assertEqual(logic.call_llm(client, "s", "u", 0), {"ok": True})
        self.assertEqual(client.cagrilar, ["ana", "ana"])

    def test_kalici_hata_tekrar_denenmez(self, _):
        client = SahteModel("400 API key not valid")
        with self.assertRaises(RuntimeError):
            logic.call_llm(client, "s", "u", 0)
        self.assertEqual(client.cagrilar, ["ana"])


if __name__ == "__main__":
    unittest.main()
