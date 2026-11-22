/* Dix Mille Escales – « Où partir en… » : les meilleures villes du monde pour un mois et des envies données. */
(function () {
  var D = window.DME, E = D.E, f = document.getElementById('op');
  if (!f) return;
  var res = document.getElementById('op-res');
  f.querySelector('#op-mois').innerHTML = D.MOIS.map(function (m, i) { return '<option value="' + i + '">' + m.charAt(0).toUpperCase() + m.slice(1) + '</option>'; }).join('');
  f.querySelector('#op-mois').value = String((new Date().getMonth() + 1) % 12);
  function chercher(e) {
    if (e) e.preventDefault();
    res.innerHTML = '<p class="o-vide">Recherche parmi toutes les villes…</p>';
    D.chargerMonde().then(function (M) {
      var m = +f.querySelector('#op-mois').value, tmin = +f.querySelector('#op-tmin').value, tmax = +f.querySelector('#op-tmax').value;
      var pluieMax = +f.querySelector('#op-pluie').value, env = f.querySelector('#op-envie').value, cont = f.querySelector('#op-cont').value;
      var budget = f.querySelector('#op-budget').value, sansVisa = f.querySelector('#op-visa').checked, sur = f.querySelector('#op-sur').checked;
      var taille = f.querySelector('#op-taille').value, paris = { lat: 48.857, lon: 2.352 }, distMax = +f.querySelector('#op-dist').value;
      var l = M.villes.filter(function (v) {
        if (!v.tmax) return false;
        var p = M.pays[v.cc] || {}, tx = v.tmax[m];
        if (tx < tmin || tx > tmax || v.pluie[m] > pluieMax) return false;
        if (cont && p.cont !== cont) return false;
        if (env === 'plage' && !v.plage) return false;
        if (env === 'ski' && !v.ski) return false;
        if (env === 'culture' && v.culture < 5) return false;
        if (env === 'nature' && v.nature < 3) return false;
        if (budget === 'petit' && !(p.cout && p.cout < 0.6)) return false;
        if (budget === 'moyen' && !(p.cout && p.cout < 0.9)) return false;
        if (sansVisa) { var vi = (p.visa || {})['Passeport français'] || ''; if (!/Sans visa|Libre circulation|Ressortissants/.test(vi)) return false; }
        if (sur && p.secu > 2) return false;
        if (taille === 'grandes' && v.niveau === 2) return false;
        if (taille === 'petites' && v.niveau !== 2) return false;
        if (distMax && D.dist(paris, v) > distMax) return false;
        return true;
      });
      l.forEach(function (v) {  // score : douceur, sécheresse, richesse en lieux, notoriété
        var tx = v.tmax[m];
        v._s = -Math.abs(tx - 25) * 1.5 - v.pluie[m] / 25 + Math.log10(1 + v.voir + v.faire + v.manger) * 4 + [6, 3, 0][v.niveau] + (env && env !== 'tout' ? 2 : 0);
      });
      l.sort(function (a, b) { return b._s - a._s; });
      var vus = {}, tri = [];  // pas plus de 3 villes du même pays dans les 30 premières, pour varier
      l.forEach(function (v) { vus[v.cc] = (vus[v.cc] || 0) + 1; if (vus[v.cc] <= 3 || tri.length >= 30) tri.push(v); });
      res.innerHTML = '<p class="o-nb">' + D.nb(l.length) + ' ville' + (l.length > 1 ? 's' : '') + ' correspondent. Les 60 meilleures :</p>' + (tri.length ? '<ol class="o-liste">' + tri.slice(0, 60).map(function (v) {
        var p = M.pays[v.cc] || {};
        return '<li><a href="' + D.root + 'villes/' + v.slug + '/"><b>' + E(v.nom) + '</b> <span>' + E(p.nom || v.cc) + '</span></a>'
          + '<small>' + v.tmin[m] + ' à ' + v.tmax[m] + ' °C · ' + v.pluie[m] + ' mm de pluie' + (v.plage ? ' · plage' : '') + (p.cout ? ' · prix ' + Math.round(p.cout * 100) + ' % de la France' : '') + '</small>'
          + '<button type="button" class="o-ajout" data-s="' + v.slug + '">+ itinéraire</button></li>';
      }).join('') + '</ol>' : '<p class="o-vide">Aucune ville ne correspond : élargissez les températures ou la pluie.</p>');
      res.querySelectorAll('.o-ajout').forEach(function (b) { b.onclick = function () { var c = D.carnet(); c.brouillon = c.brouillon || []; if (c.brouillon.indexOf(b.getAttribute('data-s')) < 0) c.brouillon.push(b.getAttribute('data-s')); D.garder(c); b.textContent = 'ajoutée ✓'; }; });
    }).catch(function () { res.innerHTML = '<p class="o-alerte">Les données n’ont pas pu être chargées.</p>'; });
  }
  f.addEventListener('submit', chercher);
})();
