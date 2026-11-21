/* Dix Mille Escales – carte interactive des lieux d'une ville.
   Chargée seulement quand on clique sur « Ouvrir la carte interactive » (la bibliothèque pèse environ 800 Ko).
   Fond de carte gratuit et sans inscription : OpenFreeMap (données © contributeurs OpenStreetMap).
   Points regroupés quand ils sont nombreux, couleur par rubrique, fiche du lieu au clic. */
(function () {
  var VERSION = '4.7.1';
  var LIB = 'https://cdn.jsdelivr.net/npm/maplibre-gl@' + VERSION + '/dist/maplibre-gl.js';
  var CSS = 'https://cdn.jsdelivr.net/npm/maplibre-gl@' + VERSION + '/dist/maplibre-gl.css';
  var STYLE = 'https://tiles.openfreemap.org/styles/liberty';
  var COUL = { voir: '#2F7D6D', manger: '#B5485D', dormir: '#2E6DB4', faire: '#C9761E', acheter: '#7B5EA7', alentours: '#4E7D3A', bouger: '#56707A' };
  var NOMS = { voir: 'À voir', manger: 'Manger et boire', dormir: 'Dormir', faire: 'Activités', acheter: 'Acheter', alentours: 'Aux alentours', bouger: 'Se déplacer' };
  var charge = null;
  function E(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function lireJson(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); }).then(function (b) {
      var o = new Uint8Array(b);
      if (o[0] === 0x1f && o[1] === 0x8b) return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
      return JSON.parse(new TextDecoder().decode(o));
    });
  }
  function bibliotheque() {
    if (charge) return charge;
    charge = new Promise(function (ok, ko) {
      var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = CSS; document.head.appendChild(l);
      var s = document.createElement('script'); s.src = LIB; s.onload = ok; s.onerror = ko; document.head.appendChild(s);
    });
    return charge;
  }
  function ouvrir(zone) {
    var btn = zone.querySelector('.carte-ouvrir');
    btn.disabled = true; btn.textContent = 'Chargement de la carte…';
    var root = document.body.getAttribute('data-root') || '../../';
    var slug = location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '').split('/').pop();
    Promise.all([bibliotheque(), lireJson(root + 'villes/' + slug + '/lieux.json.gz')]).then(function (r) {
      var lieux = (r[1].lieux || []).filter(function (f) { return f.lat != null && f.lon != null; });
      var boite = document.createElement('div');
      boite.style.cssText = 'height:min(70vh,560px);border-radius:14px;overflow:hidden;border:1px solid var(--line);margin-top:.8rem';
      zone.innerHTML = ''; zone.appendChild(boite);
      var leg = document.createElement('p'); leg.className = 'legend';
      leg.innerHTML = Object.keys(NOMS).map(function (k) { return '<span style="--c:' + COUL[k] + '">' + NOMS[k] + '</span>'; }).join('') + '<span style="--c:transparent">Fond de carte : OpenFreeMap, © contributeurs OpenStreetMap</span>';
      zone.appendChild(leg);
      var lat = +zone.getAttribute('data-lat'), lon = +zone.getAttribute('data-lon'), rayon = +zone.getAttribute('data-rayon') || 3;
      var carte = new maplibregl.Map({ container: boite, style: STYLE, center: [lon, lat], zoom: rayon > 8 ? 11 : rayon > 4 ? 12 : 13, attributionControl: { compact: true } });
      carte.addControl(new maplibregl.NavigationControl(), 'top-right');
      carte.addControl(new maplibregl.FullscreenControl(), 'top-right');
      carte.on('load', function () {
        carte.addSource('lieux', { type: 'geojson', cluster: true, clusterRadius: 45, clusterMaxZoom: 15,
          data: { type: 'FeatureCollection', features: lieux.map(function (f, i) { return { type: 'Feature', geometry: { type: 'Point', coordinates: [f.lon, f.lat] }, properties: { i: i, r: f.rubrique } }; }) } });
        carte.addLayer({ id: 'groupes', type: 'circle', source: 'lieux', filter: ['has', 'point_count'],
          paint: { 'circle-color': '#12313B', 'circle-opacity': 0.85, 'circle-radius': ['step', ['get', 'point_count'], 14, 20, 18, 100, 24, 500, 30], 'circle-stroke-color': '#F2B705', 'circle-stroke-width': 2 } });
        carte.addLayer({ id: 'nombres', type: 'symbol', source: 'lieux', filter: ['has', 'point_count'],
          layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12, 'text-font': ['Noto Sans Bold'] }, paint: { 'text-color': '#ffffff' } });
        carte.addLayer({ id: 'points', type: 'circle', source: 'lieux', filter: ['!', ['has', 'point_count']],
          paint: { 'circle-radius': 7, 'circle-stroke-width': 2, 'circle-stroke-color': '#ffffff',
            'circle-color': ['match', ['get', 'r'], 'voir', COUL.voir, 'manger', COUL.manger, 'dormir', COUL.dormir, 'faire', COUL.faire, 'acheter', COUL.acheter, 'alentours', COUL.alentours, COUL.bouger] } });
        carte.on('click', 'groupes', function (e) {
          var f = e.features[0];
          carte.getSource('lieux').getClusterExpansionZoom(f.properties.cluster_id).then(function (z) { carte.easeTo({ center: f.geometry.coordinates, zoom: z }); });
        });
        carte.on('click', 'points', function (e) {
          var f = lieux[e.features[0].properties.i];
          new maplibregl.Popup({ maxWidth: '280px' }).setLngLat(e.features[0].geometry.coordinates)
            .setHTML('<b>' + E(f.nom) + '</b><br>' + E([f.type, f.cuisine].filter(Boolean).join(' · ')) + (f.adresse ? '<br>' + E(f.adresse) : '') + (f.horaires ? '<br>Horaires : ' + E(f.horaires) : '')
              + (f.site && /^https?:/.test(f.site) ? '<br><a href="' + E(f.site) + '" target="_blank" rel="noopener nofollow">Site</a>' : ''))
            .addTo(carte);
        });
        ['groupes', 'points'].forEach(function (c) { carte.on('mouseenter', c, function () { carte.getCanvas().style.cursor = 'pointer'; }); carte.on('mouseleave', c, function () { carte.getCanvas().style.cursor = ''; }); });
      });
    }).catch(function () {
      btn.disabled = false; btn.textContent = 'La carte n’a pas pu se charger : réessayer';
    });
  }
  function lier(scope) {
    (scope || document).querySelectorAll('.carte-zone .carte-ouvrir').forEach(function (b) {
      if (b.dataset.lie) return; b.dataset.lie = '1';
      b.addEventListener('click', function () { ouvrir(b.closest('.carte-zone')); });
    });
  }
  window.DME_lierCarte = lier;
  lier(document);
})();
