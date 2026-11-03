"""Tableau des chants : CSV pour Excel français (UTF-8 avec BOM, « ; », virgule décimale) et page HTML imprimable.

Pur Python. Les textes passent par t (Textes).
"""
from __future__ import annotations

import html

from .chants import PieceLue, chant_par_cote, debit, totaux

BOM = "﻿"


def _cellule(x) -> str:
    s = str(x)
    if any(c in s for c in ';"\n\r'):
        s = '"' + s.replace('"', '""') + '"'
    return s


def _ligne(valeurs) -> str:
    return ";".join(_cellule(v) for v in valeurs)


def _nb(x: float, decimales: int = 1) -> str:
    """Nombre pour Excel français : virgule décimale, toujours (indépendant de la langue de Fusion)."""
    return f"{x:.{decimales}f}".replace(".", ",")


def _ref(ch) -> str:
    return ch.reference if ch else ""


def ecrire_csv(pieces: list[PieceLue], marge: float, avec_debit: bool, t, disparus: list | None = None) -> str:
    """Texte complet du CSV, BOM compris : à écrire tel quel (encoding="utf-8", newline="")."""
    lignes = [_ligne([t("tableau.titre_totaux")]),
              _ligne([t("col.reference"), t("col.ep_chant"), t("col.nombre"), t("col.nette"), t("col.marge", m=_nb(marge, 0))])]
    for tot in totaux(pieces, marge):
        lignes.append(_ligne([tot.reference, _nb(tot.epaisseur), tot.nombre, _nb(tot.longueur_nette / 1000, 2),
                              _nb(tot.longueur_avec_marge / 1000, 2)]))
    lignes.append("")
    lignes.append(_ligne([t("tableau.titre_pieces")]))
    entete = [t("col.piece"), t("col.quantite"), t("col.longueur"), t("col.largeur"), t("col.epaisseur")]
    if avec_debit:
        entete += [t("col.longueur_debit"), t("col.largeur_debit")]
    entete += [t("col.long1"), t("col.long2"), t("col.court1"), t("col.court2"), t("col.autres")]
    lignes.append(_ligne(entete))
    for p in pieces:
        cotes = chant_par_cote(p)
        v = [p.nom, p.quantite, _nb(p.longueur), _nb(p.largeur), _nb(p.epaisseur)]
        if avec_debit:
            dl, dw = debit(p)
            v += [_nb(dl), _nb(dw)]
        v += [_ref(cotes["+v"]), _ref(cotes["-v"]), _ref(cotes["+u"]), _ref(cotes["-u"]),
              " / ".join(f"{c.reference} {_nb(c.longueur, 0)} mm" for c in cotes["autres"])]
        lignes.append(_ligne(v))
    if disparus:
        lignes.append("")
        lignes.append(_ligne([t("tableau.disparus", n=len(disparus))]))
        for d in disparus:
            lignes.append(_ligne([d.get("piece", ""), d.get("reference", ""), _nb(d.get("longueur", 0.0), 0)]))
    return BOM + "\r\n".join(lignes) + "\r\n"


# --- page HTML --------------------------------------------------------------------------------------------------

def svg_piece(p: PieceLue, taille: int = 120) -> str:
    """Petit schéma de la pièce vue de face : rectangle à l'échelle, côtés plaqués épais à la couleur du chant."""
    cotes = chant_par_cote(p)
    m = 8
    L, W = max(p.longueur, 1e-6), max(p.largeur, 1e-6)
    k = (taille - 2 * m) / max(L, W)
    w, h = L * k, max(W * k, 4)
    x0, y0 = m, m
    s = [f'<svg class="schema" viewBox="0 0 {taille} {h + 2 * m:.1f}" width="{taille}" height="{h + 2 * m:.1f}">',
         f'<rect x="{x0}" y="{y0}" width="{w:.1f}" height="{h:.1f}" class="panneau"/>']
    segments = {"+v": (x0, y0, x0 + w, y0), "-v": (x0, y0 + h, x0 + w, y0 + h),
                "-u": (x0, y0, x0, y0 + h), "+u": (x0 + w, y0, x0 + w, y0 + h)}
    for c, (xa, ya, xb, yb) in segments.items():
        ch = cotes[c]
        if ch:
            s.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{html.escape(ch.couleur)}" '
                     f'stroke-width="5" stroke-linecap="round"><title>{html.escape(ch.reference)}</title></line>')
    s.append("</svg>")
    return "".join(s)


