#!/usr/bin/env python3
"""
Robot Langues : quelques mots et phrases utiles dans la langue de chaque pays, d'après les guides linguistiques
de Wikivoyage en français (licence CC BY-SA), cités avec un lien vers l'article. Une fois par mois.

  python3 robots/robot_langues.py
"""
import argparse, json, re, time, unicodedata, urllib.parse
from datetime import datetime
import commun as c

API = "https://fr.wikivoyage.org/w/api.php"
SECTIONS_UTILES = ("bases", "expressions de base", "phrases de base", "l'essentiel", "essentiel", "mots de base", "politesse", "salutations", "expressions courantes")


def sans_accents(t):
    return unicodedata.normalize("NFD", (t or "").lower()).encode("ascii", "ignore").decode()


def api(**q):
    q.update(format="json", formatversion=2)
    brut = c.http(API + "?" + urllib.parse.urlencode(q), delai=15)
    return json.loads(brut) if brut else None


def lignes_utiles(texte, n=24):
    """Lignes de la première section « de base » ; à défaut, les premières lignes courtes du guide."""
    blocs = re.split(r"\n(==+)\s*(.*?)\s*==+\n", "\n" + texte)
    candidats = []
    for i in range(1, len(blocs) - 2, 3):
        if any(sans_accents(blocs[i + 1]).startswith(s) for s in SECTIONS_UTILES):
            candidats = blocs[i + 2].splitlines()
            break
    if not candidats:
        candidats = texte.splitlines()
    out = []
    for l in candidats:
        l = l.strip(" *•\t")
        if 3 < len(l) < 140 and (":" in l or "(" in l or "—" in l) and not l.lower().startswith(("voir", "cette page")):
            out.append(l)
        if len(out) >= n:
            break
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--forcer", action="store_true")
    a = p.parse_args()
    ancien = c.lire("langues.json")
    if ancien and not a.forcer and (c.maintenant() - datetime.fromisoformat(ancien["date"].replace("Z", "+00:00"))).days < 30:
        print("Guides linguistiques à jour.")
        return
    titres = []
    for motif in ('intitle:"Guide linguistique"', 'intitle:"guide de conversation"'):
        rep = api(action="query", list="search", srsearch=motif, srlimit=500, srnamespace=0)
        titres += [x["title"] for x in (rep or {}).get("query", {}).get("search", [])]
    if not titres:
        c.journal("langues", "echec", raison="aucun guide linguistique trouvé sur Wikivoyage")
        raise SystemExit("Aucun guide linguistique trouvé.")
    pays = c.lire("pays.json", {}) or {}
    voulues = {l for pz in pays.values() for l in pz.get("langues", [])[:2] if l and l != "français"}
    res = {}
    for langue in sorted(voulues):
        cle = sans_accents(langue)
        titre = next((t for t in titres if re.search(r"\b" + re.escape(cle) + r"\b", sans_accents(t))), None)
        if not titre:
            continue
        rep = api(action="query", prop="extracts", explaintext=1, titles=titre, redirects=1)
        pages = (rep or {}).get("query", {}).get("pages", [])
        texte = pages[0].get("extract") if pages else None
        if not texte:
            continue
        lignes = lignes_utiles(texte)
        if len(lignes) >= 4:
            res[langue] = {"titre": titre, "url": "https://fr.wikivoyage.org/wiki/" + urllib.parse.quote(titre.replace(" ", "_")), "lignes": lignes}
        time.sleep(0.5)
    if len(res) < 5:
        c.journal("langues", "echec", raison=f"seulement {len(res)} langues lues ({len(titres)} guides trouvés)")
        raise SystemExit("Trop peu de langues : guides précédents conservés.")
    c.ecrire("langues.json", {"date": c.horodatage(), "langues": res})
    c.journal("langues", "ok", langues=len(res), guides_trouves=len(titres))
    print(f"Langues : {len(res)} guides linguistiques.")


if __name__ == "__main__":
    main()
