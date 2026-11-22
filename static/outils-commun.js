/* Dix Mille Escales – fonctions communes aux outils (planificateur, « où partir », comparateur, carnet, préparation). */
window.DME = (function () {
  var root = document.body.getAttribute('data-root') || '../';
  var MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  var monde = null, parSlug = null, index = null;

  function E(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function nb(n) { return new Intl.NumberFormat('fr-FR').format(Math.round(n)); }
  function norm(t) { return (t || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[’'\-|]/g, ' '); }
  function dist(a, b) {
    var t = Math.PI / 180, x = Math.pow(Math.sin((b.lat - a.lat) * t / 2), 2) + Math.cos(a.lat * t) * Math.cos(b.lat * t) * Math.pow(Math.sin((b.lon - a.lon) * t / 2), 2);
    return 2 * 6371 * Math.asin(Math.sqrt(x));
  }
  function lireJson(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); }).then(function (b) {
      var o = new Uint8Array(b);
      if (o[0] === 0x1f && o[1] === 0x8b) {
        if (!('DecompressionStream' in window)) throw new Error('Navigateur trop ancien');
        return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
      }
      return JSON.parse(new TextDecoder().decode(o));
    });
  }
  // Ville : [slug, nom, pays, lat, lon, pop, niveau, tmax[12], tmin[12], pluie[12], voir, manger, dormir, faire, culture, nature, plage, ski, [aéroport, km]]
  function ville(r) {
    return { slug: r[0], nom: r[1], cc: r[2], lat: r[3], lon: r[4], pop: r[5], niveau: r[6], tmax: r[7] || null, tmin: r[8] || null, pluie: r[9] || null,
      voir: r[10], manger: r[11], dormir: r[12], faire: r[13], culture: r[14], nature: r[15], plage: !!r[16], ski: !!r[17], aero: r[18] || null };
  }
  function chargerMonde() {
    if (monde) return Promise.resolve(monde);
    return lireJson(root + 'static/monde.json.gz').then(function (d) {
      monde = { villes: d.villes.map(ville), pays: d.pays, change: d.change, change_date: d.change_date, date: d.date };
      parSlug = {}; monde.villes.forEach(function (v) { parSlug[v.slug] = v; });
      return monde;
    });
  }
  function chargerIndex() {
    if (index) return Promise.resolve(index);
    return fetch(root + 'static/index.json').then(function (r) { return r.json(); }).then(function (d) {
      index = d.map(function (r) { return { nom: r[0], slug: r[1], pays: r[2], pop: r[3] + (r[5] ? 1e10 : 0), k: norm(r[0] + ' ' + (r[4] || '').split('|').join(' ')) }; });
      return index;
    });
  }
  function chercher(q, n) {
    var t = norm(q).trim(); if (t.length < 2 || !index) return [];
    var res = [];
    for (var i = 0; i < index.length && res.length < 60; i++) { var k = index[i].k; if (k.indexOf(t) === 0 || k.indexOf(' ' + t) > -1) res.push(index[i]); }
    res.sort(function (a, b) { return (norm(a.nom).indexOf(t) === 0 ? 0 : 1) - (norm(b.nom).indexOf(t) === 0 ? 0 : 1) || b.pop - a.pop; });
    return res.slice(0, n || 8);
  }
  /* Champ de choix d'une ville avec suggestions. onChoix(slug) */
  function choixVille(input, onChoix) {
    var ul = document.createElement('ul'); ul.className = 'o-sugg'; input.parentNode.style.position = 'relative'; input.parentNode.appendChild(ul);
    var hits = [], act = -1;
    function rendre() { ul.innerHTML = hits.map(function (h, i) { return '<li data-i="' + i + '" aria-selected="' + (i === act) + '">' + E(h.nom) + '<span>' + E(h.pays) + '</span></li>'; }).join(''); }
    function prendre(i) { var h = hits[i]; if (!h) return; ul.innerHTML = ''; input.value = ''; hits = []; onChoix(h.slug); }
    input.addEventListener('focus', function () { chargerIndex(); });
    input.addEventListener('input', function () { chargerIndex().then(function () { hits = chercher(input.value); act = -1; rendre(); }); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { act = Math.min(hits.length - 1, act + 1); rendre(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { act = Math.max(0, act - 1); rendre(); e.preventDefault(); }
      else if (e.key === 'Enter') { e.preventDefault(); prendre(act > -1 ? act : 0); }
      else if (e.key === 'Escape') ul.innerHTML = '';
    });
    ul.addEventListener('mousedown', function (e) { var li = e.target.closest('li'); if (li) { e.preventDefault(); prendre(+li.getAttribute('data-i')); } });
    input.addEventListener('blur', function () { setTimeout(function () { ul.innerHTML = ''; }, 150); });
  }
  /* Trajet entre deux villes : mode conseillé et durée estimée (heures). */
  function trajet(a, b) {
    var d = dist(a, b), route = d < 100 ? d * 1.3 / 60 : d * 1.2 / 85;  // détours de la route ; plus rapide sur les longues distances
    if (d > 350 && a.aero && b.aero) {
      var avion = 2.2 + d / 750 + (a.aero[1] + b.aero[1]) / 60;  // enregistrement, vol, accès aux aéroports
      if (avion < route) return { km: d, mode: 'avion', h: avion, detail: 'vol ' + a.aero[0] + ' → ' + b.aero[0] };
    }
    if (d > 1500) return { km: d, mode: 'avion', h: 3 + d / 750, detail: 'vol conseillé (pas d’aéroport proche trouvé pour l’une des villes)' };
    return { km: d, mode: d < 60 ? 'route courte' : 'route ou train', h: route, detail: '' };
  }
  function duree(h) { return h < 1 ? Math.max(10, Math.round(h * 12) * 5) + ' min' : Math.floor(h) + ' h' + (Math.round(h % 1 * 60) >= 5 ? ' ' + String(Math.round(h % 1 * 12) * 5).padStart(2, '0') : ''); }
  /* Climat d'une ville pour un mois : texte et alerte éventuelle. */
  function climat(v, m) {
    if (!v.tmax) return { ok: true, texte: 'climat non encore disponible', alerte: '' };
    var tx = v.tmax[m], tn = v.tmin[m], p = v.pluie[m], al = '';
    if (p > 300) al = 'très pluvieux (mousson ou saison des pluies)';
    else if (tx >= 38) al = 'très chaud';
    else if (tx <= 2) al = 'froid, neige possible';
    return { ok: !al, tx: tx, tn: tn, p: p, texte: tn + ' à ' + tx + ' °C, ' + p + ' mm de pluie', alerte: al };
  }
  /* Carnet : villes et itinéraires gardés sur l'appareil */
  function carnet() { try { return JSON.parse(localStorage.getItem('dme-carnet') || '{}') || {}; } catch (e) { return {}; } }
  function garder(c) { try { localStorage.setItem('dme-carnet', JSON.stringify(c)); } catch (e) {} }
  function carnetVille(slug, ajouter) {
    var c = carnet(); c.villes = c.villes || [];
    var i = c.villes.indexOf(slug);
    if (ajouter === undefined) ajouter = i < 0;
    if (ajouter && i < 0) c.villes.push(slug); if (!ajouter && i > -1) c.villes.splice(i, 1);
    garder(c); return ajouter;
  }
  /* Liste de préparation pour un ensemble de villes et un mois */
  function preparation(villes, mois, passeport) {
    var m = monde, pays = {}, tmin = 99, tmax = -99, pluie = 0, routes = false;
    villes.forEach(function (v) {
      pays[v.cc] = 1;
      if (v.tmax) { tmin = Math.min(tmin, v.tmin[mois]); tmax = Math.max(tmax, v.tmax[mois]); pluie = Math.max(pluie, v.pluie[mois]); }
    });
    var L = { 'Papiers': [], 'Argent': [], 'Valise': [], 'Santé et sécurité': [] };
    Object.keys(pays).forEach(function (cc) {
      var p = m.pays[cc] || {}, visa = (p.visa || {})[passeport || 'Passeport français'] || 'information non disponible';
      L['Papiers'].push(E(p.nom) + ' : ' + E(visa) + '.');
      if (p.devise && p.devise !== 'EUR') L['Argent'].push(E(p.nom) + ' : ' + E(p.monnaie || p.devise) + (p.taux ? ' (1 € ≈ ' + String(Math.round(p.taux * 100) / 100).replace('.', ',') + ' ' + E(p.devise) + ')' : '') + '. Prévenez votre banque de votre voyage.');
      if (p.urgences && p.urgences.length) L['Santé et sécurité'].push(E(p.nom) + ' : numéros d’urgence ' + E(p.urgences.join(' · ')) + '.');
      if (p.secu >= 2) L['Santé et sécurité'].push(E(p.nom) + ' : niveau de sécurité ' + p.secu + ' sur 4. Lisez les Conseils aux voyageurs avant de partir.');
    });
    L['Papiers'].push('Passeport ou carte d’identité valides (souvent 6 mois après le retour hors Union européenne).', 'Assurance voyage et rapatriement, avec l’attestation (voir <a href="' + root + 'assurance/">notre guide</a>).', 'Copies numériques des papiers, envoyées à vous-même.');
    if (Object.keys(pays).some(function (cc) { return ['FR', 'BE', 'CH', 'DE', 'IT', 'ES', 'PT', 'NL', 'AT', 'LU'].indexOf(cc) < 0; })) L['Papiers'].push('Permis de conduire international si vous louez une voiture hors d’Europe.');
    L['Argent'].push('Une carte bancaire de secours, rangée à part.', 'Un peu d’argent liquide pour l’arrivée.');
    if (tmax >= 26) L['Valise'].push('Vêtements légers, chapeau, lunettes de soleil, crème solaire (jusqu’à ' + tmax + ' °C).');
    if (tmin <= 12) L['Valise'].push('Pull et veste chaude (minimales autour de ' + tmin + ' °C).');
    if (tmin <= 2) L['Valise'].push('Manteau d’hiver, bonnet, gants : il peut geler.');
    if (pluie >= 80) L['Valise'].push('Imperméable ou parapluie : jusqu’à ' + pluie + ' mm de pluie dans le mois.');
    if (villes.some(function (v) { return v.plage; })) L['Valise'].push('Maillot de bain, serviette de plage.');
    if (villes.some(function (v) { return v.nature > 5; })) L['Valise'].push('Chaussures de marche, gourde.');
    Object.keys(pays).forEach(function (cc) {
      var p = m.pays[cc] || {};
      if (p.prises && p.prises.length) L['Valise'].push(E(p.nom) + ' : prises de type ' + E(p.prises.join(', ')) + (p.prises.every(function (x) { return 'CEF'.indexOf(x) > -1; }) ? ' (vos prises françaises conviennent)' : ' : <b>adaptateur nécessaire</b>') + '.');
      if (p.conduite === 'gauche') L['Papiers'].push(E(p.nom) + ' : on y conduit à gauche.');
    });
    L['Valise'].push('Chargeurs et batterie externe.');
    // Trousse à pharmacie : liste générale, à valider avec un médecin ou un pharmacien
    var T = L['Trousse à pharmacie'] = ['Vos traitements habituels en quantité suffisante, dans leur boîte, avec l’ordonnance.',
      'Pansements, compresses stériles, désinfectant, sparadrap.', 'Antidouleur et contre la fièvre adaptés à chacun (demandez conseil à votre pharmacien).',
      'Sels de réhydratation orale, en cas de diarrhée ou de forte chaleur.', 'Thermomètre, pince à épiler ou à tiques, petits ciseaux.',
      'Crème solaire et produit contre les coups de soleil.', 'Gel hydroalcoolique.'];
    var palu = Object.keys(pays).some(function (cc) { return (m.pays[cc] || {}).palu; }), dengue = Object.keys(pays).some(function (cc) { return (m.pays[cc] || {}).dengue; });
    if (palu || dengue) T.push('Répulsif anti-moustiques pour la peau et vêtements longs le soir' + (dengue ? ' (dengue ou autres maladies transmises par les moustiques signalées)' : '') + '.');
    if (palu) T.push('<b>Paludisme signalé dans au moins un des pays</b> : demandez à votre médecin s’il faut un traitement préventif, à commencer avant le départ.');
    if (tmax >= 30) T.push('Chapeau et de quoi bien s’hydrater : fortes chaleurs attendues.');
    T.push('<small>Liste indicative : faites-la valider par votre médecin ou votre pharmacien selon votre santé et votre destination.</small>');
    L['Santé et sécurité'].push('Vaccins et traitements conseillés : consultez votre médecin ou un centre de vaccinations internationales (Institut Pasteur) 4 à 6 semaines avant le départ.',
      'Inscrivez-vous sur le service Ariane du ministère des Affaires étrangères.', 'Trousse de premiers soins et médicaments habituels.');
    return L;
  }
  return { root: root, MOIS: MOIS, E: E, nb: nb, norm: norm, dist: dist, lireJson: lireJson, chargerMonde: chargerMonde, chargerIndex: chargerIndex,
    choixVille: choixVille, trajet: trajet, duree: duree, climat: climat, carnet: carnet, garder: garder, carnetVille: carnetVille,
    preparation: preparation, ville: function (s) { return parSlug && parSlug[s]; } };
})();
