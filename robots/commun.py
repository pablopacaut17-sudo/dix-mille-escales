"""Outils partagés par tous les robots de Dix Mille Escales."""
import gzip, json, os, sys, time, urllib.request
from datetime import datetime, timezone

# Les machines de GitHub n'ont pas de route IPv6 vers certains serveurs : on force l'IPv4 (sans effet ailleurs)
import socket as _socket
_getaddrinfo = _socket.getaddrinfo


def _ipv4_seulement(hote, *args, **kwargs):
    res = _getaddrinfo(hote, *args, **kwargs)
    v4 = [r for r in res if r[0] == _socket.AF_INET]
    return v4 or res


_socket.getaddrinfo = _ipv4_seulement

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(RACINE, "data")  # liste des villes et des pays : dans le dépôt principal
# Données des robots : dans un dossier à part (branches « donnees-… » du dépôt), jamais dans l'historique principal
DATA = os.environ.get("DME_DONNEES") or CONFIG
FICHIERS_CONFIG = ("villes.json", "pays.json")


def _chemin(nom):
    return os.path.join(CONFIG if nom in FICHIERS_CONFIG else DATA, nom)
USER_AGENT = "DixMilleEscales/1.0 (+https://github.com/ ; robots du guide)"


def maintenant():
    return datetime.now(timezone.utc)


def horodatage():
    return maintenant().strftime("%Y-%m-%dT%H:%M:%SZ")


def lire(chemin, defaut=None):
    chemin = _chemin(chemin)
    if not os.path.exists(chemin):
        return defaut
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def ecrire(chemin, donnees, compact=False):
    chemin = _chemin(chemin)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            json.dump(donnees, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)  # jamais de fichier à moitié écrit


def ecrire_gz(chemin, donnees):
    """JSON compressé : 5 à 10 fois moins de place dans le dépôt."""
    chemin = _chemin(chemin)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin + ".tmp", "wb") as f:
        f.write(gzip.compress(json.dumps(donnees, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))
    os.replace(chemin + ".tmp", chemin)


def lire_gz_brut(nom):
    p = os.path.join(DATA, nom)
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def lire_lieux(ville_id):
    """Fichier des lieux d'une ville, où qu'il soit rangé (lieux/<n°>/<id>.json.gz, ou anciens formats non compressés)."""
    base = os.path.join(DATA, "lieux")
    if os.path.isdir(base):
        for d in os.listdir(base):
            for ext, ouvrir in ((".json.gz", gzip.open), (".json", open)):
                p = os.path.join(base, d, f"{ville_id}{ext}")
                if os.path.isfile(p):
                    with ouvrir(p, "rt", encoding="utf-8") as f:
                        return json.load(f)
    return lire(f"lieux/{ville_id}.json")


def villes():
    return lire("villes.json", [])


def http(url, donnees=None, essais=3, delai=30, timeout=120):
    """Télécharge une URL avec plusieurs essais. Renvoie les octets, ou None en cas d'échec."""
    for n in range(1, essais + 1):
        try:
            req = urllib.request.Request(url, data=donnees, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status == 204:
                    return b""
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None  # inutile de réessayer
            print(f"    essai {n}/{essais} : erreur {e.code}", file=sys.stderr)
        except Exception as e:
            print(f"    essai {n}/{essais} : {e}", file=sys.stderr)
        time.sleep(delai * n)
    return None


def journal(robot, etat, **details):
    """Note le résultat du passage (un fichier par robot), affiché sur la page « État des robots » du site."""
    ecrire(f"journal/{robot}.json", dict(details, etat=etat, dernier_passage=horodatage()))
