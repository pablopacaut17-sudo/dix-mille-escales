#!/usr/bin/env python3
"""
Robot Lieux : restaurants, cafés, bars, hôtels, musées, monuments, belvédères, parcs, boutiques,
activités (plages, sports nautiques, parcs d'attractions, golf, ski…) et sites notables aux alentours.
Deux cercles par ville :
  - le cercle urbain (au moins 7 km pour les villes phares, jusqu'à 15 km pour les métropoles) : tout est collecté ;
  - le cercle des alentours (50 km, 30 km pour les petites villes) : seulement les sites notables
    (ceux qui ont une fiche Wikidata ou sont classés au patrimoine mondial).
Un seul robot pour toutes les villes : il traite chaque nuit les villes dont les données sont
les plus anciennes (phares chaque semaine, intermédiaires chaque mois, autres tous les 3 mois).
Source : OpenStreetMap via l'API Overpass (© contributeurs OpenStreetMap, ODbL).

  python3 robots/robot_lieux.py --max-villes 60
  python3 robots/robot_lieux.py --ville lisbonne-pt
  python3 robots/robot_lieux.py --demo
"""
import argparse, json, math, sys, time, urllib.parse
from datetime import datetime
import commun as c

# Serveurs Overpass publics et gratuits : chaque robot commence par « le sien » et passe au suivant en cas d'échec
SERVEURS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]
DELAI_REQUETE = 240  # secondes accordées au serveur pour une requête ; au-delà, on passe à la suite
FREQUENCE = {"phare": 7, "intermediaire": 30, "autre": 120}
PAUSE = {"phare": 8, "intermediaire": 6, "autre": 2}  # secondes entre deux villes (politesse envers Overpass)
CIBLES = {
    "amenity": ("restaurant|cafe|bar|pub|fast_food|ice_cream|marketplace|bus_station|ferry_terminal|hospital|clinic|pharmacy|doctors|dentist|bicycle_rental", None),
    "railway": ("station", None),
    "tourism": ("hotel|hostel|guest_house|museum|attraction|viewpoint|gallery|zoo|aquarium", None),
    "historic": ("monument|castle|memorial|ruins|archaeological_site|fort", None),
    "leisure": ("park|garden|nature_reserve|sports_centre|fitness_centre|swimming_pool|stadium", None),
    "sport": ("climbing", None),  # murs et salles d’escalade
    "shop": ("books|wine|deli|bakery|pastry|craft|art|antiques|gift|chocolate|sports|outdoor|bicycle", None),
    "place": ("suburb|neighbourhood|quarter", None),  # quartiers : nom + coordonnées seulement (compacts)
    "route": ("hiking", None),  # sentiers de randonnée qui passent par la ville (même sans fiche Wikidata)
}
# Activités, cherchées dans le cercle urbain et aux alentours
ACTIVITES = {
    "leisure": "water_park|marina|golf_course|swimming_area|beach_resort|ice_rink|horse_riding",
    "tourism": "theme_park|camp_site",
    "natural": "beach",
    "landuse": "winter_sports",
}
# Sites notables aux alentours (avec fiche Wikidata obligatoire)
ALENTOURS = {
    "historic": "castle|archaeological_site|monument|fort|ruins|monastery|city_gate",
    "tourism": "attraction|museum|theme_park|zoo|viewpoint|aquarium",
    "natural": "beach|waterfall|peak|cave_entrance|bay|cliff|volcano|glacier",
    "leisure": "nature_reserve|water_park",
    "boundary": "national_park|protected_area",
}
TYPE = {"restaurant": ("Restaurant", "manger"), "cafe": ("Café", "manger"), "bar": ("Bar", "manger"),
        "pub": ("Pub", "manger"), "fast_food": ("Restauration rapide", "manger"), "ice_cream": ("Glacier", "manger"),
        "marketplace": ("Marché", "acheter"), "hotel": ("Hôtel", "dormir"), "hostel": ("Auberge de jeunesse", "dormir"),
        "guest_house": ("Maison d’hôtes", "dormir"), "museum": ("Musée", "voir"), "attraction": ("Site à voir", "voir"),
        "viewpoint": ("Belvédère", "voir"), "gallery": ("Galerie", "voir"), "zoo": ("Zoo", "voir"),
        "aquarium": ("Aquarium", "voir"), "monument": ("Monument", "voir"), "castle": ("Château", "voir"),
        "memorial": ("Mémorial", "voir"), "ruins": ("Ruines", "voir"), "archaeological_site": ("Site archéologique", "voir"),
        "fort": ("Fort", "voir"), "park": ("Parc", "voir"), "garden": ("Jardin", "voir"),
        "nature_reserve": ("Réserve naturelle", "voir"), "books": ("Librairie", "acheter"), "wine": ("Caviste", "acheter"),
        "deli": ("Épicerie fine", "acheter"), "bakery": ("Boulangerie", "acheter"), "pastry": ("Pâtisserie", "acheter"),
        "craft": ("Artisanat", "acheter"), "art": ("Boutique d’art", "acheter"), "antiques": ("Antiquaire", "acheter"),
        "gift": ("Souvenirs", "acheter"), "chocolate": ("Chocolatier", "acheter"),
        "water_park": ("Parc aquatique", "faire"), "marina": ("Port de plaisance", "faire"), "golf_course": ("Golf", "faire"),
        "swimming_area": ("Baignade", "faire"), "beach_resort": ("Plage aménagée", "faire"), "ice_rink": ("Patinoire", "faire"),
        "horse_riding": ("Équitation", "faire"), "theme_park": ("Parc d’attractions", "faire"), "camp_site": ("Camping", "dormir"),
        "beach": ("Plage", "faire"), "winter_sports": ("Station de ski", "faire"), "monastery": ("Monastère", "voir"),
        "city_gate": ("Porte de ville", "voir"), "waterfall": ("Cascade", "voir"), "peak": ("Sommet", "voir"),
        "cave_entrance": ("Grotte", "voir"), "bay": ("Baie", "voir"), "cliff": ("Falaise", "voir"), "volcano": ("Volcan", "voir"),
        "glacier": ("Glacier", "voir"), "national_park": ("Parc national", "voir"), "protected_area": ("Espace naturel protégé", "voir"),
        "hiking": ("Sentier de randonnée", "faire"),
        "sports": ("Magasin de sport", "acheter"), "outdoor": ("Magasin d’outdoor (randonnée, camping)", "acheter"),
        "bicycle": ("Magasin de vélos", "acheter"), "sports_centre": ("Centre sportif", "faire"),
        "fitness_centre": ("Salle de sport", "faire"), "swimming_pool": ("Piscine", "faire"), "stadium": ("Stade", "faire"),
        "climbing": ("Escalade", "faire"), "bicycle_rental": ("Location de vélos", "bouger"),
        "suburb": ("Quartier", "quartiers"), "neighbourhood": ("Quartier", "quartiers"), "quarter": ("Quartier", "quartiers"),
        "hospital": ("Hôpital", "sante"), "clinic": ("Clinique", "sante"), "pharmacy": ("Pharmacie", "sante"),
        "doctors": ("Médecin", "sante"), "dentist": ("Dentiste", "sante"),
        "station": ("Gare ou station", "bouger"), "bus_station": ("Gare routière", "bouger"), "ferry_terminal": ("Terminal de ferry", "bouger")}
