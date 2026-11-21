/* Dix Mille Escales – bloc « données des robots » pour les fiches rédigées à la main.
   Affiche, sous le contenu rédigé, la météo, tous les lieux et adresses et les sites des alentours
   collectés chaque nuit, à partir des fichiers donnees.json et lieux.json de la ville. */
(function () {
  var zone = document.getElementById('donnees-robots');
  if (!zone) return;
  var root = zone.getAttribute('data-root') || '../../';
  var slug = location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '').split('/').pop();
  var RUB = [['manger', 'Manger et boire'], ['dormir', 'Dormir'], ['voir', 'À voir'], ['faire', 'Activités'], ['acheter', 'Acheter'], ['bouger', 'Se déplacer'], ['alentours', 'Aux alentours']];
  var COUL = { manger: '#B5485D', dormir: '#2E6DB4', voir: '#2F7D6D', faire: '#C9761E', acheter: '#7B5EA7', alentours: '#4E7D3A', bouger: '#56707A' };
  var JOURS = { Mo: 'lun', Tu: 'mar', We: 'mer', Th: 'jeu', Fr: 'ven', Sa: 'sam', Su: 'dim', PH: 'fériés', off: 'fermé' };
  function lireJson(url) {  // fichiers .json.gz : décompressés dans le navigateur
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); }).then(function (b) {
      var o = new Uint8Array(b);
      if (o[0] === 0x1f && o[1] === 0x8b) {
        if (!('DecompressionStream' in window)) throw new Error('navigateur trop ancien');
        return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
      }
      return JSON.parse(new TextDecoder().decode(o));
    });
  }
  function E(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function nb(n) { return new Intl.NumberFormat('fr-FR').format(n); }
  function norm(t) { return (t || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }
  function hfr(h) { Object.keys(JOURS).forEach(function (k) { h = h.split(k).join(JOURS[k]); }); return h.replace(/;/g, ' ; '); }

  var css = document.createElement('style');
  css.textContent = '#donnees-robots{margin:3.6rem 0}#donnees-robots h2{font-family:var(--display,system-ui);font-weight:800;font-size:clamp(1.7rem,3.4vw,2.4rem);letter-spacing:-.025em;line-height:1.1;margin:0 0 .8rem}'
    + '.dr-lead{max-width:70ch;margin:0 0 1rem}.dr-meteo{display:grid;grid-template-columns:repeat(7,minmax(84px,1fr));gap:.5rem;overflow-x:auto;margin:0 0 2rem}'
    + '.dr-meteo div{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:.6rem;text-align:center;font-family:var(--display,system-ui);font-size:.85rem}.dr-meteo b{display:block;font-size:1.2rem}'
    + '.dr-outils{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin:0 0 .8rem}.dr-outils input{flex:1 1 220px;min-width:0;font-family:var(--display,system-ui);font-size:.95rem;padding:.45rem .8rem;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--ink)}'
    + '.dr-chip{font-family:var(--display,system-ui);font-size:.86rem;padding:.32rem .8rem;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}.dr-chip[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}'
    + '.dr-liste{list-style:none;margin:0;padding:0;columns:2 320px;column-gap:2rem}.dr-liste li{break-inside:avoid;border-left:3px solid var(--c);padding:.55rem 0 .55rem .8rem;margin-bottom:.35rem}'
    + '.dr-liste h3{font-family:var(--display,system-ui);font-weight:600;font-size:1.02rem;margin:0}.dr-m{font-family:var(--display,system-ui);font-size:.84rem;color:var(--muted)}.dr-i{font-size:.92rem}.dr-i a{font-family:var(--display,system-ui);font-size:.84rem}'
    + '.dr-plus{font-family:var(--display,system-ui);font-weight:600;padding:.6rem 1rem;border-radius:10px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer;margin-top:.6rem}'
    + '.dr-note{font-size:.9rem;color:var(--muted);font-style:italic}';
  document.head.appendChild(css);

  function lieu(f) {
    var meta = [f.type, f.cuisine, f.etoiles ? f.etoiles + ' étoiles' : '', f.payant === 'oui' ? 'payant' : f.payant === 'non' ? 'gratuit' : '', f.fauteuil === 'oui' ? 'accessible en fauteuil' : '', f.terrasse === 'oui' ? 'terrasse' : '',
      f.distance_km && f.rubrique === 'alentours' ? String(f.distance_km).replace('.', ',') + ' km ' + (f.direction || '') : '', f.patrimoine_mondial ? 'patrimoine mondial' : ''].filter(Boolean).join(' · ');
    var liens = [];
    if (f.site && /^https?:/.test(f.site)) liens.push('<a href="' + E(f.site) + '" rel="nofollow noopener" target="_blank">Site</a>');
    if (f.telephone) liens.push('<a href="tel:' + E(f.telephone.replace(/\s/g, '')) + '">' + E(f.telephone) + '</a>');
    if (f.id) { var p = f.id.slice(4).split('/'); liens.push('<a href="https://www.openstreetmap.org/' + p[0] + '/' + p[1] + '" rel="nofollow noopener" target="_blank">Carte</a>'); }
    return '<li style="--c:' + COUL[f.rubrique] + '"><h3>' + E(f.nom) + '</h3><div class="dr-m">' + E(meta) + '</div>'
      + (f.adresse ? '<div class="dr-i">' + E(f.adresse) + '</div>' : '') + (f.horaires ? '<div class="dr-i">Horaires : ' + E(hfr(f.horaires)) + '</div>' : '')
      + '<div class="dr-i">' + liens.join(' · ') + '</div></li>';
  }

  Promise.all([
    lireJson(root + 'villes/' + slug + '/donnees.json.gz').catch(function () { return null; }),
    lireJson(root + 'villes/' + slug + '/lieux.json.gz').catch(function () { return null; })
  ]).then(function (res) {
    var d = res[0], L = res[1], h = '<h2>Mis à jour chaque nuit par nos robots</h2>';
    if (d && d.meteo) {
      h += '<p class="dr-lead">Météo des 7 prochains jours' + (d.air ? ', qualité de l’air ' + E(d.air.qualite) + ' (indice ' + d.air.indice + ')' : '') + '.</p><div class="dr-meteo">'
        + d.meteo.map(function (j) { return '<div>' + E(j.date.slice(8, 10) + '/' + j.date.slice(5, 7)) + '<br>' + E(j.ciel) + '<b>' + Math.round(j.max) + '°</b>' + Math.round(j.min) + '°</div>'; }).join('') + '</div>';
    }
    if (!L || !L.lieux || !L.lieux.length) {
      zone.innerHTML = h + '<p class="dr-lead">Les robots n’ont pas encore exploré la ville : restaurants, hôtels, lieux, activités et sites des alentours apparaîtront ici après leur premier passage.</p>';
      return;
    }
    var tous = L.lieux, cur = '', filtre = '', vus = 60;
    var cpt = {}; tous.forEach(function (f) { cpt[f.rubrique] = (cpt[f.rubrique] || 0) + 1; });
    h += '<p class="dr-lead"><b>' + nb(tous.length) + ' lieux et adresses</b> recensés : dans un rayon de ' + String(L.rayon_km).replace('.', ',') + ' km autour du centre, et les sites notables à moins de ' + L.rayon_alentours_km + ' km. Données vérifiées le ' + E(L.date.slice(8, 10) + '/' + L.date.slice(5, 7) + '/' + L.date.slice(0, 4)) + '.</p>'
      + '<div class="dr-outils"><label class="vh" for="dr-q" style="position:absolute;left:-9999px">Chercher une adresse</label><input id="dr-q" type="search" placeholder="Chercher un nom, une rue, une cuisine…">'
      + '<button type="button" class="dr-chip" data-r="" aria-pressed="true">Tout (' + nb(tous.length) + ')</button>'
      + RUB.filter(function (r) { return cpt[r[0]]; }).map(function (r) { return '<button type="button" class="dr-chip" data-r="' + r[0] + '" aria-pressed="false">' + r[1] + ' (' + nb(cpt[r[0]]) + ')</button>'; }).join('')
      + '</div><ul class="dr-liste"></ul><button type="button" class="dr-plus" hidden>Afficher plus</button>'
      + '<p class="dr-note">Source : © contributeurs OpenStreetMap (ODbL). Horaires et adresses vérifiés automatiquement chaque semaine pour les villes phares.</p>';
    zone.innerHTML = h;
    var ul = zone.querySelector('.dr-liste'), plus = zone.querySelector('.dr-plus');
    function rendre() {
      var q = norm(filtre), l = tous.filter(function (f) { return (!cur || f.rubrique === cur) && (!q || norm(f.nom + ' ' + (f.adresse || '') + ' ' + (f.cuisine || '') + ' ' + f.type).indexOf(q) > -1); });
      ul.innerHTML = l.slice(0, vus).map(lieu).join('') || '<li style="border:0">Aucune adresse ne correspond.</li>';
      plus.hidden = l.length <= vus; plus.textContent = 'Afficher plus (' + nb(l.length - vus) + ' restants)';
    }
    zone.querySelectorAll('.dr-chip').forEach(function (b) { b.addEventListener('click', function () { cur = b.getAttribute('data-r'); vus = 60; zone.querySelectorAll('.dr-chip').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); }); rendre(); }); });
    zone.querySelector('#dr-q').addEventListener('input', function (e) { filtre = e.target.value; vus = 60; rendre(); });
    plus.addEventListener('click', function () { vus += 120; rendre(); });
    rendre();
    var toc = document.querySelector('.toc ol');
    if (toc) { var li = document.createElement('li'); li.innerHTML = '<a href="#donnees-robots">Toutes les adresses</a>'; toc.appendChild(li); }
  });
})();
