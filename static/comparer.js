/* Dix Mille Escales – comparateur : deux à quatre villes côte à côte. */
(function () {
  var D = window.DME, E = D.E, f = document.getElementById('cmp');
  if (!f) return;
  var choisies = [], res = document.getElementById('cmp-res');
  function rendre() {
    var ul = f.querySelector('#cmp-villes');
    ul.innerHTML = choisies.map(function (s, i) { var v = D.ville(s); return '<li>' + E(v ? v.nom : s) + ' <button type="button" data-i="' + i + '">✕</button></li>'; }).join('') || '<li class="o-vide">Choisissez deux à quatre villes.</li>';
    ul.querySelectorAll('button').forEach(function (b) { b.onclick = function () { choisies.splice(+b.getAttribute('data-i'), 1); rendre(); comparer(); }; });
  }
  D.choixVille(f.querySelector('#cmp-q'), function (s) { if (choisies.indexOf(s) < 0 && choisies.length < 4) choisies.push(s); rendre(); comparer(); });
  function comparer() {
    if (choisies.length < 2) { res.innerHTML = ''; return; }
    var m = +f.querySelector('#cmp-mois').value;
    D.chargerMonde().then(function (M) {
      var vs = choisies.map(D.ville).filter(Boolean);
      Promise.all(vs.map(function (v) { return D.lireJson(D.root + 'villes/' + v.slug + '/donnees.json.gz').catch(function () { return {}; }); })).then(function (ds) {
        var paris = { lat: 48.857, lon: 2.352 };
        var lignes = [
          ['Pays', function (v) { return E((M.pays[v.cc] || {}).nom); }],
          ['Habitants', function (v) { return D.nb(v.pop); }],
          ['Climat en ' + D.MOIS[m], function (v) { var c = D.climat(v, m); return E(c.texte) + (c.alerte ? '<br><b>' + E(c.alerte) + '</b>' : ''); }],
          ['Budget par jour (moyen)', function (v, d) { return d.cout ? '≈ ' + d.cout.prix['budget par jour (moyen)'] + ' €' : '–'; }],
          ['Visa (passeport français)', function (v) { return E(((M.pays[v.cc] || {}).visa || {})['Passeport français'] || '–'); }],
          ['Sécurité', function (v) { var s = (M.pays[v.cc] || {}).secu; return s ? s + ' sur 4' : '–'; }],
          ['Lieux à voir', function (v) { return D.nb(v.voir); }], ['Restaurants, cafés, bars', function (v) { return D.nb(v.manger); }],
          ['Hébergements', function (v) { return D.nb(v.dormir); }], ['Activités', function (v) { return D.nb(v.faire); }],
          ['Plage', function (v) { return v.plage ? 'oui' : 'non'; }],
          ['Patrimoine mondial', function (v, d) { return d.unesco && d.unesco.length ? E(d.unesco.slice(0, 2).join(', ')) + (d.unesco.length > 2 ? '…' : '') : 'non'; }],
          ['Aéroport le plus proche', function (v) { return v.aero ? E(v.aero[0]) + ', ' + v.aero[1] + ' km' : '–'; }],
          ['Depuis Paris', function (v) { return D.nb(D.dist(paris, v)) + ' km'; }],
          ['Langue', function (v) { return E(((M.pays[v.cc] || {}).langues || []).slice(0, 2).join(', ')); }],
          ['Monnaie', function (v) { return E((M.pays[v.cc] || {}).monnaie || ''); }],
          ['Meilleurs mois', function (v, d) { return E((d.meilleurs_mois || []).join(', ') || '–'); }]
        ];
        res.innerHTML = '<div class="table-scroll"><table class="o-cmp"><thead><tr><th></th>' + vs.map(function (v) { return '<th><a href="' + D.root + 'villes/' + v.slug + '/">' + E(v.nom) + '</a></th>'; }).join('') + '</tr></thead><tbody>'
          + lignes.map(function (l) { return '<tr><td>' + l[0] + '</td>' + vs.map(function (v, i) { return '<td>' + l[1](v, ds[i] || {}) + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table></div>';
      });
    });
  }
  f.querySelector('#cmp-mois').innerHTML = D.MOIS.map(function (x, i) { return '<option value="' + i + '">' + x.charAt(0).toUpperCase() + x.slice(1) + '</option>'; }).join('');
  f.querySelector('#cmp-mois').value = String(new Date().getMonth());
  f.querySelector('#cmp-mois').onchange = comparer;
  var h = new URLSearchParams(location.hash.slice(1));
  D.chargerMonde().then(function () { if (h.get('v')) choisies = h.get('v').split(',').filter(D.ville).slice(0, 4); rendre(); comparer(); });
})();
