"""Icônes de l'add-in Edge Banding (Chants plaqués).

Style : design system « Icônes Fusion natives » (cavalière, gris = existant, bleu = ce que fait la commande,
aplats, contour de 1 px en clair seulement, ni texte ni lettre). Palette et classe Dessin reprises de
`design-system/idees/generer_icones.py` du dépôt fusion360-ecosystem-plugin (icône « chants » de l'étude).

Écrit docs/icones/svg/<dossier>/{16x16,32x32}{,-dark}.svg, puis `node docs/icones/rendre_png.js` rend les PNG dans
EdgeBanding/ressources/<dossier>/ : 16x16, 16x16@2x, 32x32, 32x32@2x, en clair, -dark, -dark_blue, -dark_gray
(-dark_blue et -dark_gray = copies de -dark : règle provisoire du skill).

Usage (depuis la racine du dépôt) : python docs/icones/generer_icones.py && node docs/icones/rendre_png.js
"""
from pathlib import Path

SORTIE = Path(__file__).parent / "svg"

THEMES = {
    "clair": {
        "g1": "#F3F3F3", "g2": "#D9D9D9", "g3": "#BBBBBB", "g4": "#808080",
        "contour": "#666666", "relief": "#000000", "relief_op": "0.2",
        "bd": "#89CBFA", "bc": "#67B1E6", "bo": "#4795CC", "action": "#178FE6",
        "vert": "#24B353", "encre": "#333333",
    },
    "sombre": {
        "g1": "#F3F3F3", "g2": "#D9D9D9", "g3": "#BBBBBB", "g4": "#999999",
        "contour": None, "relief": None, "relief_op": "0",
        "bd": "#B2DFFF", "bc": "#89CBFA", "bo": "#67B1E6", "action": "#73C5FF",
        "vert": "#62D987", "encre": "#FFFFFF",
    },
}


class Dessin:
    def __init__(self, theme, petit):
        self.t = THEMES[theme]
        self.petit = petit
        self.cw = 2 if petit else 1  # épaisseur du contour en unités de la grille de 32
        self.els = []
        self.defs = []
        self.n = 0

    # --- primitives -------------------------------------------------------
    @staticmethod
    def pts(p):
        return " ".join(f"{x:g},{y:g}" for x, y in p)

    def poly(self, p, couleur, extra=""):
        self.els.append(f'<polygon points="{self.pts(p)}" fill="{couleur}"{extra}/>')

    def path(self, d, couleur, extra=""):
        self.els.append(f'<path d="{d}" fill="{couleur}"{extra}/>')

    def trait(self, d, couleur, largeur):
        self.els.append(
            f'<path d="{d}" fill="none" stroke="{couleur}" stroke-width="{largeur}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')

    def anneau(self, forme_d, corps_gris=True):
        """Contour de cw unités à l'intérieur de la silhouette (trait double rogné à la forme)."""
        if corps_gris:
            couleur, op = self.t["contour"], "1"
        else:
            couleur, op = self.t["relief"], self.t["relief_op"]
        if not couleur:
            return
        self.n += 1
        cid = f"c{self.n}"
        self.defs.append(f'<clipPath id="{cid}"><path d="{forme_d}"/></clipPath>')
        self.els.append(
            f'<path d="{forme_d}" fill="none" stroke="{couleur}" stroke-opacity="{op}" '
            f'stroke-width="{2 * self.cw}" clip-path="url(#{cid})"/>')

    @staticmethod
    def d_poly(p):
        return "M" + " L".join(f"{x:g},{y:g}" for x, y in p) + " Z"

    def bloc(self, x, y, w, h, d, bleu=False):
        """Bloc en cavalière : face avant (x, y, w, h), profondeur d à 45° vers le haut-droite."""
        t = self.t
        dessus, avant, cote = (t["bd"], t["bc"], t["bo"]) if bleu else (t["g1"], t["g2"], t["g3"])
        self.poly([(x, y), (x + d, y - d), (x + w + d, y - d), (x + w, y)], dessus)
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], avant)
        self.poly([(x + w, y), (x + w + d, y - d), (x + w + d, y + h - d), (x + w, y + h)], cote)
        sil = [(x, y), (x + d, y - d), (x + w + d, y - d), (x + w + d, y + h - d), (x + w, y + h), (x, y + h)]
        return sil

    def svg(self):
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
                + defs + "".join(self.els) + "</svg>\n")


