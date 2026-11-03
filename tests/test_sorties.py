"""CSV (Excel français), page HTML, réglages et bibliothèque, traductions."""
import json
import re
from pathlib import Path

from edgebanding import export, reglages
from edgebanding.chants import ChantLu, PieceLue
from edgebanding.textes import Textes

LANGUES = Path(__file__).resolve().parents[1] / "EdgeBanding" / "ressources" / "langues"


def _pieces():
    return [PieceLue("Côté; gauche", 2, 720, 560, 19, [
        ChantLu("a", "ABS 2 mm blanc", 2, "#FF7A00", 720, "+v"),
        ChantLu("b", "Placage \"chêne\"", 0.6, "#2EAD4B", 157.1, None)])]


def test_csv_excel_francais():
    t = Textes(LANGUES, "fr")
    s = export.ecrire_csv(_pieces(), 40, True, t, [{"piece": "Fond", "reference": "ABS", "longueur": 500}])
    assert s.startswith("﻿") and "\r\n" in s
    lignes = s.lstrip("﻿").split("\r\n")
    assert lignes[0] == "Totaux par référence"
    assert lignes[1].split(";")[0] == "Référence" and len(lignes[1].split(";")) == 5
    assert "ABS 2 mm blanc;2,0;2;1,44;1,52" in s           # 2 × 720 mm, + 2 × 40 mm de marge
    assert '"Placage ""chêne""";0,6;2;0,31;0,39' in s
    assert '"Côté; gauche";2;720,0;560,0;19,0;720,0;558,0;ABS 2 mm blanc;;;;' in s
    assert "1 chants plaqués ont disparu" in s


def test_csv_sans_debit_moins_de_colonnes():
    t = Textes(LANGUES, "en")
    s = export.ecrire_csv(_pieces(), 0, False, t)
    entete = next(li for li in s.split("\r\n") if li.startswith("Part;"))
    assert len(entete.split(";")) == 10 and "Cut length" not in s


def test_page_html():
    t = Textes(LANGUES, "fr")
    h = export.ecrire_html(_pieces(), 40, True, t, "Cuisine <test>", [])
    assert "<title>Tableau des chants – Cuisine &lt;test&gt;</title>" in h
    assert h.count("<svg") == 1 and 'stroke="#FF7A00"' in h
    assert "× 2" in h and "Débit" in h and "720,0 × 558,0 mm" in h
    vide = export.ecrire_html([], 40, False, t, "Vide", [])
    assert "Aucun chant plaqué" in vide


def test_schema_piece_cotes():
    p = PieceLue("x", 1, 600, 300, 19, [ChantLu(str(i), "A", 1, "#123456", 1, c) for i, c in
                                        enumerate(("+u", "-u", "+v", "-v"))])
    assert export.svg_piece(p).count("<line") == 4


def test_reglages_defauts_et_relecture(tmp_path):
    t = Textes(LANGUES, "fr")
    f = tmp_path / "r.json"
    r = reglages.lire(f, t)
    assert r["bibliotheque"][0]["nom"] == "ABS 2 mm blanc" and r["marge"] == 40 and r["mode"] == "couleur"
    r["bibliotheque"].append({"cle": "x", "nom": "Mon chant", "epaisseur": 1.5, "couleur": "bleu"})
    r.update(reference="x", mode="aucune", marge=25.0, debit=True)
    reglages.ecrire(f, r)
    lu = reglages.lire(f, t)
    assert lu["reference"] == "x" and lu["mode"] == "aucune" and lu["marge"] == 25 and lu["debit"] is True
    assert lu["bibliotheque"][-1]["nom"] == "Mon chant"
    f.write_text("pas du json", encoding="utf-8")
    assert reglages.lire(f, t)["reference"] == "abs2-blanc"
    f.write_text(json.dumps({"bibliotheque": [{"cle": "a", "nom": "", "epaisseur": 1, "couleur": "bleu"}],
                             "reference": "zz", "mode": "rose", "marge": -3}), encoding="utf-8")
    lu = reglages.lire(f, t)
    assert len(lu["bibliotheque"]) == 5 and lu["reference"] == "abs2-blanc" and lu["mode"] == "couleur"
    assert lu["marge"] == 40


def test_nouvelle_cle_et_couleurs():
    b = [{"cle": "abs-2"}, {"cle": "abs-2-2"}]
    assert reglages.nouvelle_cle(b, "ABS 2") == "abs-2-3"
    assert reglages.nouvelle_cle(b, "Chêne!") == "ch-ne"
    assert reglages.rvb("#FF7A00") == (255, 122, 0) and reglages.rvb("zz") == (255, 122, 0)
    assert reglages.hexa("inconnue") == reglages.COULEURS["orange"]


def test_toutes_les_cles_dans_les_quatre_langues_avec_les_memes_variables():
    tables = {c: json.loads((LANGUES / f"{c}.json").read_text(encoding="utf-8")) for c in ("en", "fr", "ja", "de")}
    for c, tab in tables.items():
        assert tab.keys() == tables["en"].keys(), c
        for k, v in tab.items():
            assert v.strip(), (c, k)
            assert set(re.findall(r"{(\w+)}", v)) == set(re.findall(r"{(\w+)}", tables["en"][k])), (c, k)


def test_cles_du_code_presentes():
    en = json.loads((LANGUES / "en.json").read_text(encoding="utf-8"))
    code = "".join(p.read_text(encoding="utf-8") for p in (LANGUES.parents[1] / "edgebanding").glob("*.py"))
    cles = set(re.findall(r'(?:\bt|ctx\.t)\("([a-z_]+\.[a-z_0-9.]+)"', code))
    cles |= set(re.findall(r'ErreurChants\("([a-z_]+\.[a-z_0-9]+)"', code))
    assert cles and not (cles - en.keys()), cles - en.keys()
    for prefixe, noms in (("couleur", reglages.COULEURS), ("mode", reglages.MODES)):
        assert all(f"{prefixe}.{n}" in en for n in noms)
    for c in ("pinceau", "tableau", "surbrillance", "retirer"):
        assert f"{c}.nom" in en and f"{c}.infobulle" in en
    assert all(k in en for _, k, _, _ in reglages.REFERENCES_DEFAUT)


def test_langue_de_secours(tmp_path):
    (tmp_path / "en.json").write_text('{"a": "A {x}"}', encoding="utf-8")
    t = Textes(tmp_path, "ja")
    assert t("a", x=1) == "A 1" and t("inconnue") == "inconnue" and t.nombre(1.234, 2) == "1.23"