CLES = ("amenity", "tourism", "historic", "leisure", "shop", "natural", "landuse", "boundary", "route", "railway", "place", "sport")
DIRECTIONS = ["au nord", "au nord-est", "à l’est", "au sud-est", "au sud", "au sud-ouest", "à l’ouest", "au nord-ouest"]
CUISINES = {"portuguese": "portugaise", "seafood": "fruits de mer", "fish": "poisson", "italian": "italienne",
            "pizza": "pizza", "burger": "burgers", "japanese": "japonaise", "sushi": "sushis", "chinese": "chinoise",
            "indian": "indienne", "french": "française", "spanish": "espagnole", "mexican": "mexicaine",
            "thai": "thaïe", "vegetarian": "végétarienne", "vegan": "végane", "coffee_shop": "café",
            "regional": "régionale", "mediterranean": "méditerranéenne", "steak_house": "grillades",
            "kebab": "kebab", "sandwich": "sandwichs", "ice_cream": "glaces", "korean": "coréenne",
            "vietnamese": "vietnamienne", "lebanese": "libanaise", "turkish": "turque", "greek": "grecque",
            "american": "américaine", "brazilian": "brésilienne", "african": "africaine", "asian": "asiatique"}
NIVEAU = {"adresse": "critique", "lat": "critique", "lon": "critique",
          "nom": "important", "horaires": "important", "type": "important", "payant": "important"}
