/* Dix Mille Escales – comparateur de trajets entre deux villes : avion, train, bus, voiture.
   Estimations (durée, prix, CO₂) à partir de la distance ; liens pour chercher les vrais billets. Facteurs d'émission
   moyens par passager et par km, ordres de grandeur inspirés de la Base Empreinte de l'ADEME. */
(function () {
  var D = window.DME, E = D.E, f = document.getElementById('tj');
  if (!f) return;
  var A = null, B = null, res = document.getElementById('tj-res');
  function nom(v) { return v ? v.nom : ''; }
  function eur(a, b) { return '≈ ' + D.nb(a) + (b ? ' à ' + D.nb(b) : '') + ' €'; }
  function calc() {
    f.querySelector('#tj-a-v').textContent = A ? 'Départ : ' + A.nom : ''; f.querySelector('#tj-b-v').textContent = B ? 'Arrivée : ' + B.nom : '';
    if (!A || !B) { res.innerHTML = ''; return; }
    var M = D.chargerMonde, n = Math.max(1, +f.querySelector('#tj-n').value || 1), d = D.dist(A, B), dr = d * 1.2;
    D.chargerMonde().then(function (W) {
      var pa = W.pays[A.cc] || {}, pb = W.pays[B.cc] || {}, meme = pa.cont && pa.cont === pb.cont, modes = [];
      if (A.aero && B.aero && d > 250) {
        var co2a = d * 1.1 * (d < 1000 ? 0.26 : d < 3500 ? 0.19 : 0.15);
        var px = d < 1500 ? [50, 220] : d < 4000 ? [150, 550] : [450, 1300];
        modes.push({ m: 'Avion', h: 2.2 + d / 750 + (A.aero[1] + B.aero[1]) / 60, prix: eur(px[0] * n, px[1] * n), co2: co2a * n,
          note: 'Vol ' + E(A.aero[0]) + ' → ' + E(B.aero[0]) + ', avec l’accès aux aéroports et les formalités.',
          lien: 'https://www.google.com/travel/flights?q=' + encodeURIComponent('vols de ' + A.aero[0] + ' à ' + B.aero[0]), lienTxt: 'Chercher des vols' });
      }
      if (meme && d < 1600) modes.push({ m: 'Train', h: dr / 110 + 0.5, prix: eur(dr * 0.08 * n, dr * 0.2 * n), co2: dr * 0.03 * n,
        note: 'Si une ligne existe entre les deux villes ; le train à grande vitesse est plus rapide, les lignes classiques plus lentes.', lien: '', lienTxt: '' });
      if (meme && d < 2500) modes.push({ m: 'Bus', h: dr / 65 + 0.5, prix: eur(dr * 0.04 * n, dr * 0.09 * n), co2: dr * 0.03 * n,
        note: 'Souvent le moins cher ; pauses comprises dans l’estimation.', lien: '', lienTxt: '' });
      if (meme && d < 3500) {
        var carb = dr * 6.5 / 100 * 1.8;
        modes.push({ m: 'Voiture', h: d < 100 ? d * 1.3 / 60 : dr / 85, prix: eur(carb) + ' de carburant', co2: dr * 0.2,
          note: 'Pour tout le véhicule (jusqu’à 4 ou 5 personnes), hors péages et location. Conduite à ' + (pb.conduite || 'droite ?') + ' à l’arrivée.', lien: '', lienTxt: '' });
      }
      modes.sort(function (x, y) { return x.h - y.h; });
      var r2r = 'https://www.rome2rio.com/fr/map/' + encodeURIComponent(A.nom) + '/' + encodeURIComponent(B.nom);
      res.innerHTML = '<p class="o-nb">' + E(A.nom) + ' → ' + E(B.nom) + ' : ' + D.nb(d) + ' km à vol d’oiseau.</p>'
        + (modes.length ? '<div class="table-scroll"><table class="o-cmp"><thead><tr><th>Mode</th><th>Durée estimée</th><th>Prix estimé (' + n + ' pers.)</th><th>CO₂ estimé</th><th></th></tr></thead><tbody>'
          + modes.map(function (x, i) { return '<tr><td><b>' + x.m + '</b>' + (i === 0 ? ' <small>le plus rapide</small>' : '') + '<br><small>' + x.note + '</small></td><td>' + D.duree(x.h) + '</td><td>' + x.prix + '</td><td>' + D.nb(x.co2) + ' kg</td><td>' + (x.lien ? '<a href="' + x.lien + '" target="_blank" rel="noopener">' + x.lienTxt + '</a>' : '') + '</td></tr>'; }).join('')
          + '</tbody></table></div>' : '<p class="o-alerte">Aucun mode simple trouvé : pas d’aéroport proche ou destinations sur des continents différents.</p>')
        + '<p><a class="tout-voir" style="display:inline-block;text-decoration:none" href="' + r2r + '" target="_blank" rel="noopener">Voir les horaires et les billets réels sur Rome2Rio</a></p>'
        + '<p class="note">Estimations à partir de la distance : vérifiez toujours les horaires, l’existence des lignes et les prix au moment de réserver. Dix Mille Escales ne touche aucune commission sur ces liens.</p>';
    });
  }
  D.choixVille(f.querySelector('#tj-a'), function (s) { D.chargerMonde().then(function () { A = D.ville(s); calc(); }); });
  D.choixVille(f.querySelector('#tj-b'), function (s) { D.chargerMonde().then(function () { B = D.ville(s); calc(); }); });
  f.querySelector('#tj-n').oninput = calc;
  var h = new URLSearchParams(location.hash.slice(1));
  D.chargerMonde().then(function () { if (h.get('de')) A = D.ville(h.get('de')); if (h.get('a')) B = D.ville(h.get('a')); calc(); });
})();
