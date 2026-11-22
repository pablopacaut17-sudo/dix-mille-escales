#!/usr/bin/env python3
"""
Robot Lieux (version OpenStreetMap directe) : au lieu d'interroger des serveurs partagés et saturés ville par ville,
il télécharge les fichiers OpenStreetMap complets, région par région, depuis Geofabrik (gratuit), en extrait tous
les lieux utiles et les répartit entre les villes du guide :
  - cercle urbain de chaque ville : restaurants, cafés, bars, hôtels, musées, monuments, parcs, boutiques,
    activités, gares… ;
  - cercle des alentours (50 km, 30 km pour les petites villes) : sites notables (fiche Wikidata, patrimoine mondial,
    plages, cascades, sommets, parcs nationaux, randonnées…).

Plusieurs robots se partagent les régions du monde (--part / --parts). Chaque région est retraitée au plus une fois
par semaine (usage raisonnable des serveurs de Geofabrik). Le robot s'arrête proprement à --duree-max.

Outils : osmium-tool (tri rapide en ligne de commande) et pyosmium (lecture), installés par la tâche GitHub.
Données : © contributeurs OpenStreetMap, licence ODbL ; fichiers fournis par Geofabrik GmbH.

  python3 robots/robot_osm.py --part 0 --parts 4
  python3 robots/robot_osm.py --fichier test.osm.pbf     # test sur un fichier local
"""
import argparse, gzip, json, math, os, shutil, subprocess, sys, time, urllib.request, zlib
from datetime import datetime
import commun as c
import robot_lieux as L

INDEX = "https://download.geofabrik.de/index-v1-nogeom.json"
COMPOSITES = {"alps", "britain-and-ireland", "dach", "us-midwest", "us-northeast", "us-pacific", "us-south", "us-west"}
FREQUENCE_JOURS = 7
TRAVAIL = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "osm")
FILTRES = [
    "nwr/amenity=restaurant,cafe,bar,pub,fast_food,ice_cream,marketplace,bus_station,ferry_terminal",
    "nwr/tourism=hotel,hostel,guest_house,museum,attraction,viewpoint,gallery,zoo,aquarium,theme_park,camp_site",
    "nwr/historic=monument,castle,memorial,ruins,archaeological_site,fort,monastery,city_gate",
    "nwr/leisure=park,garden,nature_reserve,water_park,marina,golf_course,swimming_area,beach_resort,ice_rink,horse_riding",
    "nwr/shop=books,wine,deli,bakery,pastry,craft,art,antiques,gift,chocolate",
    "nwr/natural=beach,waterfall,peak,cave_entrance,bay,cliff,volcano,glacier",
    "nwr/landuse=winter_sports", "nwr/boundary=national_park,protected_area", "nwr/railway=station", "nwr/heritage=1",
    "r/route=hiking",
]
NOTABLES = {"Château", "Site archéologique", "Monastère", "Fort", "Ruines", "Parc national", "Espace naturel protégé", "Réserve naturelle",
            "Cascade", "Sommet", "Grotte", "Volcan", "Glacier", "Plage", "Baie", "Falaise", "Sentier de randonnée", "Station de ski",
            "Parc d’attractions", "Parc aquatique", "Zoo", "Aquarium", "Musée", "Site à voir", "Belvédère", "Monument"}


