#!/usr/bin/env python3
"""
Robot Météo : prévisions à 7 jours et qualité de l’air pour les villes phares et intermédiaires (≈ 1 100 villes).
Source : Open-Meteo (données CC BY 4.0).
ATTENTION : l'API gratuite d'Open-Meteo est réservée aux usages NON commerciaux. Dès que le site
a de la publicité ou de l'affiliation, prenez un abonnement et placez la clé dans la variable
d'environnement OPENMETEO_KEY (secret GitHub du même nom).

  python3 robots/robot_meteo.py
  python3 robots/robot_meteo.py --demo
"""
import argparse, json, os, random, time, urllib.parse
import commun as c

LOT = 50  # Open-Meteo accepte plusieurs coordonnées séparées par des virgules dans un même appel


def url(villes):
    cle = os.environ.get("OPENMETEO_KEY")
    base = "https://customer-api.open-meteo.com/v1/forecast" if cle else "https://api.open-meteo.com/v1/forecast"
    q = {"latitude": ",".join(str(v["lat"]) for v in villes), "longitude": ",".join(str(v["lon"]) for v in villes),
         "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
         "timezone": "auto", "forecast_days": 7}
    if cle:
        q["apikey"] = cle
    return base + "?" + urllib.parse.urlencode(q)


def qualite_air(lot, demo):
    """Indice européen de qualité de l'air (0 = excellent, plus de 100 = extrêmement mauvais) et particules fines."""
    if demo:
        return {v["id"]: {"indice": random.randint(15, 60), "pm25": random.randint(5, 25)} for v in lot}
    cle = os.environ.get("OPENMETEO_KEY")
    base = "https://customer-air-quality-api.open-meteo.com/v1/air-quality" if cle else "https://air-quality-api.open-meteo.com/v1/air-quality"
    q = {"latitude": ",".join(str(v["lat"]) for v in lot), "longitude": ",".join(str(v["lon"]) for v in lot),
         "current": "european_aqi,pm2_5"}
    if cle:
        q["apikey"] = cle
    brut = c.http(base + "?" + urllib.parse.urlencode(q), delai=20)
    if not brut:
        return {}
    rep = json.loads(brut)
    rep = rep if isinstance(rep, list) else [rep]
    out = {}
    for v, r in zip(lot, rep):
        cur = r.get("current") or {}
        if cur.get("european_aqi") is not None:
            out[v["id"]] = {"indice": round(cur["european_aqi"]), "pm25": round(cur.get("pm2_5") or 0)}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    V = [v for v in c.villes() if v["niveau"] in ("phare", "intermediaire")]
    if a.demo:
        V = [v for v in V if v["slug"] in ("lisbonne-pt", "porto-pt", "tokyo-jp")]
    ok = ech = 0
    for i in range(0, len(V), LOT):
        lot = V[i:i + LOT]
        if a.demo:
            from datetime import date, timedelta
            rep = [{"daily": {"time": [(date.today() + timedelta(d)).isoformat() for d in range(7)],
                              "temperature_2m_max": [random.randint(14, 22) for _ in range(7)],
                              "temperature_2m_min": [random.randint(7, 13) for _ in range(7)],
                              "precipitation_sum": [random.choice([0, 0, 0.4, 3.2]) for _ in range(7)],
                              "weather_code": [random.choice([0, 1, 3, 61]) for _ in range(7)]}} for _ in lot]
        else:
            brut = c.http(url(lot), delai=20)
            if brut is None:
                ech += len(lot)
                continue
            rep = json.loads(brut)
            if isinstance(rep, dict):
                rep = [rep]
        air = qualite_air(lot, a.demo)
        for v, r in zip(lot, rep):
            d = r.get("daily") or {}
            if not d.get("time"):
                ech += 1
                continue
            jours = [{"date": d["time"][k], "max": d["temperature_2m_max"][k], "min": d["temperature_2m_min"][k],
                      "pluie_mm": d["precipitation_sum"][k], "code": d["weather_code"][k]} for k in range(len(d["time"]))]
            fiche = {"date": c.horodatage(), "jours": jours}
            if air.get(v["id"]):
                fiche["air"] = air[v["id"]]
            c.ecrire(f"meteo/{v['id']}.json", fiche, compact=True)
            ok += 1
        if not a.demo:
            time.sleep(2)
    c.journal("meteo", "ok" if ech == 0 else "partiel", villes_a_jour=ok, echecs=ech, mode="démo" if a.demo else "réel")
    print(f"Météo : {ok} villes à jour, {ech} échecs.")


if __name__ == "__main__":
    main()