CHAMPS = ("nom", "type", "adresse", "lat", "lon", "horaires", "cuisine", "etoiles", "payant",
          "site", "telephone", "fauteuil", "terrasse")


def rayon_km(v):
    """Cercle urbain : assez large pour les quartiers touristiques excentrés (Belém à Lisbonne, par exemple)."""
    r = 2.5 + math.sqrt(v["population"]) / 250
    if v["niveau"] == "phare":
        r = max(r, 7)
    elif v["niveau"] == "intermediaire":
        r = max(r, 5)
    else:
        r = max(r, 3)
    return min(10.0, r)  # au-delà, les requêtes des métropoles deviennent trop lourdes pour les serveurs gratuits


def rayon_alentours_km(v):
    return 30 if v["niveau"] == "autre" else 50


def requetes(v):
    """Requêtes du cercle urbain. Les grandes villes ont des requêtes découpées par thème, plus légères pour le serveur."""
    r, a = int(rayon_km(v) * 1000), f'{v["lat"]},{v["lon"]}'
    morceaux = [f'nwr["{k}"~"^({vals})$"]["name"](around:{r},{a});' for k, (vals, _) in CIBLES.items()]
    morceaux += [f'nwr["{k}"~"^({vals})$"]["name"](around:{r},{a});' for k, vals in ACTIVITES.items()]
    entete = f"[out:json][timeout:{DELAI_REQUETE}][maxsize:536870912];"
    if v["niveau"] == "autre" and v["population"] < 150000:
        return [entete + "(" + "".join(morceaux) + ");out center tags;"]
    return [entete + "(" + m + ");out center tags;" for m in morceaux]


def requete_alentours(v):
    r, a = int(rayon_alentours_km(v) * 1000), f'{v["lat"]},{v["lon"]}'
    blocs = "".join(f'nwr["{k}"~"^({vals})$"]["name"]["wikidata"](around:{r},{a});' for k, vals in ALENTOURS.items())
    blocs += "".join(f'nwr["{k}"~"^({vals})$"]["name"](around:{r},{a});' for k, vals in ACTIVITES.items() if k in ("natural", "landuse"))
    blocs += f'nwr["heritage"="1"]["name"](around:{r},{a});'
    blocs += f'relation["route"="hiking"]["name"]["wikidata"](around:{r},{a});'
    return f"[out:json][timeout:{DELAI_REQUETE}][maxsize:536870912];({blocs});out center tags 2500;"