# --- les icônes -------------------------------------------------------------------------------------------------

def bande_avant(D, couleur):
    """Panneau couché gris, chant avant (bande) d'une couleur donnée ; rend la bande."""
    sil = D.bloc(1, 19, 20, 6, 10)
    D.anneau(D.d_poly(sil))
    bande = [(1, 19), (21, 19), (21, 25), (1, 25)]
    D.poly(bande, couleur)
    D.anneau(D.d_poly(bande), corps_gris=(couleur == D.t["g2"]))
    return bande


def pinceau(D):
    """Commande principale : le chant avant du panneau est plaqué (bleu). Icône « chants » de l'étude."""
    bande_avant(D, D.t["bc"])


def tableau(D):
    """Feuille (grise) avec des lignes : pastille bleue + trait gris, une ligne par référence de chant."""
    t = D.t
    feuille = [(4, 2), (28, 2), (28, 30), (4, 30)]
    D.poly(feuille, t["g1"])
    D.anneau(D.d_poly(feuille))
    lignes = (8, 15, 22) if D.petit else (7, 12.5, 18, 23.5)
    cote = 4 if D.petit else 3
    for y in lignes:
        D.poly([(8, y), (8 + cote, y), (8 + cote, y + cote), (8, y + cote)], t["bc"])
        D.trait(f"M{14 if D.petit else 13},{y + cote / 2} L24,{y + cote / 2}", t["g4"], 2.5 if D.petit else 1.75)


def surbrillance(D):
    """Panneau gris, chant avant cerné d'un trait bleu action : on le montre sans le modifier."""
    t = D.t
    sil = D.bloc(1, 19, 20, 6, 10)
    D.anneau(D.d_poly(sil))
    bande = [(1, 19), (21, 19), (21, 25), (1, 25)]
    D.poly(bande, t["bd"])
    w = 2.5 if D.petit else 2
    D.trait(D.d_poly([(2, 20), (20, 20), (20, 24), (2, 24)]), t["action"], w)
    for (x1, y1, x2, y2) in ((6, 15, 4, 12), (11, 14, 11, 10), (16, 15, 18, 12)) if not D.petit else ((6, 15, 4, 11), (14, 15, 16, 11)):
        D.trait(f"M{x1},{y1} L{x2},{y2}", t["action"], w)


def retirer(D):
    """Panneau gris au chant gris (couleur retirée) et gomme bleue posée dessus."""
    t = D.t
    bande_avant(D, t["g2"])
    # gomme en cavalière, inclinée, posée sur le chant
    D.poly([(12, 18), (20, 10), (27, 10), (19, 18)], t["bd"])        # dessus
    D.poly([(19, 18), (27, 10), (27, 14), (19, 22)], t["bo"])        # flanc
    D.poly([(12, 18), (19, 18), (19, 22), (12, 22)], t["bc"])        # face avant
    D.anneau(D.d_poly([(12, 18), (20, 10), (27, 10), (27, 14), (19, 22), (12, 22)]), corps_gris=False)


def tous(D):
    """Bouton du dialogue, vue de dessus : panneau gris, ses quatre chants en bleu action."""
    t = D.t
    p = [(4, 8), (28, 8), (28, 24), (4, 24)]
    D.poly(p, t["g2"])
    w = 3.5 if D.petit else 3
    D.trait(D.d_poly(p), t["action"], w)


ICONES = {
    "EdgeBanding": pinceau,
    "Tableau": tableau,
    "Surbrillance": surbrillance,
    "RetirerCouleurs": retirer,
    "boutons/tous": tous,
}


def main():
    for nom, f in ICONES.items():
        dossier = SORTIE / nom
        dossier.mkdir(parents=True, exist_ok=True)
        for theme, suffixe in (("clair", ""), ("sombre", "-dark")):
            for taille, petit in (("32x32", False), ("16x16", True)):
                D = Dessin(theme, petit)
                f(D)
                (dossier / f"{taille}{suffixe}.svg").write_text(D.svg(), encoding="utf-8")
    print(f"{len(ICONES)} icônes écrites")


if __name__ == "__main__":
    main()
