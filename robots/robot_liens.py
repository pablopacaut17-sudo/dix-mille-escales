#!/usr/bin/env python3
"""
Robot Liens cassés : vérifie les sites web des lieux (musées, restaurants, offices de tourisme…) affichés dans le guide.

Chaque jour, il teste un paquet de liens (d'abord ceux qui ont échoué la veille, puis les plus anciennement vérifiés).
Un lien n'est déclaré mort qu'après deux échecs nets (page introuvable 404/410, site disparu, erreur serveur) à
au moins un jour d'écart : un site en panne quelques heures n'est pas retiré. build.py n'affiche plus les liens morts.
Un lien mort est retesté tous les 30 jours et réapparaît s'il remarche ; un lien valide est retesté tous les 60 jours.
Les refus d'accès (403, 429…) ne comptent pas : beaucoup de sites bloquent les robots mais marchent pour les visiteurs.

État : liens.json.gz  {url: [date du dernier test, dernier résultat, échecs consécutifs]}

  python3 robots/robot_liens.py --max 4000 --duree-max 40
"""
import argparse, os, re, time, gzip, json, urllib.request, urllib.error, concurrent.futures as cf
from datetime import date, timedelta
import commun as c

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "fr,en;q=0.8"}
DEBUT = time.monotonic()


def urls_des_lieux():
    """Toutes les adresses de sites web présentes dans les fichiers de lieux."""
    U = set()
    base = os.path.join(c.DATA, "lieux")
    for racine, _, fichiers in os.walk(base):
        for fn in fichiers:
            if not fn.endswith((".json", ".json.gz")):
                continue
            p = os.path.join(racine, fn)
            try:
                with (gzip.open if fn.endswith(".gz") else open)(p, "rt", encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            for x in d.get("lieux", []) if isinstance(d, dict) else []:
                u = (x.get("site") or "").strip()
                if re.match(r"https?://[^\s]+\.[a-z]{2,}", u, re.I):
                    U.add(u)
    return U


def tester(u):
    for m in ("HEAD", "GET"):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA, method=m), timeout=20) as r:
                return u, r.status
        except urllib.error.HTTPError as e:
            if m == "HEAD" and e.code not in (404, 410):
                continue  # beaucoup de sites refusent HEAD : on réessaie en GET
            return u, e.code
        except Exception as e:
            if m == "GET":
                return u, str(getattr(e, "reason", e))[:60]
    return u, "?"


def echec(s):
    if isinstance(s, int):
        return s in (404, 410) or s >= 500
    return any(k in s for k in ("Name or service not known", "No address", "Connection refused", "nodename", "getaddrinfo"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max", type=int, default=4000)
    p.add_argument("--duree-max", type=int, default=40, help="minutes")
    a = p.parse_args()
    etat = c.lire_gz_brut("liens.json.gz") or {}
    U = urls_des_lieux()
    auj = date.today()
    hier = (auj - timedelta(days=1)).isoformat()
    for u in list(etat):
        if u not in U:
            del etat[u]  # lien qui n'est plus dans les données
    def priorite(u):
        e = etat.get(u)
        if not e:
            return (1, "")
        if e[2] == 1 and e[0] <= hier:
            return (0, e[0])  # premier échec : on confirme ou on infirme dès le lendemain
        delai = 30 if e[2] >= 2 else 60
        return (2, e[0]) if e[0] <= (auj - timedelta(days=delai)).isoformat() else (9, e[0])
    file = sorted((u for u in U if priorite(u)[0] < 9), key=priorite)[:a.max]
    print(f"{len(U)} liens connus, {len(file)} à tester aujourd'hui.")
    n = morts = 0
    with cf.ThreadPoolExecutor(24) as ex:
        for i in range(0, len(file), 200):
            if time.monotonic() - DEBUT > a.duree_max * 60:
                break
            for u, s in ex.map(tester, file[i:i + 200]):
                avant = etat.get(u, ["", "", 0])
                etat[u] = [auj.isoformat(), str(s), (avant[2] + 1) if echec(s) else 0]
                n += 1
    morts = sum(1 for e in etat.values() if e[2] >= 2)
    c.ecrire_gz("liens.json.gz", etat)
    c.journal("liens", "ok", testes=n, connus=len(U), morts=morts)
    print(f"{n} liens testés ; {morts} liens morts masqués sur le site.")


if __name__ == "__main__":
    main()
