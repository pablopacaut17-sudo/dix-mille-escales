/* Dix Mille Escales – planificateur d'itinéraire multi-villes.
   Ordre optimal des étapes, répartition des jours, trajets (route, train ou avion), climat du mois,
   programme jour par jour tiré des fiches, budget, formalités et liste de préparation. Tout se calcule ici, sans serveur. */
(function () {
  var D = window.DME, E = D.E, f = document.getElementById('itin');
  if (!f) return;
  var choisies = [], res = document.getElementById('itin-res');
  var ENVIES = [['culture', 'Culture et monuments'], ['nature', 'Nature et randonnée'], ['plage', 'Plages'], ['gastronomie', 'Gastronomie'], ['ski', 'Ski et montagne'], ['detente', 'Rythme tranquille']];
  var BUDGET = { petit: 70, moyen: 150, confort: 300 };

  f.querySelector('#itin-envies').innerHTML = ENVIES.map(function (e) { return '<label class="o-coche"><input type="checkbox" value="' + e[0] + '"> ' + e[1] + '</label>'; }).join('');
  f.querySelector('#itin-mois').innerHTML = D.MOIS.map(function (m, i) { return '<option value="' + i + '">' + m.charAt(0).toUpperCase() + m.slice(1) + '</option>'; }).join('');
  f.querySelector('#itin-mois').value = String(new Date().getMonth());

  function afficherChoix() {
    var ul = f.querySelector('#itin-villes');
    ul.innerHTML = choisies.length ? choisies.map(function (s, i) {
      var v = D.ville(s); return '<li>' + (i === 0 && f.querySelector('#itin-depart').checked ? '<b>Départ :</b> ' : '') + E(v ? v.nom : s) + ' <button type="button" data-i="' + i + '" aria-label="Retirer ' + E(v ? v.nom : s) + '">✕</button></li>';
    }).join('') : '<li class="o-vide">Ajoutez au moins deux villes.</li>';
    ul.querySelectorAll('button').forEach(function (b) { b.onclick = function () { choisies.splice(+b.getAttribute('data-i'), 1); afficherChoix(); }; });
  }
  D.choixVille(f.querySelector('#itin-q'), function (slug) { if (choisies.indexOf(slug) < 0 && choisies.length < 15) choisies.push(slug); afficherChoix(); });
  f.querySelector('#itin-depart').onchange = afficherChoix;

  function ordonner(vs, fixe) {
    if (vs.length < 3) return vs.slice();
    var reste = vs.slice(), chemin = [fixe ? reste.shift() : reste.splice(0, 1)[0]];
    while (reste.length) {  // plus proche voisin
      var der = chemin[chemin.length - 1], k = 0;
      reste.forEach(function (v, i) { if (D.dist(der, v) < D.dist(der, reste[k])) k = i; });
      chemin.push(reste.splice(k, 1)[0]);
    }
    var mieux = true;  // améliorations 2-opt (la première étape reste fixe)
    function lg(c) { var s = 0; for (var i = 1; i < c.length; i++) s += D.dist(c[i - 1], c[i]); return s; }
    while (mieux) {
      mieux = false;
      for (var i = 1; i < chemin.length - 1; i++) for (var j = i + 1; j < chemin.length; j++) {
        var c = chemin.slice(0, i).concat(chemin.slice(i, j + 1).reverse(), chemin.slice(j + 1));
        if (lg(c) + 0.01 < lg(chemin)) { chemin = c; mieux = true; }
      }
    }
    return chemin;
  }

  function repartir(vs, jours, envies, legs) {
    var perdus = legs.reduce(function (s, t) { return s + (t.h > 5 ? 0.5 : 0); }, 0);
    var dispo = Math.max(vs.length, Math.round(jours - perdus));
    var w = vs.map(function (v) {
      var x = [3, 2, 1][v.niveau] + Math.log10(1 + v.voir + v.faire) / 1.5;
      if (envies.culture) x += Math.min(1.5, v.culture / 20);
      if (envies.nature) x += Math.min(1.5, v.nature / 8);
      if (envies.plage && v.plage) x += 1;
      if (envies.ski && v.ski) x += 1;
      if (envies.gastronomie) x += Math.min(1, v.manger / 400);
      return x;
    });
    var tot = w.reduce(function (a, b) { return a + b; }, 0), base = vs.map(function () { return 1; }), reste = dispo - vs.length;
    var parts = w.map(function (x) { return x / tot * reste; }), ent = parts.map(Math.floor);
    var r = reste - ent.reduce(function (a, b) { return a + b; }, 0);
    parts.map(function (p, i) { return [p - ent[i], i]; }).sort(function (a, b) { return b[0] - a[0]; }).slice(0, r).forEach(function (x) { ent[x[1]]++; });
    return base.map(function (b, i) { return b + ent[i]; });
  }

  function programme(v, d, n, envies) {
    if (!d) return [];
    var voir = (d.voir || []).slice(), faire = (d.faire || []).slice(), manger = (d.manger || []).slice(), autour = (d.alentours || []).slice();
    if (envies.nature) voir.sort(function (a, b) { return /Parc|Jardin|Belvédère/.test(b.type) - /Parc|Jardin|Belvédère/.test(a.type); });
    var jours = [];
    for (var i = 0; i < n; i++) {
      var etapes = [];
      if (i === 0) etapes.push('Arrivée et installation');
      var excursion = n >= 3 && i === n - 1 && autour.length && !envies.detente;
      if (excursion) {
        var x = autour.filter(function (a) { return a.patrimoine_mondial; })[0] || autour[0];
        autour.splice(autour.indexOf(x), 1);
        etapes.push('Excursion : <b>' + E(x.nom) + '</b> (' + E(x.type.toLowerCase()) + ', ' + String(x.km).replace('.', ',') + ' km ' + E(x.direction) + ')');
      } else {
        var k = envies.detente ? 2 : 3;
        for (var j = 0; j < k && (voir.length || faire.length); j++) {
          var it = (j === 2 && faire.length) ? faire.shift() : (voir.shift() || faire.shift());
          etapes.push('<b>' + E(it.nom) + '</b> (' + E(it.type.toLowerCase()) + ')');
        }
      }
      if (manger.length) { var m = manger.shift(); etapes.push('Repas : ' + E(m.nom) + (m.cuisine ? ' (cuisine ' + E(m.cuisine) + ')' : '')); }
      if (etapes.length <= (i === 0 ? 1 : 0)) etapes.push('Journée libre : flânez dans les quartiers et suivez les conseils de la fiche.');
      jours.push(etapes);
    }
    return jours;
  }

  function lien(etat) {
    return location.origin + location.pathname + '#v=' + etat.villes.join(',') + '&j=' + etat.jours + '&m=' + etat.mois + '&e=' + etat.envies.join(',') + '&b=' + etat.budget + '&p=' + encodeURIComponent(etat.passeport) + '&f=' + (etat.fixe ? 1 : 0) + '&n=' + etat.voyageurs;
  }

  function calculer(etat) {
    res.innerHTML = '<p class="o-vide">Calcul de l’itinéraire…</p>';
    D.chargerMonde().then(function (M) {
      var vs = etat.villes.map(D.ville).filter(Boolean);
      if (vs.length < 2) { res.innerHTML = '<p class="o-alerte">Ajoutez au moins deux villes.</p>'; return; }
      var envies = {}; etat.envies.forEach(function (e) { envies[e] = 1; });
      var ordre = ordonner(vs, etat.fixe), legs = [];
      for (var i = 1; i < ordre.length; i++) legs.push(D.trajet(ordre[i - 1], ordre[i]));
      var jours = repartir(ordre, etat.jours, envies, legs);
      return Promise.all(ordre.map(function (v) { return D.lireJson(D.root + 'villes/' + v.slug + '/donnees.json.gz').catch(function () { return null; }); })).then(function (fiches) {
        var h = '', km = legs.reduce(function (s, t) { return s + t.km; }, 0), jour = 1, budget = 0, transport = 0;
        var totalJ = jours.reduce(function (a, b) { return a + b; }, 0);
        h += '<div class="o-resume"><div><span>Étapes</span><b>' + ordre.length + '</b></div><div><span>Jours sur place</span><b>' + totalJ + '</b></div><div><span>Distance totale</span><b>' + D.nb(km) + ' km</b></div><div><span>Mois</span><b>' + D.MOIS[etat.mois] + '</b></div></div>';
        if (totalJ > etat.jours) h += '<p class="o-alerte">Avec ' + etat.jours + ' jours, le programme est serré : chaque étape garde au moins une journée. Retirez une ville ou ajoutez des jours.</p>';
        h += '<h2>Votre itinéraire</h2><ol class="o-etapes">';
        ordre.forEach(function (v, i) {
          var d = fiches[i], cl = D.climat(v, etat.mois), p = M.pays[v.cc] || {}, n = jours[i];
          var cout = (p.cout || 1) * BUDGET[etat.budget] * n * etat.voyageurs; budget += cout;
          var prog = programme(v, d, n, envies);
          h += '<li class="o-etape"><div class="o-tete"><h3><a href="' + D.root + 'villes/' + v.slug + '/">' + E(v.nom) + '</a> <small>' + E(p.nom || v.cc) + '</small></h3>'
            + '<p class="o-jours">Jour' + (n > 1 ? 's ' + jour + ' à ' + (jour + n - 1) : ' ' + jour) + ' · ' + n + ' jour' + (n > 1 ? 's' : '') + '</p></div>'
            + '<p class="o-climat' + (cl.alerte ? ' o-mauvais' : '') + '">' + D.MOIS[etat.mois].charAt(0).toUpperCase() + D.MOIS[etat.mois].slice(1) + ' : ' + E(cl.texte) + (cl.alerte ? ' · <b>Attention : ' + E(cl.alerte) + '</b>' : '') + '</p>'
            + '<ol class="o-prog">' + prog.map(function (j, k) { return '<li><b>Jour ' + (jour + k) + '</b><ul>' + j.map(function (x) { return '<li>' + x + '</li>'; }).join('') + '</ul></li>'; }).join('') + '</ol>'
            + (d && d.avis && d.avis.conseils ? '<p class="o-conseil">Conseil : ' + E(d.avis.conseils[0]) + '</p>' : '')
            + '</li>';
          jour += n;
          if (i < legs.length) {
            var t = legs[i], prix = t.mode === 'avion' ? Math.max(60, t.km * 0.11) : t.km * 0.07; transport += prix * etat.voyageurs;
            h += '<li class="o-trajet">' + (t.mode === 'avion' ? '✈' : '→') + ' <b>' + E(t.mode.charAt(0).toUpperCase() + t.mode.slice(1)) + '</b> vers ' + E(ordre[i + 1].nom) + ' : ' + D.nb(t.km) + ' km, ≈ ' + D.duree(t.h) + (t.detail ? ' (' + E(t.detail) + ')' : '') + '</li>';
          }
        });
        h += '</ol>';
        // Budget
        h += '<h2>Budget estimé</h2><div class="table-scroll"><table><tbody><tr><td>Séjour sur place (' + etat.voyageurs + ' pers., budget ' + E(etat.budget) + ')</td><td class="num">≈ ' + D.nb(budget) + ' €</td></tr>'
          + '<tr><td>Trajets entre les étapes</td><td class="num">≈ ' + D.nb(transport) + ' €</td></tr><tr><td><b>Total, hors voyage aller et retour</b></td><td class="num"><b>≈ ' + D.nb(budget + transport) + ' €</b></td></tr></tbody></table></div>'
          + '<p class="note">Estimation tirée du niveau des prix de chaque pays (Banque mondiale) ; billets d’avion et de train à vérifier au moment de réserver.</p>';
        // Préparation
        var prep = D.preparation(ordre, etat.mois, etat.passeport);
        h += '<h2>Préparer le départ</h2><div class="o-prep">' + Object.keys(prep).map(function (k) { return '<div><h3>' + E(k) + '</h3><ul class="o-cases">' + prep[k].map(function (x) { return '<li><label><input type="checkbox"> ' + x + '</label></li>'; }).join('') + '</ul></div>'; }).join('') + '</div>';
        h += '<div class="o-actions"><button type="button" id="itin-garder">Garder dans mon carnet</button><button type="button" id="itin-lien">Copier le lien</button><button type="button" onclick="window.print()">Imprimer</button></div><p class="note" id="itin-msg"></p>';
        res.innerHTML = h;
        var url = lien(etat);
        if (history.replaceState) history.replaceState(null, '', url.slice(url.indexOf('#')));
        document.getElementById('itin-lien').onclick = function () { (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function () { document.getElementById('itin-msg').textContent = 'Lien copié : vous pouvez le partager.'; }, function () { document.getElementById('itin-msg').textContent = url; }); };
        document.getElementById('itin-garder').onclick = function () {
          var c = D.carnet(); c.itineraires = c.itineraires || [];
          c.itineraires.unshift({ titre: ordre.map(function (v) { return v.nom; }).join(' · '), lien: url, date: new Date().toISOString().slice(0, 10), jours: totalJ });
          c.itineraires = c.itineraires.slice(0, 30); D.garder(c);
          document.getElementById('itin-msg').textContent = 'Itinéraire gardé dans votre carnet (sur cet appareil).';
        };
        res.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth' });
      });
    }).catch(function (e) { res.innerHTML = '<p class="o-alerte">Le calcul a échoué (' + E(e.message) + '). Réessayez dans un instant.</p>'; });
  }

  function etatForm() {
    return { villes: choisies.slice(), jours: Math.max(1, +f.querySelector('#itin-jours').value || 7), mois: +f.querySelector('#itin-mois').value,
      envies: Array.prototype.map.call(f.querySelectorAll('#itin-envies input:checked'), function (x) { return x.value; }),
      budget: f.querySelector('#itin-budget').value, passeport: f.querySelector('#itin-passeport').value, fixe: f.querySelector('#itin-depart').checked,
      voyageurs: Math.max(1, +f.querySelector('#itin-pers').value || 1) };
  }
  f.addEventListener('submit', function (e) { e.preventDefault(); calculer(etatForm()); });

  // Reprise : lien partagé, ou villes ajoutées depuis les fiches (« Ajouter à un itinéraire »)
  D.chargerMonde().then(function () {
    var h = new URLSearchParams(location.hash.slice(1));
    if (h.get('v')) {
      choisies = h.get('v').split(',').filter(D.ville);
      f.querySelector('#itin-jours').value = h.get('j') || 7; f.querySelector('#itin-mois').value = h.get('m') || 0;
      f.querySelector('#itin-budget').value = h.get('b') || 'moyen'; f.querySelector('#itin-pers').value = h.get('n') || 1;
      if (h.get('p')) f.querySelector('#itin-passeport').value = h.get('p');
      f.querySelector('#itin-depart').checked = h.get('f') === '1';
      (h.get('e') || '').split(',').forEach(function (e) { var x = f.querySelector('#itin-envies input[value="' + e + '"]'); if (x) x.checked = true; });
      afficherChoix(); calculer(etatForm());
    } else {
      var c = D.carnet(); if (c.brouillon && c.brouillon.length) { choisies = c.brouillon.filter(D.ville); c.brouillon = []; D.garder(c); }
      afficherChoix();
    }
  }).catch(function () { res.innerHTML = '<p class="o-alerte">Les données des villes n’ont pas pu être chargées.</p>'; });
})();
