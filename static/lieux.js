/* Dix Mille Escales – listes complètes d'adresses, chargées à la demande sur les fiches automatiques.
   La page ne contient que les meilleures adresses ; le bouton « Voir les … adresses » charge toutes les autres
   depuis le fichier compressé lieux.json.gz de la ville, avec une recherche. */
(function () {
  var root = document.body.getAttribute('data-root') || '';
  var slug = location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '').split('/').pop();
  var donnees = null;
  var JOURS = { Mo: 'lun', Tu: 'mar', We: 'mer', Th: 'jeu', Fr: 'ven', Sa: 'sam', Su: 'dim', PH: 'jours fériés', off: 'fermé' };
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
  function norm(t) { return (t || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }
  function hfr(h) { Object.keys(JOURS).forEach(function (k) { h = h.split(k).join(JOURS[k]); }); return h.replace(/;/g, ' ; '); }
  function item(f) {
    var meta = [(f.wikidata || f.patrimoine_mondial) ? '★ incontournable' : '', f.type, f.cuisine, f.etoiles ? f.etoiles + ' étoiles' : '', f.payant === 'oui' ? 'payant' : f.payant === 'non' ? 'gratuit' : '',
      f.fauteuil === 'oui' ? 'accessible en fauteuil' : '', f.terrasse === 'oui' ? 'terrasse' : '',
      f.rubrique === 'alentours' && f.distance_km ? String(f.distance_km).replace('.', ',') + ' km ' + (f.direction || '') : '',
      f.patrimoine_mondial ? 'patrimoine mondial' : '', f.urgences === 'oui' ? 'service d’urgences' : ''].filter(Boolean).join(' · ');
    var liens = [];
    if (f.site && /^https?:/.test(f.site)) liens.push('<a href="' + E(f.site) + '" rel="nofollow noopener" target="_blank">Site</a>');
    if (f.telephone) liens.push('<a href="tel:' + E(f.telephone.replace(/\s/g, '')) + '">' + E(f.telephone) + '</a>');
    if (f.id) { var p = f.id.slice(4).split('/'); liens.push('<a href="https://www.openstreetmap.org/' + p[0] + '/' + p[1] + '" rel="nofollow noopener" target="_blank">Carte</a>'); }
    return '<li data-type="' + E(f.type) + '" style="--c:var(--' + f.rubrique + ')"><h3>' + E(f.nom) + '</h3><div class="m">' + E(meta) + '</div>'
      + (f.adresse ? '<div class="i">' + E(f.adresse) + '</div>' : '') + (f.horaires ? '<div class="i">Horaires : ' + E(hfr(f.horaires)) + '</div>' : '')
      + '<div class="i">' + liens.join(' · ') + '</div></li>';
  }
  function lier(scope) {
  scope.querySelectorAll('.tout-voir[data-rub]').forEach(function (b) {
    if (b.dataset.lie) return; b.dataset.lie = '1';
    b.addEventListener('click', function () {
      var rub = b.getAttribute('data-rub'), section = b.closest('section'), ul = section.querySelector('ul.places');
      b.disabled = true; b.textContent = 'Chargement…';
      (donnees ? Promise.resolve(donnees) : lireJson(root + 'villes/' + slug + '/lieux.json.gz')).then(function (d) {
        donnees = d;
        var tous = d.lieux.filter(function (f) { return f.rubrique === rub; }).sort(function (x, y) { return ((y.wikidata || y.patrimoine_mondial) ? 1 : 0) - ((x.wikidata || x.patrimoine_mondial) ? 1 : 0); }), vus = 120, filtre = '', type = '';
        var outils = document.createElement('div');
        outils.className = 'chips';
        var types = {}; tous.forEach(function (f) { types[f.type] = (types[f.type] || 0) + 1; });
        outils.innerHTML = '<input type="search" class="recherche-lieux" placeholder="Chercher un nom, une rue, une cuisine…" aria-label="Chercher une adresse">'
          + '<button type="button" class="chip" data-t="" aria-pressed="true">Tout (' + tous.length + ')</button>'
          + Object.keys(types).sort(function (x, y) { return types[y] - types[x]; }).slice(0, 10).map(function (t) {
            return '<button type="button" class="chip" data-t="' + E(t) + '" aria-pressed="false">' + E(t) + ' (' + types[t] + ')</button>'; }).join('');
        ul.parentNode.insertBefore(outils, ul);
        var plus = document.createElement('button'); plus.type = 'button'; plus.className = 'tout-voir';
        function rendre() {
          var q = norm(filtre), l = tous.filter(function (f) { return (!type || f.type === type) && (!q || norm(f.nom + ' ' + (f.adresse || '') + ' ' + (f.cuisine || '') + ' ' + f.type).indexOf(q) > -1); });
          ul.innerHTML = l.slice(0, vus).map(item).join('') || '<li>Aucune adresse ne correspond.</li>';
          plus.hidden = l.length <= vus; plus.textContent = 'Afficher plus (' + (l.length - vus) + ' restantes)';
        }
        outils.querySelector('input').addEventListener('input', function (e) { filtre = e.target.value; vus = 120; rendre(); });
        outils.querySelectorAll('.chip').forEach(function (c) { c.addEventListener('click', function () { type = c.getAttribute('data-t'); vus = 120;
          outils.querySelectorAll('.chip').forEach(function (x) { x.setAttribute('aria-pressed', x === c ? 'true' : 'false'); }); rendre(); }); });
        plus.addEventListener('click', function () { vus += 240; rendre(); });
        b.replaceWith(plus);
        rendre();
      }).catch(function () { b.disabled = false; b.textContent = 'Chargement impossible, réessayer'; });
    });
  });
  }
  window.DME_lierBoutons = lier;
  lier(document);
})();