def _f(t, x, d=1):
    return t.nombre(x, d)


def ecrire_html(pieces: list[PieceLue], marge: float, avec_debit: bool, t, document: str,
                disparus: list | None = None) -> str:
    e = html.escape
    tot = totaux(pieces, marge)
    lignes_tot = "".join(
        f'<tr><td><span class="pastille" style="background:{e(x.couleur)}"></span>{e(x.reference)}</td>'
        f'<td class="n">{_f(t, x.epaisseur)}</td><td class="n">{x.nombre}</td>'
        f'<td class="n">{_f(t, x.longueur_nette / 1000, 2)}</td><td class="n"><b>{_f(t, x.longueur_avec_marge / 1000, 2)}</b></td></tr>'
        for x in tot)
    cartes = []
    for p in pieces:
        cotes = chant_par_cote(p)
        lst = []
        for c, cle in (("+v", "col.long1"), ("-v", "col.long2"), ("+u", "col.court1"), ("-u", "col.court2")):
            if cotes[c]:
                lst.append(f"<li>{e(t(cle))} : {e(cotes[c].reference)} · {_f(t, cotes[c].longueur, 0)} mm</li>")
        for ch in cotes["autres"]:
            lst.append(f"<li>{e(t('col.autres'))} : {e(ch.reference)} · {_f(t, ch.longueur, 0)} mm</li>")
        dims = f"{_f(t, p.longueur)} × {_f(t, p.largeur)} × {_f(t, p.epaisseur)} mm"
        deb = ""
        if avec_debit:
            dl, dw = debit(p)
            deb = f'<div class="debit">{e(t("tableau.debit"))} : <b>{_f(t, dl)} × {_f(t, dw)} mm</b></div>'
        qte = f' <span class="qte">× {p.quantite}</span>' if p.quantite > 1 else ""
        cartes.append(f'<div class="carte">{svg_piece(p)}<div><h3>{e(p.nom)}{qte}</h3><div>{dims}</div>{deb}'
                      f'<ul>{"".join(lst)}</ul></div></div>')
    alerte = ""
    if disparus:
        items = "".join(f"<li>{e(d.get('piece', ''))} · {e(d.get('reference', ''))} · {_f(t, d.get('longueur', 0.0), 0)} mm</li>"
                        for d in disparus)
        alerte = f'<div class="alerte"><b>⚠ {e(t("tableau.disparus", n=len(disparus)))}</b><ul>{items}</ul></div>'
    titre = t("tableau.titre_page", doc=document)
    return f"""<!doctype html>
<html lang="{e(t.langue)}"><head><meta charset="utf-8"><title>{e(titre)}</title>
<style>
body{{font:13px "Artifakt Element","Segoe UI",Arial,sans-serif;color:#222;margin:24px;background:#fff}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:15px;margin:24px 0 8px}} h3{{font-size:13px;margin:0 0 4px}}
table{{border-collapse:collapse}} th,td{{border:1px solid #ccc;padding:4px 8px;text-align:left}} td.n{{text-align:right}}
th{{background:#f3f3f3}} .pastille{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:middle}}
.cartes{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}}
.carte{{display:flex;gap:10px;border:1px solid #ddd;border-radius:4px;padding:8px;break-inside:avoid}}
.carte ul{{margin:4px 0 0;padding-left:16px}} .panneau{{fill:#eee;stroke:#888;stroke-width:1}}
.qte{{color:#178FE6}} .debit{{margin-top:2px}} .note{{color:#666}}
.alerte{{border:1px solid #D62828;background:#fdecec;padding:8px;border-radius:4px;margin:12px 0}}
@media print{{body{{margin:10mm}} .carte{{page-break-inside:avoid}}}}
</style></head><body>
<h1>{e(titre)}</h1>
<div class="note">{e(t("tableau.note_marge", m=_f(t, marge, 0)))}</div>
{alerte}
<h2>{e(t("tableau.titre_totaux"))}</h2>
<table><tr><th>{e(t("col.reference"))}</th><th>{e(t("col.ep_chant"))}</th><th>{e(t("col.nombre"))}</th>
<th>{e(t("col.nette"))}</th><th>{e(t("col.marge", m=_f(t, marge, 0)))}</th></tr>{lignes_tot}</table>
<h2>{e(t("tableau.titre_pieces"))}</h2>
<div class="cartes">{"".join(cartes) or e(t("tableau.aucun"))}</div>
</body></html>
"""
