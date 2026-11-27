#!/usr/bin/env python3
"""
Robot Rédaction : écrit des conseils de voyage originaux en français (villes phares, puis intermédiaires, puis les autres)
à partir des données vérifiées des autres robots (histoire, lieux, climat, budget, formalités).
Il utilise l'API Claude d'Anthropic : clé à placer dans le secret GitHub ANTHROPIC_API_KEY.
Sans clé, le robot ne fait rien. Le texte est marqué sur le site comme rédigé par IA.
Consigne donnée au modèle : n'utiliser que les faits fournis, n'inventer ni adresse ni prix.

  python3 robots/robot_redaction.py                 # 80 villes par nuit (Claude Haiku 5.5, ≈ 0,3 $ par nuit au maximum)
  python3 robots/robot_redaction.py --niveau intermediaire --max-villes 50
  python3 robots/robot_redaction.py --demo
"""
import argparse, json, os, re, time
from datetime import datetime
import commun as c

API = "https://api.anthropic.com/v1/messages"
MODELE = os.environ.get("CLAUDE_MODEL") or "claude-haiku-5-5"  # Haiku 5.5 : environ 10 fois moins cher que Sonnet, pour rédiger bien plus de villes
RENOUVELER = {"phare": 30, "intermediaire": 180, "autre": 365}  # jours avant de réécrire les conseils d'une ville
CONSIGNE = """Tu es rédacteur d'un guide de voyage francophone exigeant, dans l'esprit des meilleurs guides papier.
À partir UNIQUEMENT des faits fournis, rédige des conseils utiles, concrets et chaleureux sur la ville.
Règles absolues : n'invente aucun nom de lieu, d'adresse, de prix, d'horaire ou de date qui ne figure pas dans les faits.
Si une information manque, n'en parle pas. Pas de superlatifs creux, pas de clichés publicitaires.
Réponds uniquement avec un objet JSON valide, sans texte autour, de la forme :
{"accroche": "2 phrases qui donnent envie",
 "pourquoi": ["3 à 5 raisons d'y aller, une phrase chacune"],
 "conseils": ["6 à 10 conseils pratiques d'initié, une ou deux phrases chacun"],
 "a_eviter": ["3 à 5 erreurs à éviter"],
 "quand_partir": "2 à 3 phrases fondées sur les normales climatiques fournies",
 "un_jour": ["programme d'une journée en 3 à 5 étapes, avec des lieux cités dans les faits"],
 "trois_jours": ["jour 1 : …", "jour 2 : …", "jour 3 : …"],
 "pour_qui": "1 phrase : quel type de voyageur appréciera le plus"}"""


def faits(v, pays):
    enc = c.lire(f"encyclo/{v['id']}.json") or {}
    wp = enc.get("wikipedia") or {}
    lieux = (c.lire_lieux(v["id"]) or {}).get("lieux", [])
    clim = (c.lire(f"climat/{v['id']}.json") or {}).get("mois")
    cout = (c.lire("cout.json") or {}).get("pays", {}).get(v["pays"])
    voir = sorted([l for l in lieux if l["rubrique"] == "voir"], key=lambda l: -l["infos"])[:40]
    manger = sorted([l for l in lieux if l["rubrique"] == "manger"], key=lambda l: -l["infos"])[:20]
    f = {"ville": v["nom"], "pays": pays.get(v["pays"], {}).get("nom"), "population": v["population"],
         "description": enc.get("description"), "fondation": enc.get("fondation"), "surnoms": enc.get("surnoms"),
         "resume": (wp.get("resume") or "")[:2500],
         "histoire": (wp.get("sections", {}).get("histoire", {}).get("texte") or "")[:3500],
         "gastronomie": (wp.get("sections", {}).get("gastronomie", {}).get("texte") or "")[:1500],
         "culture": (wp.get("sections", {}).get("culture", {}).get("texte") or "")[:1500],
         "patrimoine_unesco": enc.get("unesco"), "evenements": [e["date"] + " : " + e["nom"] for e in enc.get("evenements", [])][:20],
         "lieux_a_voir": [f"{l['nom']} ({l['type']})" for l in voir],
         "ou_manger": [f"{l['nom']} ({l['type']}{', ' + l['cuisine'] if l.get('cuisine') else ''})" for l in manger],
         "normales_climatiques": [{"mois": i + 1, "tmax": m["tmax"], "pluie_mm": m["pluie_mm"], "jours_pluie": m["jours_pluie"]}
                                  for i, m in enumerate(clim)] if clim else None,
         "niveau_des_prix_vs_france": cout["indice"] if cout else None}
    return {k: x for k, x in f.items() if x}


