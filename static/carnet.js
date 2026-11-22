/* Dix Mille Escales – carnet de voyage (gardé sur l'appareil) : boutons sur les fiches, et page « Mon carnet ». */
(function () {
  function lire() { try { return JSON.parse(localStorage.getItem('dme-carnet') || '{}') || {}; } catch (e) { return {}; } }
  function garder(c) { try { localStorage.setItem('dme-carnet', JSON.stringify(c)); } catch (e) {} }
  function E(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var root = document.body.getAttribute('data-root') || '../../';

  // 1. Boutons sur une fiche de ville
  var h1 = document.querySelector('h1.city');
  if (h1 && /\/villes\//.test(location.pathname)) {
    var slug = location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '').split('/').pop();
    var nom = h1.textContent.replace(/Ville phare|Fiche complète/g, '').trim();
    var box = document.createElement('div'); box.className = 'carnet-btns';
    box.innerHTML = '<button type="button" class="carnet-garder"></button><button type="button" class="carnet-itin">Ajouter à un itinéraire</button><a href="' + root + 'comparer/#v=' + slug + '">Comparer</a>';
    h1.insertAdjacentElement('afterend', box);
    var bg = box.querySelector('.carnet-garder');
    function maj() { var c = lire(); var dedans = (c.villes || []).some(function (x) { return x.slug === slug; }); bg.textContent = dedans ? '★ Dans mon carnet' : '☆ Garder dans mon carnet'; bg.classList.toggle('on', dedans); }
    bg.onclick = function () {
      var c = lire(); c.villes = c.villes || [];
      var i = c.villes.findIndex(function (x) { return x.slug === slug; });
      if (i > -1) c.villes.splice(i, 1); else c.villes.unshift({ slug: slug, nom: nom, date: new Date().toISOString().slice(0, 10) });
      garder(c); maj();
    };
    box.querySelector('.carnet-itin').onclick = function () {
      var c = lire(); c.brouillon = c.brouillon || []; if (c.brouillon.indexOf(slug) < 0) c.brouillon.push(slug); garder(c);
      location.href = root + 'itineraire/';
    };
    maj();
  }

  // 2. Page « Mon carnet »
  var page = document.getElementById('carnet-page');
  if (!page) return;
  function rendre() {
    var c = lire(), v = c.villes || [], it = c.itineraires || [];
    page.innerHTML = '<h2>Mes villes (' + v.length + ')</h2>' + (v.length ? '<ul class="o-liste">' + v.map(function (x, i) {
      return '<li><a href="' + root + 'villes/' + x.slug + '/"><b>' + E(x.nom) + '</b></a><small>gardée le ' + E(x.date) + '</small><button type="button" data-v="' + i + '">Retirer</button></li>'; }).join('') + '</ul>'
      + '<p><a class="btn-lien" href="' + root + 'itineraire/" id="carnet-vers-itin">Faire un itinéraire avec ces villes</a> · <a class="btn-lien" href="' + root + 'comparer/#v=' + v.slice(0, 4).map(function (x) { return x.slug; }).join(',') + '">Les comparer</a></p>'
      : '<p class="o-vide">Aucune ville gardée. Sur une fiche, cliquez sur « Garder dans mon carnet ».</p>')
      + '<h2>Mes itinéraires (' + it.length + ')</h2>' + (it.length ? '<ul class="o-liste">' + it.map(function (x, i) {
        return '<li><a href="' + E(x.lien) + '"><b>' + E(x.titre) + '</b></a><small>' + x.jours + ' jours · créé le ' + E(x.date) + '</small><button type="button" data-it="' + i + '">Retirer</button></li>'; }).join('') + '</ul>'
        : '<p class="o-vide">Aucun itinéraire gardé.</p>')
      + '<h2>Sauvegarde</h2><p class="note">Le carnet est gardé dans ce navigateur. Pour le retrouver sur un autre appareil, exportez-le puis importez-le.</p>'
      + '<div class="o-actions"><button type="button" id="carnet-export">Exporter mon carnet</button><label class="o-bouton">Importer un carnet<input type="file" accept=".json" id="carnet-import" hidden></label><button type="button" id="carnet-vider">Tout effacer</button></div>';
    page.querySelectorAll('[data-v]').forEach(function (b) { b.onclick = function () { var c = lire(); c.villes.splice(+b.getAttribute('data-v'), 1); garder(c); rendre(); }; });
    page.querySelectorAll('[data-it]').forEach(function (b) { b.onclick = function () { var c = lire(); c.itineraires.splice(+b.getAttribute('data-it'), 1); garder(c); rendre(); }; });
    var vi = page.querySelector('#carnet-vers-itin'); if (vi) vi.onclick = function () { var c = lire(); c.brouillon = (c.villes || []).map(function (x) { return x.slug; }); garder(c); };
    page.querySelector('#carnet-export').onclick = function () {
      var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(lire(), null, 1)], { type: 'application/json' }));
      a.download = 'mon-carnet-dix-mille-escales.json'; a.click();
    };
    page.querySelector('#carnet-import').onchange = function (e) {
      var fi = e.target.files[0]; if (!fi) return;
      fi.text().then(function (t) { try { var d = JSON.parse(t); var c = lire(); c.villes = (d.villes || []).concat(c.villes || []); c.itineraires = (d.itineraires || []).concat(c.itineraires || []); garder(c); rendre(); } catch (err) { alert('Fichier illisible.'); } });
    };
    page.querySelector('#carnet-vider').onclick = function () { if (confirm('Effacer tout le carnet de cet appareil ?')) { garder({}); rendre(); } };
  }
  rendre();
})();
