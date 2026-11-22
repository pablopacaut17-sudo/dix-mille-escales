#!/usr/bin/env python3
"""
Robot Conseils : les Conseils aux voyageurs et avertissements du gouvernement du Canada, en français
(données ouvertes, Licence du gouvernement ouvert – Canada) : niveau de risque, zones à éviter, sécurité
(dont transports et arnaques), entrée et sortie, santé et vaccins, lois et coutumes, catastrophes naturelles
et climat, services d'urgence locaux.

Les fiches du ministère français (diplomatie.gouv.fr) ne sont pas réutilisables (« tous droits réservés ») :
le site y renvoie par un lien, et elles font foi pour les voyageurs français.

Une fiche n'est retéléchargée que si sa date de publication a changé.

  python3 robots/robot_conseils.py
"""
import argparse, html, json, re, time
from html.parser import HTMLParser
import commun as c

INDEX = "https://data.international.gc.ca/travel-voyage/index-alpha-fra.json"
FICHE = "https://data.international.gc.ca/travel-voyage/cta-cap-{iso}.json"
SECTIONS = [("advisories", "avertissements"), ("security", "securite"), ("entry-exit", "entree_sortie"), ("health", "sante"),
            ("laws-culture", "lois_culture"), ("disasters-climate", "catastrophes_climat"), ("offices-html", "aide")]


class Blocs(HTMLParser):
    """Transforme le HTML en blocs simples et sûrs : titres, paragraphes, éléments de liste."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocs, self.tampon, self.genre = [], [], None

    def _fin(self):
        t = re.sub(r"\s+", " ", "".join(self.tampon)).strip()
        if t and self.genre:
            if not (self.blocs and self.blocs[-1] == [self.genre, t]):
                self.blocs.append([self.genre, t])
        self.tampon = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h2", "h3", "h4", "h5"):
            self._fin(); self.genre = "t"
        elif tag in ("p", "div", "td"):
            self._fin(); self.genre = "p"
        elif tag == "li":
            self._fin(); self.genre = "l"
        elif tag == "br":
            self.tampon.append(" ")

    def handle_endtag(self, tag):
        if tag in ("h2", "h3", "h4", "h5", "p", "li", "div", "td", "ul", "ol"):
            self._fin(); self.genre = "p"

    def handle_data(self, d):
        if self.genre is None:
            self.genre = "p"
        self.tampon.append(d)


def blocs(h):
    if not isinstance(h, str) or not h.strip():
        return []
    b = Blocs(); b.feed(h); b._fin()
    return [x for x in b.blocs if len(x[1]) > 1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--forcer", action="store_true")
    a = p.parse_args()
    brut = c.http(INDEX, timeout=120)
    if not brut:
        c.journal("conseils", "echec", raison="index du gouvernement du Canada injoignable")
        raise SystemExit("Index injoignable : conseils précédents conservés.")
    index = json.loads(brut).get("data", {})
    pays_guide = set(c.lire("pays.json", {}) or {})
    faits = gardes = ech = 0
    for iso, e in index.items():
        if len(iso) != 2 or iso not in pays_guide:
            continue  # régions (ex. Açores) et territoires hors du guide
        date = (e.get("date-published") or {}).get("date", "")
        ancien = c.lire(f"conseils/{iso}.json")
        if ancien and ancien.get("date_source") == date and not a.forcer:
            gardes += 1
            continue
        brut = c.http(FICHE.format(iso=iso), timeout=120, delai=10)
        if not brut:
            ech += 1
            continue
        try:
            d = json.loads(brut)["data"]
        except (ValueError, KeyError):
            ech += 1
            continue
        fr = d.get("fra", {})
        sections = {cle: blocs(fr.get(src)) for src, cle in SECTIONS}
        c.ecrire(f"conseils/{iso}.json", {
            "date": c.horodatage(), "date_source": date, "niveau": d.get("advisory-state", e.get("advisory-state", 0)),
            "avertissement_regional": bool(d.get("has-regional-advisory")), "niveau_texte": fr.get("advisory-text", ""),
            "mise_a_jour": fr.get("friendly-date", ""), "nouveautes": fr.get("recent-updates", ""),
            "url": "https://voyage.gc.ca/destinations/" + fr.get("url-slug", ""), "sections": {k: v for k, v in sections.items() if v}}, compact=True)
        faits += 1
        time.sleep(0.5)
    c.journal("conseils", "ok" if ech == 0 else "partiel", fiches_mises_a_jour=faits, fiches_inchangees=gardes, echecs=ech)
    print(f"Conseils : {faits} fiches mises à jour, {gardes} inchangées, {ech} échecs.")


if __name__ == "__main__":
    main()