def dist(a, b, c_, d):
    t = math.pi / 180
    x = math.sin((c_ - a) * t / 2) ** 2 + math.cos(a * t) * math.cos(c_ * t) * math.sin((d - b) * t / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


# ---------- Régions Geofabrik ----------
def regions(part, parts):
    brut = c.http(INDEX, timeout=120, essais=5, delai=20)
    if brut:
        feats = [f["properties"] for f in json.loads(brut)["features"]]
        c.ecrire("geofabrik_index.json", feats, compact=True)  # copie de secours
    else:
        feats = c.lire("geofabrik_index.json")
        if not feats:
            raise SystemExit("Index de Geofabrik injoignable et aucune copie de secours.")
        print("Index de Geofabrik injoignable : copie de secours utilisée.")
    parents = {p.get("parent") for p in feats}
    feuilles = [p for p in feats if p["id"] not in parents and p["id"] not in COMPOSITES and p.get("urls", {}).get("pbf")]
    # Répartition stable entre robots (même région → même robot, d'une nuit à l'autre)
    return [p for p in sorted(feuilles, key=lambda p: p["id"]) if zlib.crc32(p["id"].encode()) % parts == part]


def telecharger(url, chemin):
    req = urllib.request.Request(url, headers={"User-Agent": c.USER_AGENT})
    with urllib.request.urlopen(req, timeout=600) as r, open(chemin, "wb") as f:
        shutil.copyfileobj(r, f, 4 * 1024 * 1024)


def trier(source, cible):
    """Premier tri avec osmium-tool (très rapide) ; si l'outil manque, on lit directement le fichier complet."""
    if shutil.which("osmium"):
        r = subprocess.run(["osmium", "tags-filter", "--overwrite", "-o", cible, source, *FILTRES], capture_output=True, text=True)
        if r.returncode == 0:
            return cible
        print("   tri osmium impossible :", r.stderr[:200])
    return source


# ---------- Lecture des lieux d'un fichier ----------
def lire_lieux(fichier):
    import osmium

    cles = set(L.CLES)
    membres, relations = set(), []

    class Relations(osmium.SimpleHandler):
        def relation(self, r):
            t = {k.k: k.v for k in r.tags}
            if "name" in t and (any(k in t for k in cles) or t.get("heritage") == "1"):
                ws = [m.ref for m in r.members if m.type == "w"][:50]
                membres.update(ws)
                relations.append((r.id, t, ws))

    Relations().apply_file(fichier)
    centres_ways, points = {}, []

    class Elements(osmium.SimpleHandler):
        def node(self, n):
            if len(n.tags) and "name" in n.tags:
                t = {k.k: k.v for k in n.tags}
                points.append(("node", n.id, n.location.lat, n.location.lon, t))

        def way(self, w):
            utile = "name" in w.tags
            if not utile and w.id not in membres:
                return
            try:
                lats = [x.lat for x in w.nodes if x.location.valid()]
                lons = [x.lon for x in w.nodes if x.location.valid()]
            except osmium.InvalidLocationError:
                return
            if not lats:
                return
            centre = (sum(lats) / len(lats), sum(lons) / len(lons))
            if w.id in membres:
                centres_ways[w.id] = centre
            if utile:
                t = {k.k: k.v for k in w.tags}
                points.append(("way", w.id, centre[0], centre[1], t))

    Elements().apply_file(fichier, locations=True, idx="flex_mem")
    for rid, t, ws in relations:
        cs = [centres_ways[w] for w in ws if w in centres_ways]
        if cs:
            points.append(("relation", rid, sum(x[0] for x in cs) / len(cs), sum(x[1] for x in cs) / len(cs), t))
    return points


# ---------- Répartition entre les villes ----------
class Grille:
    def __init__(self, villes):
        self.cases = {}
        for v in villes:
            self.cases.setdefault((int(math.floor(v["lat"] / 0.5)), int(math.floor(v["lon"] / 0.5))), []).append(v)

    def proches(self, lat, lon, km):
        n = int(km / 50) + 1
        gi, gj = int(math.floor(lat / 0.5)), int(math.floor(lon / 0.5))
        for di in range(-n, n + 1):
            for dj in range(-n - 1, n + 2):
                for v in self.cases.get((gi + di, gj + dj), []):
                    yield v


def repartir(points, grille, date, accu):
    """Chaque lieu va à la ville la plus proche dont il est dans le cercle urbain ; les lieux notables vont aussi
    dans les « alentours » des villes situées à moins de 50 km (30 km pour les petites)."""
    for typ, ident, lat, lon, t in points:
        el = {"type": typ, "id": ident, "lat": lat, "lon": lon, "tags": t}
        dedans = set()
        for v in grille.proches(lat, lon, 15):  # toutes les villes (et quartiers) dont le lieu est dans le cercle urbain
            if dist(v["lat"], v["lon"], lat, lon) <= v["_r"]:
                f = L.normaliser(el, date, v)
                if f:
                    accu.setdefault(v["id"], {})[f["id"]] = f
                    dedans.add(v["id"])
        notable = t.get("wikidata") or t.get("heritage") == "1" or t.get("route") == "hiking" or \
            t.get("natural") in ("beach", "waterfall", "peak", "volcano", "glacier") or t.get("landuse") == "winter_sports"
        if not notable:
            continue
        for v in grille.proches(lat, lon, 50):
            if v["id"] in dedans:
                continue
            d = dist(v["lat"], v["lon"], lat, lon)
            if v["_r"] < d <= v["_ra"]:
                f = L.normaliser(el, date, v, alentours=True)
                if f and f["type"] in NOTABLES:
                    accu.setdefault(v["id"], {})[f["id"]] = f


MAX_AUTRES = 400
niveaux, rayons = {}, {}


def ecrire(accu, part, date):
    for vid, lieux in accu.items():
        anc = c.lire_gz_brut(f"lieux/osm-{part}/{vid}.json.gz") or {}
        fusion = {f["id"]: f for f in anc.get("lieux", [])}
        fusion.update(lieux)
        liste = list(fusion.values())
        autour = sorted([f for f in liste if f["rubrique"] == "alentours"], key=lambda f: f.get("distance_km", 99))[:300]
        urbains = [f for f in liste if f["rubrique"] != "alentours"]
        if niveaux.get(vid) == "autre" and len(urbains) > MAX_AUTRES:  # petites villes et quartiers : les plus complets
            urbains = sorted(urbains, key=lambda f: -f["infos"])[:MAX_AUTRES]
        liste = urbains + autour
        c.ecrire_gz(f"lieux/osm-{part}/{vid}.json.gz", {"ville": vid, "date": date, "source": "OpenStreetMap (Geofabrik)",
                                                         "rayon_km": rayons.get(vid, (3, 30))[0], "rayon_alentours_km": rayons.get(vid, (3, 30))[1],
                                                         "lieux": liste})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--part", type=int, default=0)
    p.add_argument("--parts", type=int, default=1)
    p.add_argument("--duree-max", type=float, default=320)
    p.add_argument("--fichier", help="tester sur un fichier .osm.pbf local")
    p.add_argument("--region", help="traiter une seule région Geofabrik (ex. portugal), pour un test")
    a = p.parse_args()
    debut, t0 = time.monotonic(), c.maintenant()
    villes = c.villes()
    for v in villes:
        v["_r"], v["_ra"] = L.rayon_km(v), L.rayon_alentours_km(v)
        niveaux[v["id"]] = v["niveau"]
        rayons[v["id"]] = (round(v["_r"], 1), v["_ra"])
    grille = Grille(villes)
    suivi_f = f"lieux/_osm_suivi_{a.part}.json"
    suivi = c.lire(suivi_f, {}) or {}
    os.makedirs(TRAVAIL, exist_ok=True)
    if a.fichier:
        a_faire = [{"id": "test", "name": "fichier de test", "urls": {"pbf": None}}]
    elif a.region:
        a_faire = [r for r in regions(0, 1) if r["id"] == a.region]
    else:
        a_faire = []
        for r in regions(a.part, a.parts):
            d = suivi.get(r["id"])
            if not d or (t0 - datetime.fromisoformat(d)).days >= FREQUENCE_JOURS:
                a_faire.append(r)
        a_faire.sort(key=lambda r: suivi.get(r["id"], ""))  # jamais faites d'abord, puis les plus anciennes
    print(f"{len(a_faire)} région(s) à traiter.")
    faites = ech = nb_lieux = 0
    villes_touchees = set()
    for r in a_faire:
        if time.monotonic() - debut > a.duree_max * 60:
            print("Durée maximale atteinte : les autres régions passeront la nuit prochaine.")
            break
        date = c.horodatage()
        source = a.fichier or os.path.join(TRAVAIL, "region.osm.pbf")
        try:
            t1 = time.monotonic()
            if not a.fichier:
                telecharger(r["urls"]["pbf"], source)
            fichier = trier(source, os.path.join(TRAVAIL, "tri.osm.pbf"))
            points = lire_lieux(fichier)
            accu = {}
            repartir(points, grille, date, accu)
            for v in villes:
                if v["id"] in accu:
                    villes_touchees.add(v["id"])
            ecrire(accu, a.part, date)
            nb_lieux += sum(len(x) for x in accu.values())
            suivi[r["id"]] = t0.isoformat()
            faites += 1
            print(f"{r['name']} : {len(points)} lieux lus, {len(accu)} villes servies, {round(time.monotonic() - t1)} s")
        except Exception as e:
            ech += 1
            print(f"{r.get('name', r['id'])} : échec ({e})")
        finally:
            for f in ("region.osm.pbf", "tri.osm.pbf"):
                if not a.fichier and os.path.exists(os.path.join(TRAVAIL, f)):
                    os.remove(os.path.join(TRAVAIL, f))
        c.ecrire(suivi_f, suivi, compact=True)
    c.journal(f"lieux_{a.part}", "ok" if ech == 0 else "partiel", regions_traitees=faites, echecs=ech,
              villes_servies=len(villes_touchees), lieux=nb_lieux, regions_restantes=max(0, len(a_faire) - faites - ech),
              mode="test" if a.fichier else "réel")
    print(f"Terminé : {faites} régions, {ech} échecs, {len(villes_touchees)} villes servies, {nb_lieux} lieux.")


if __name__ == "__main__":
    main()
