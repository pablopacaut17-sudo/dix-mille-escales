#!/usr/bin/env python3
"""
Robot Sécurité : niveau d'alerte de chaque pays (1 à 4), d'après les avis aux voyageurs publiés
par le Département d'État américain (données publiques, flux officiel mis à jour en continu).
Le site affiche ce niveau à titre indicatif et renvoie toujours vers les Conseils aux voyageurs
du ministère français des Affaires étrangères, qui font foi pour les voyageurs français.

  python3 robots/robot_securite.py
  python3 robots/robot_securite.py --demo
"""
import argparse, html, re, unicodedata
import commun as c

FLUX = "https://travel.state.gov/_res/rss/TAsTWs.xml"
ALIAS = {"burma": "MM", "cote d ivoire": "CI", "the bahamas": "BS", "bahamas": "BS", "the gambia": "GM", "gambia": "GM",
         "republic of the congo": "CG", "democratic republic of the congo": "CD", "mainland china": "CN", "china": "CN",
         "south korea": "KR", "north korea": "KP", "czechia": "CZ", "czech republic": "CZ", "turkey": "TR", "turkiye": "TR",
         "russia": "RU", "vietnam": "VN", "laos": "LA", "syria": "SY", "iran": "IR", "eswatini": "SZ", "timor leste": "TL",
         "micronesia": "FM", "macau": "MO", "hong kong": "HK", "kosovo": "XK", "north macedonia": "MK", "cabo verde": "CV",
         "brunei": "BN", "moldova": "MD", "tanzania": "TZ", "bolivia": "BO", "venezuela": "VE", "united kingdom": "GB",
         "netherlands": "NL", "vatican city": "VA", "holy see": "VA", "sao tome and principe": "ST", "israel": "IL",
         "west bank": "PS", "palestinian territories": "PS", "taiwan": "TW", "the netherlands": "NL", "curacao": "CW",
         "st kitts and nevis": "KN", "saint kitts and nevis": "KN", "st lucia": "LC", "saint lucia": "LC",
         "st vincent and the grenadines": "VC", "saint vincent and the grenadines": "VC", "ireland": "IE",
         "united arab emirates": "AE", "dominican republic": "DO", "central african republic": "CF", "south sudan": "SS",
         "papua new guinea": "PG", "bosnia and herzegovina": "BA", "trinidad and tobago": "TT", "antigua and barbuda": "AG",
         "equatorial guinea": "GQ", "guinea bissau": "GW", "solomon islands": "SB", "marshall islands": "MH", "mauritius": "MU"}


def norm(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", " ", t).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    noms = {norm(p.get("nom_en", "")): cc for cc, p in c.lire("pays.json", {}).items() if p.get("nom_en")}
    noms.update(ALIAS)
    if a.demo:
        texte = ("<item><title>Portugal - Level 1: Exercise Normal Precautions</title><pubDate>Mon, 03 Nov 2026 00:00:00 GMT</pubDate>"
                 "<link>https://travel.state.gov/x</link></item><item><title>Japan - Level 1: Exercise Normal Precautions</title>"
                 "<pubDate>Mon, 03 Nov 2026 00:00:00 GMT</pubDate><link>https://travel.state.gov/y</link></item>")
    else:
        brut = c.http(FLUX)
        if not brut:
            c.journal("securite", "echec")
            raise SystemExit("Flux injoignable, niveaux conservés.")
        texte = brut.decode("utf-8", "replace")
    res, inconnus = {}, []
    for item in re.findall(r"<(?:item|entry)>(.*?)</(?:item|entry)>", texte, re.S):
        t = re.search(r"<title>(.*?)</title>", item, re.S)
        if not t:
            continue
        titre = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1))).strip()
        m = re.match(r"(.+?)\s*[-–]\s*Level\s*(\d)", titre)
        if not m:
            continue
        pays = norm(re.sub(r"\(.*?\)", "", m.group(1)))
        cc = noms.get(pays) or noms.get(pays.replace("the ", "", 1))
        if not cc:
            inconnus.append(m.group(1)); continue
        d = re.search(r"<(?:pubDate|updated)>(.*?)</", item)
        l = re.search(r"<link[^>]*?(?:href=\"([^\"]+)\"[^>]*/?>|>(.*?)</link>)", item, re.S)
        res[cc] = {"niveau": int(m.group(2)), "titre": titre, "date": d.group(1).strip() if d else "",
                   "lien": ((l.group(1) or l.group(2)).strip() if l else "")}
    if not res:
        c.journal("securite", "echec")
        raise SystemExit("Aucun niveau lu : le format du flux a peut-être changé.")
    c.ecrire("securite.json", {"date": c.horodatage(), "source": "U.S. Department of State", "pays": res})
    c.journal("securite", "ok", pays=len(res), non_reconnus=len(inconnus), mode="démo" if a.demo else "réel")
    print(f"Sécurité : {len(res)} pays. Non reconnus : {', '.join(inconnus[:15]) or 'aucun'}")


if __name__ == "__main__":
    main()