def direction(v, lat, lon):
    t = math.pi / 180
    y = math.sin((lon - v["lon"]) * t) * math.cos(lat * t)
    x = math.cos(v["lat"] * t) * math.sin(lat * t) - math.sin(v["lat"] * t) * math.cos(lat * t) * math.cos((lon - v["lon"]) * t)
    cap = (math.degrees(math.atan2(y, x)) + 360) % 360
    return DIRECTIONS[int((cap + 22.5) // 45) % 8]


def interroger(q, depart):
    """Essaie la requête sur chaque serveur, en commençant par celui du robot. Renvoie (éléments, serveur utilisé) ou (None, depart)."""
    for k in range(len(SERVEURS)):
        i = (depart + k) % len(SERVEURS)
        brut = c.http(SERVEURS[i], urllib.parse.urlencode({"data": q}).encode(), essais=1, delai=5, timeout=DELAI_REQUETE + 30)
        if brut:
            try:
                d = json.loads(brut)
                if "elements" in d and not d.get("remark", "").lower().startswith(("runtime error", "error")):
                    return d["elements"], i
            except ValueError:
                pass
        time.sleep(3)
    return None, depart


def distance_km(a, b):
    t = math.pi / 180
    x = (math.sin((b[0] - a[0]) * t / 2) ** 2 +
         math.cos(a[0] * t) * math.cos(b[0] * t) * math.sin((b[1] - a[1]) * t / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(x))


def normaliser(el, date, v=None, alentours=False):
    t = el.get("tags", {})
    cle = next((t[k] for k in CLES if t.get(k) in TYPE), None)
    nom = t.get("name:fr") or t.get("name")
    lat = el["lat"] if "lat" in el else el.get("center", {}).get("lat")
    lon = el["lon"] if "lon" in el else el.get("center", {}).get("lon")
    if not cle or not nom or lat is None:
        return None
    if t.get("access") in ("private", "no", "customers") and cle in ("swimming_pool", "sports_centre", "fitness_centre", "climbing", "stadium"):
        return None  # piscines d'hôtel ou privées, clubs fermés : inutiles au voyageur
    type_, rubrique = TYPE[cle]
    if cle == "station":  # distinguer les vraies gares des stations de métro et de tram
        st_ = t.get("station", "")
        type_ = "Station de métro" if st_ in ("subway", "monorail") or t.get("subway") == "yes" else \
            "Station de tram" if st_ in ("light_rail", "tram") or t.get("light_rail") == "yes" else "Gare ferroviaire"
    elif cle == "ferry_terminal":
        type_ = "Port (ferry)"
    if alentours:
        rubrique = "alentours"
    rue = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    f = {"id": f"osm:{el['type']}/{el['id']}", "rubrique": rubrique, "type": type_, "nom": nom,
         "adresse": ", ".join(x for x in (rue, t.get("addr:postcode")) if x),
         "lat": round(lat, 6), "lon": round(lon, 6), "horaires": t.get("opening_hours", ""),
         "cuisine": ", ".join(CUISINES.get(x.strip(), x.strip().replace("_", " "))
                              for x in t.get("cuisine", "").split(";") if x.strip()),
         "etoiles": t.get("stars", ""), "payant": {"yes": "oui", "no": "non"}.get(t.get("fee"), ""),
         "site": t.get("website") or t.get("contact:website", ""),
         "telephone": t.get("phone") or t.get("contact:phone", ""),
         "fauteuil": {"yes": "oui", "limited": "partiel", "no": "non"}.get(t.get("wheelchair"), ""),
         "terrasse": {"yes": "oui", "no": "non"}.get(t.get("outdoor_seating"), ""),
         "wikidata": t.get("wikidata", ""), "patrimoine_mondial": t.get("heritage") == "1", "verifie_le": date}
    if rubrique == "sante" and t.get("emergency") in ("yes", "no"):
        f["urgences"] = "oui" if t["emergency"] == "yes" else "non"  # service d'urgences ouvert au public
    if v is not None:
        f["distance_km"] = round(distance_km((v["lat"], v["lon"]), (lat, lon)), 1)
        f["direction"] = direction(v, lat, lon)
    f["infos"] = sum(1 for k in CHAMPS if f.get(k)) + 1
    return f


def comparer(avant, apres):
    a, b = {f["id"]: f for f in avant}, {f["id"]: f for f in apres}
    ch = [{"niveau": "important", "lieu": b[i]["nom"], "quoi": "nouveau lieu"} for i in b.keys() - a.keys()]
    ch += [{"niveau": "critique", "lieu": a[i]["nom"], "quoi": "absent de la source"} for i in a.keys() - b.keys()]
    for i in a.keys() & b.keys():
        for k in CHAMPS:
            if a[i].get(k) != b[i].get(k):
                niv = NIVEAU.get(k, "sans risque")
                if k in ("lat", "lon") and distance_km((a[i]["lat"], a[i]["lon"]), (b[i]["lat"], b[i]["lon"])) < 0.05:
                    niv = "sans risque"
                ch.append({"niveau": niv, "lieu": b[i]["nom"], "quoi": k, "avant": a[i].get(k), "apres": b[i].get(k)})
    return ch


def demo_elements(v):
    ex = [("amenity", "restaurant", "Restaurant Exemple", {"cuisine": "seafood", "opening_hours": "Mo-Sa 12:00-23:00",
           "addr:street": "Rua Exemplo", "addr:housenumber": "5", "outdoor_seating": "yes"}),
          ("amenity", "cafe", "Café Modèle", {"opening_hours": "Mo-Su 08:00-19:00"}),
          ("tourism", "museum", "Musée Fictif", {"opening_hours": "Tu-Su 10:00-18:00", "fee": "yes", "wheelchair": "yes"}),
          ("tourism", "viewpoint", "Belvédère Exemple", {}),
          ("tourism", "hotel", "Hôtel Modèle", {"stars": "3", "addr:street": "Avenida Exemplo", "addr:housenumber": "100"}),
          ("leisure", "park", "Parc Exemple", {}),
          ("shop", "books", "Librairie Fictive", {"opening_hours": "Mo-Sa 10:00-19:00"})]
    return [{"type": "node", "id": i, "lat": v["lat"] + (i % 3 - 1) * 0.006, "lon": v["lon"] + (i % 4 - 1.5) * 0.007,
             "tags": dict(t, **{k: val, "name": n})} for i, (k, val, n, t) in enumerate(ex, 1)]


def demo_alentours(v):
    ex = [("historic", "castle", "Château d’exemple", 24, {"wikidata": "Q1", "heritage": "1"}),
          ("natural", "beach", "Plage d’exemple", 31, {}), ("boundary", "national_park", "Parc naturel d’exemple", 42, {"wikidata": "Q2"}),
          ("route", "hiking", "Sentier d’exemple", 18, {"wikidata": "Q3"})]
    return [{"type": "node", "id": 100 + i, "lat": v["lat"] + d / 111 * (1 if i % 2 else -0.6), "lon": v["lon"] + d / 111 * (0.5 if i % 2 else -1),
             "tags": dict(t, **{k: val, "name": n})} for i, (k, val, n, d, t) in enumerate(ex)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-villes", type=int, default=1500)
    p.add_argument("--part", type=int, default=0, help="numéro de ce robot quand plusieurs travaillent en parallèle")
    p.add_argument("--parts", type=int, default=1, help="nombre de robots Lieux en parallèle")
    p.add_argument("--ville", help="slug d'une ville, ex. lisbonne-pt")
    p.add_argument("--pause", type=float, default=15)
    p.add_argument("--demo", action="store_true", help="hors ligne : données factices pour 3 villes")
    p.add_argument("--duree-max", type=float, default=320, help="minutes : au-delà, le robot s'arrête proprement")
    a = p.parse_args()

    V = [v for v in c.villes() if v["id"] % a.parts == a.part]
    fsuivi = f"lieux/_suivi_{a.part}.json"
    suivi = c.lire(fsuivi)
    if suivi is None:  # reprise de l'ancien suivi commun
        ancien = c.lire("lieux/_suivi.json", {}) or {}
        suivi = {k: x for k, x in ancien.items() if int(k) % a.parts == a.part}
    t = c.maintenant()
    if a.ville:
        lot = [v for v in V if v["slug"] == a.ville]
    elif a.demo:
        lot = [v for v in V if v["slug"] in ("lisbonne-pt", "porto-pt", "tokyo-jp")]
    else:
        dues = []
        for v in V:
            sv = suivi.get(str(v["id"]), {})
            d = sv.get("dernier_passage")
            retard = (t - datetime.fromisoformat(d)).days - FREQUENCE[v["niveau"]] if d else 10**6
            if retard >= 0:
                echec = sv.get("echec")
                recalee = 1 if echec and (t - datetime.fromisoformat(echec)).days < 3 else 0  # échec récent : en fin de file
                dues.append((recalee, {"phare": 0, "intermediaire": 1, "autre": 2}[v["niveau"]], -retard, -v["population"], v))
        dues.sort(key=lambda x: x[:4])
        lot = [x[4] for x in dues[:a.max_villes]]

    print(f"{len(lot)} ville(s) à traiter.")
    ok = ech = sus = 0
    debut = time.monotonic()
    serveur = a.part % len(SERVEURS)
    for n, v in enumerate(lot, 1):
        if time.monotonic() - debut > a.duree_max * 60:
            print(f"Durée maximale atteinte : arrêt propre, les {len(lot) - n + 1} villes restantes passeront la nuit prochaine.")
            break
        print(f"[{n}/{len(lot)}] {v['nom']} ({v['pays']}, {v['niveau']})")
        if a.demo:
            elements = demo_elements(v)
        else:
            elements, rate = [], False
            for q in requetes(v):
                res, serveur = interroger(q, serveur)
                if res is None:
                    rate = True
                    break
                elements += res
            if rate:
                ech += 1
                sv = suivi.get(str(v["id"]), {})
                suivi[str(v["id"])] = dict(sv, echec=t.isoformat(), nb_echecs=sv.get("nb_echecs", 0) + 1)
                c.ecrire(fsuivi, suivi, compact=True)
                print("    serveurs saturés : ville reportée")
                continue
        date = c.horodatage()
        fiches = [f for f in (normaliser(e, date, v) for e in elements) if f]
        # Second cercle : les sites notables aux alentours (hors du cercle urbain)
        if a.demo:
            autour = demo_alentours(v)
        else:
            time.sleep(1)
            autour, serveur = interroger(requete_alentours(v), serveur)
            autour = autour or []
        r_urbain = rayon_km(v)
        for e in autour:
            f = normaliser(e, date, v, alentours=True)
            if f and f["distance_km"] > r_urbain:
                fiches.append(f)
        vus = set(); fiches = [f for f in fiches if not (f["id"] in vus or vus.add(f["id"]))]
        avant = (c.lire_lieux(v["id"]) or {}).get("lieux", [])
        if avant and len(fiches) < 0.5 * len(avant):
            print(f"    suspect : {len(fiches)} lieux contre {len(avant)}, données conservées")
            sus += 1
            suivi[str(v["id"])] = dict(suivi.get(str(v["id"]), {}), suspect=True, dernier_passage=t.isoformat())
            continue
        ch = comparer(avant, fiches) if avant else []
        c.ecrire_gz(f"lieux/{a.part}/{v['id']}.json.gz", {"ville": v["id"], "date": date, "rayon_km": round(rayon_km(v), 1),
                                                    "rayon_alentours_km": rayon_alentours_km(v), "lieux": fiches, "changements": ch})
        suivi[str(v["id"])] = {"dernier_passage": t.isoformat(), "lieux": len(fiches),
                               "infos": sum(f["infos"] for f in fiches),
                               "critiques": sum(1 for x in ch if x["niveau"] == "critique")}
        c.ecrire(fsuivi, suivi, compact=True)
        ok += 1
        print(f"    {len(fiches)} lieux, {suivi[str(v['id'])]['infos']} informations")
        if not a.demo and n < len(lot):
            time.sleep(PAUSE[v["niveau"]])
    couvertes = len(suivi)
    c.journal(f"lieux_{a.part}", "ok" if ech == 0 else "partiel", villes_traitees=ok, echecs=ech, suspects=sus,
              villes_couvertes=couvertes, mode="démo" if a.demo else "réel")
    print(f"Terminé : {ok} villes à jour, {ech} échecs, {sus} suspectes. {couvertes} villes couvertes au total.")


if __name__ == "__main__":
    main()