def appeler(cle, donnees):
    corps = json.dumps({"model": MODELE, "max_tokens": 8000, "system": CONSIGNE,
                        "messages": [{"role": "user", "content": "Faits vérifiés sur la ville :\n" + json.dumps(donnees, ensure_ascii=False)}]}).encode()
    import urllib.request
    req = urllib.request.Request(API, data=corps, headers={"x-api-key": cle, "anthropic-version": "2023-06-01",
                                                           "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        rep = json.load(r)
    texte = "".join(b.get("text", "") for b in rep.get("content", []) if b.get("type") == "text")
    texte = re.sub(r"^```(?:json)?|```$", "", texte.strip()).strip()
    return json.loads(texte)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--niveau", default="tous", choices=["tous", "phare", "intermediaire", "autre"])
    p.add_argument("--max-villes", type=int, default=80)
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    cle = os.environ.get("ANTHROPIC_API_KEY")
    if not cle and not a.demo:
        c.journal("redaction", "désactivé", raison="secret ANTHROPIC_API_KEY absent")
        print("Pas de clé ANTHROPIC_API_KEY : robot Rédaction désactivé.")
        return
    pays = c.lire("pays.json", {})
    V = c.villes()
    if a.demo:
        lot = [v for v in V if v["slug"] in ("porto-pt", "tokyo-jp")]
    else:
        lot = []
        ordre = {"phare": 0, "intermediaire": 1, "autre": 2}
        for v in sorted(V, key=lambda v: (ordre[v["niveau"]], -v["population"])):  # villes phares, puis intermédiaires, puis les autres, les plus peuplées d'abord
            if a.niveau != "tous" and v["niveau"] != a.niveau:
                continue
            anc = c.lire(f"redaction/{v['id']}.json")
            if not anc or (c.maintenant() - datetime.fromisoformat(anc["date"].replace("Z", "+00:00"))).days >= RENOUVELER[v["niveau"]]:
                if c.lire(f"encyclo/{v['id']}.json") or c.lire_lieux(v["id"]):  # il faut des faits
                    lot.append(v)
            if len(lot) >= a.max_villes:
                break
    ok = ech = 0
    for v in lot:
        donnees = faits(v, pays)
        try:
            if a.demo:
                texte = {"accroche": f"Texte d’exemple pour {v['nom']} (mode démo).", "pourquoi": ["Raison d’exemple."] * 3,
                         "conseils": ["Conseil d’exemple."] * 6, "a_eviter": ["Erreur d’exemple."] * 3,
                         "quand_partir": "Phrase d’exemple sur la meilleure période.", "un_jour": ["Étape d’exemple."] * 4,
                         "trois_jours": ["jour 1 : exemple", "jour 2 : exemple", "jour 3 : exemple"], "pour_qui": "Voyageur d’exemple."}
            else:
                texte = appeler(cle, donnees)
        except Exception as e:
            print(f"{v['nom']} : échec ({e})")
            ech += 1
            continue
        c.ecrire(f"redaction/{v['id']}.json", dict(texte, date=c.horodatage(), modele=MODELE))
        ok += 1
        print(f"{v['nom']} : conseils rédigés")
        if not a.demo:
            time.sleep(2)
    c.journal("redaction", "ok" if ech == 0 else "partiel", villes_redigees=ok, echecs=ech, modele=MODELE, mode="démo" if a.demo else "réel")


if __name__ == "__main__":
    main()
