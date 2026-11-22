/* Dix Mille Escales – construction des fiches légères (villes de moins de 300 000 habitants environ).
   La page ne contient que le titre et l'introduction ; tout le reste est construit ici, dans le navigateur,
   à partir des fichiers compressés donnees.json.gz et lieux.json.gz de la ville. */
(function () {
  var zone = document.getElementById('fiche-dyn');
  if (!zone) return;
  var root = document.body.getAttribute('data-root') || '../../', slug = zone.getAttribute('data-slug');
  var MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  var MC = ['janv', 'févr', 'mars', 'avr', 'mai', 'juin', 'juil', 'août', 'sept', 'oct', 'nov', 'déc'];
  var RUB = [['voir', 'À voir', 'Monuments, musées, belvédères, parcs et sites.'], ['manger', 'Manger et boire', 'Restaurants, cafés, bars et glaciers.'],
    ['dormir', 'Dormir', 'Hôtels, auberges et maisons d’hôtes.'], ['faire', 'Activités', 'Plages, sports, loisirs.'], ['acheter', 'Acheter', 'Marchés, boutiques et artisanat.'], ['bouger', 'Gares et stations', 'Gares, stations, gares routières et terminaux de ferry.']];
  var GUIDE = [['comprendre', 'Comprendre {v}'], ['circuler', 'Se déplacer'], ['voir', 'Le guide : que voir'], ['faire', 'Le guide : que faire'], ['manger', 'Le guide : où manger'], ['sortir', 'Sortir le soir'], ['loger', 'Le guide : où dormir'], ['acheter', 'Le guide : shopping'], ['securite', 'Sécurité sur place'], ['sante', 'Santé'], ['communiquer', 'Communiquer'], ['respecter', 'Coutumes et savoir-vivre'], ['environs', 'Le guide : aux environs']];
  var JOURS = { Mo: 'lun', Tu: 'mar', We: 'mer', Th: 'jeu', Fr: 'ven', Sa: 'sam', Su: 'dim', PH: 'jours fériés', off: 'fermé' };
  var HTML_OK = { 'Heure locale': 1, 'Décalage': 1, 'Saison': 1, 'Monnaie': 1, 'Soleil aujourd’hui': 1 };
  function lireJson(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); }).then(function (b) {
      var o = new Uint8Array(b);
      if (o[0] === 0x1f && o[1] === 0x8b) {
        if (!('DecompressionStream' in window)) throw new Error('ancien');
        return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
      }
      return JSON.parse(new TextDecoder().decode(o));
    });
  }
  function E(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function nb(n) { return new Intl.NumberFormat('fr-FR').format(n); }
  function v(x) { return String(x).replace('.', ','); }
  function hfr(h) { Object.keys(JOURS).forEach(function (k) { h = h.split(k).join(JOURS[k]); }); return h.replace(/;/g, ' ; '); }
  function carac(c) {
    if (!c) return '';
    function m(x) { return (x < 100 ? String(Math.round(x * 10) / 10).replace('.', ',') : nb(Math.round(x))) + ' m'; }
    function su(x) { return x >= 1e6 ? String(Math.round(x / 1e4) / 100).replace('.', ',') + ' km²' : x >= 1e4 ? nb(Math.round(x / 1e4)) + ' ha' : nb(Math.round(x)) + ' m²'; }
    function an(x) { return x < 0 ? (-x) + ' av. J.-C.' : String(x); }
    var p = [];
    if (c.hauteur) p.push('hauteur ' + m(c.hauteur)); if (c.longueur) p.push('longueur ' + m(c.longueur)); if (c.largeur) p.push('largeur ' + m(c.largeur));
    if (c.superficie) p.push('superficie ' + su(c.superficie)); if (c.altitude) p.push('altitude ' + m(c.altitude));
    var d = c.creation || c.debut || c.ouverture; if (d) p.push('date : ' + an(d));
    if (c.architecte) p.push('architecte : ' + c.architecte.join(', ')); if (c.style) p.push('style : ' + c.style.join(', '));
    if (c.visiteurs_an) p.push(nb(c.visiteurs_an) + ' visiteurs par an'); if (c.protection) p.push('protection : ' + c.protection.join(', '));
    return p.join(' · ');
  }
  function depot() { var m = location.hostname.match(/^([^.]+)\.github\.io$/), seg = location.pathname.split('/').filter(Boolean); return m && seg.length ? m[1] + '/' + seg[0] : 'pablopacaut17-sudo/dix-mille-escales'; }
  function villeNom() { var h = document.querySelector('h1.city'); return h ? h.textContent.replace(/Ville phare|Fiche complète/g, '').trim() : ''; }
  function extras(f, slug) {
    var vn = villeNom(), h = '';
    if (f.wikivoyage) h += '<div class="i wv">« ' + E(f.wikivoyage) + ' » <small>(Wikivoyage)</small></div>';
    var ph = f.histoire && f.histoire.f && f.histoire.f.photo;
    if (ph) h += '<figure class="vignette"><img src="' + E(ph.u) + '" alt="' + E(f.nom) + '" loading="lazy" decoding="async"><figcaption><a href="' + E(ph.page) + '" rel="noopener" target="_blank">' + E(ph.a) + (ph.l ? ' · ' + E(ph.l) : '') + '</a></figcaption></figure>';
    if (f.histoire && f.histoire.f) h += '<div class="i carac">' + E(carac(f.histoire.f)) + '</div>';
    if (f.histoire && f.histoire.r) h += '<details class="histoire"><summary>Histoire</summary><p>' + E(f.histoire.r) + '</p><p><a href="https://fr.wikipedia.org/wiki/' + encodeURIComponent(f.histoire.t.replace(/ /g, '_')) + '" target="_blank" rel="noopener">Lire l’article Wikipédia</a></p></details>';
    (f.avis || []).slice(0, 2).forEach(function (a) { h += '<div class="i avis-l">' + a.note + '/5 · « ' + E(a.texte.slice(0, 300)) + ' » <small>' + E(a.date || '') + '</small></div>'; });
    var corps = 'Lieu : ' + f.nom + '\nIdentifiant : ' + f.id + '\nVille : ' + slug + '\n\nNote (de 1 à 5) : \n\nVotre avis :\n\n\nDate de la visite (mois et année) : \n\n(Votre avis sera publié sur Dix Mille Escales après relecture. Restez courtois et factuel.)';
    var liens = ' · <a href="https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(f.nom + ' ' + vn) + '" target="_blank" rel="noopener nofollow">Avis et photos</a>'
      + ' · <a href="https://github.com/' + depot() + '/issues/new?title=' + encodeURIComponent('Avis – ' + f.nom + ' – ' + vn) + '&body=' + encodeURIComponent(corps) + '" target="_blank" rel="noopener nofollow">Donner mon avis</a>';
    return { avant: h, liens: liens };
  }
  function reperes(f) { return [(f.wikidata || f.patrimoine_mondial) ? '★ incontournable' : '', f.wikivoyage ? '✓ recommandé par Wikivoyage' : '', f.avis_n ? String(Math.round(f.avis_moy * 10) / 10).replace('.', ',') + '/5 (' + f.avis_n + ' avis de lecteurs)' : '']; }
  function sec(id, titre, corps) { return '<section class="block" id="' + id + '"><h2>' + titre + '</h2>' + corps + '</section>'; }
  function prose(t, ouvert) {
    var b = [], p = 0;
    (t || '').split('\n').map(function (l) { return l.trim(); }).filter(Boolean).forEach(function (l) {
      if (l.length < 70 && !/[.:»)\]]$/.test(l)) b.push('<h4>' + E(l) + '</h4>'); else { b.push('<p>' + E(l) + '</p>'); p++; }
    });
    var n = 0, cut = -1;
    for (var i = 0; i < b.length; i++) { if (b[i].indexOf('<p>') === 0) { n++; if (n === (ouvert || 3) + 1) { cut = i; break; } } }
    if (cut < 0) return '<div class="prose">' + b.join('') + '</div>';
    return '<div class="prose">' + b.slice(0, cut).join('') + '<details class="more"><summary>Lire la suite</summary>' + b.slice(cut).join('') + '</details></div>';
  }
  function lieu(f) {
    var x_ = extras(f, slug);
    var meta = reperes(f).concat([f.type, f.cuisine, f.etoiles ? f.etoiles + ' étoiles' : '', f.fauteuil === 'oui' ? 'accessible en fauteuil' : '', f.terrasse === 'oui' ? 'terrasse' : '']).filter(Boolean).join(' · ');
    var p = f.id ? f.id.slice(4).split('/') : null;
    return '<li style="--c:var(--' + f.rubrique + ')"><h3>' + E(f.nom) + '</h3><div class="m">' + E(meta) + '</div>'
      + (f.adresse ? '<div class="i">' + E(f.adresse) + '</div>' : '') + (f.horaires ? '<div class="i">Horaires : ' + E(hfr(f.horaires)) + '</div>' : '')
      + x_.avant + '<div class="i">' + (f.site && /^https?:/.test(f.site) ? '<a href="' + E(f.site) + '" rel="nofollow noopener" target="_blank">Site</a> · ' : '')
      + (p ? '<a href="https://www.openstreetmap.org/' + p[0] + '/' + p[1] + '" rel="nofollow noopener" target="_blank">Carte</a>' : '') + x_.liens + '</div></li>';
  }
  function duree(km) { var h = km * 1.3 / 70; return h < 1 ? Math.max(10, Math.round(h * 12) * 5) + ' min' : Math.floor(h) + ' h ' + String(Math.round(h % 1 * 12) * 5).padStart(2, '0'); }

  Promise.all([lireJson(root + 'villes/' + slug + '/donnees.json.gz'),
               lireJson(root + 'villes/' + slug + '/lieux.json.gz').catch(function () { return null; })]).then(function (r) {
    var d = r[0], L = r[1], c = d.complet || {}, h = '';
    // Photo
    if (c.photo) {
      var cr = [c.photo.auteur, c.photo.licence].filter(Boolean).join(' · ') || 'Wikimedia Commons';
      document.querySelector('.hero').insertAdjacentHTML('beforebegin', '<figure class="hero-photo"><img src="' + E(c.photo.url) + '" alt="Vue de ' + E(d.nom) + '" decoding="async"><figcaption>Photo : <a href="' + E(c.photo.page) + '" rel="noopener" target="_blank">' + E(cr) + '</a></figcaption></figure>');
    }
    if (c.blason) document.querySelector('.city').insertAdjacentHTML('afterbegin', '<img class="blason" src="' + E(c.blason.url) + '" alt="Blason de ' + E(d.nom) + '">');
    // Fiche d'identité
    h += '<section class="facts" aria-label="Fiche d’identité"><dl>' + (c.facts || []).map(function (x) { return '<div><dt>' + E(x[0]) + '</dt><dd>' + (HTML_OK[x[0]] || /<br>/.test(x[1]) ? x[1] : E(x[1])) + '</dd></div>'; }).join('') + '</dl></section>';
    if (d.securite && d.securite.niveau >= 2) h += '<p class="alerte" style="--a:#C99A00"><b>Sécurité : niveau ' + d.securite.niveau + ' sur 4, ' + E(d.securite.libelle.toLowerCase()) + '.</b> Consultez les Conseils aux voyageurs du ministère des Affaires étrangères avant de partir.</p>';
    if (c.resume) h += sec('en-bref', 'En bref', prose(c.resume, 4));
    var txt = c.textes || {};
    if (txt.histoire || (c.evenements && c.evenements.length) || d.fondation) {
      var fr = (d.fondation ? [{ nom: 'Fondation', date: d.fondation, big: 1 }] : []).concat(c.evenements || []);
      h += sec('histoire', 'Histoire', (fr.length ? '<ol class="timeline">' + fr.map(function (e) { return '<li class="' + (e.big ? 'big' : '') + '"><b>' + E(e.date || 'Date inconnue') + '</b>' + E(e.nom) + '</li>'; }).join('') + '</ol>' : '') + (txt.histoire ? prose(txt.histoire, 4) : ''));
    }
    if (d.meteo) h += sec('meteo', 'Météo des 7 prochains jours', '<div class="weather">' + d.meteo.map(function (j) { return '<div><p class="d" style="margin:0">' + E(j.date.slice(8, 10) + '/' + j.date.slice(5, 7)) + '</p><p class="w">' + E(j.ciel) + '</p><p class="t" style="margin:0">' + Math.round(j.max) + '°</p><p class="d" style="margin:0">' + Math.round(j.min) + '°</p></div>'; }).join('') + '</div>');
    if (d.climat) {
      var tmax = Math.max.apply(null, d.climat.map(function (m) { return m.tmax || 0; })), bas = Math.min(0, Math.min.apply(null, d.climat.map(function (m) { return m.tmin || 0; })));
      var best = d.meilleurs_mois || [];
      h += sec('quand-partir', 'Quand partir', '<p class="lead">' + (best.length ? 'Les mois les plus agréables : ' + best.join(', ') + '.' : 'Aucun mois n’est à la fois tempéré et sec : choisissez selon la chaleur et la pluie que vous tolérez.') + '</p>'
        + '<div class="climat" aria-hidden="true">' + d.climat.map(function (m, i) { return '<div class="m ' + (best.indexOf(MOIS[i]) > -1 ? 'ideal' : '') + '"><span class="v">' + Math.round(m.tmax) + '°</span><span class="b" style="height:' + Math.max(4, Math.round((m.tmax - bas) / ((tmax - bas) || 1) * 100)) + '%"></span><span class="p" style="height:' + Math.min(100, Math.round(m.pluie_mm / 3)) + '%"></span><span class="l">' + MC[i] + '</span></div>'; }).join('') + '</div>'
        + '<details class="more"><summary>Voir le tableau mois par mois</summary><div class="table-scroll"><table><thead><tr><th>Mois</th><th>Max.</th><th>Min.</th><th>Pluie</th><th>Jours de pluie</th></tr></thead><tbody>'
        + d.climat.map(function (m, i) { return '<tr><td>' + MOIS[i] + '</td><td>' + Math.round(m.tmax) + '°</td><td>' + Math.round(m.tmin) + '°</td><td>' + m.pluie_mm + ' mm</td><td>' + m.jours_pluie + '</td></tr>'; }).join('') + '</tbody></table></div></details>');
    }
    // S'y rendre et guide Wikivoyage
    var gd = c.guide || {};
    var AC = [['gares', 'En train'], ['routieres', 'En bus ou en car'], ['ports', 'En bateau']], acc = d.acces || {};
    var accH = AC.filter(function (x) { return acc[x[0]]; }).map(function (x) { return '<h3>' + x[1] + '</h3><div class="table-scroll"><table><tbody>' + acc[x[0]].map(function (g) { return '<tr><td><b>' + E(g.nom) + '</b>' + (g.adresse ? '<br><small>' + E(g.adresse) + '</small>' : '') + '</td><td class="num">' + v(g.km) + ' km du centre</td><td>' + (g.km < 1.5 ? '≈ ' + Math.max(2, Math.round(g.km / 4.5 * 60)) + ' min à pied' : '≈ ' + duree(g.km) + ' en taxi') + '</td></tr>'; }).join('') + '</tbody></table></div>'; }).join('');
    if ((d.aeroports && d.aeroports.length) || gd.aller || accH) {
      h += sec('guide-aller', 'S’y rendre et accès', (d.aeroports ? '<h3>En avion</h3><div class="table-scroll"><table><thead><tr><th>Aéroport</th><th>Code</th><th>Distance</th><th>Trajet estimé</th></tr></thead><tbody>'
        + d.aeroports.map(function (x) { return '<tr><td>' + E(x.nom) + (x.international ? ' · international' : '') + '</td><td class="num">' + E(x.code) + '</td><td class="num">' + nb(x.km) + ' km</td><td>≈ ' + duree(x.km) + ' de route</td></tr>'; }).join('') + '</tbody></table></div>' : '')
        + accH + (gd.aller ? prose(gd.aller, 3) : ''));
    }
    GUIDE.forEach(function (g) { if (gd[g[0]]) h += sec('guide-' + g[0], g[1].replace('{v}', E(d.nom)), prose(gd[g[0]], 3)); });
    // Lieux
    var tous = L && L.lieux ? L.lieux : [];
    if (tous.length) {
      h += sec('carte-lieux', 'Les lieux sur la carte', '<div class="carte-zone" data-lat="' + d.lat + '" data-lon="' + d.lon + '" data-rayon="3"><button type="button" class="tout-voir carte-ouvrir">Ouvrir la carte interactive (zoom, tous les lieux, détails)</button></div>');
      RUB.forEach(function (rb) {
        var items = tous.filter(function (f) { return f.rubrique === rb[0]; }).sort(function (x, y) { return ((y.wikidata || y.patrimoine_mondial) ? 1 : 0) - ((x.wikidata || x.patrimoine_mondial) ? 1 : 0); });
        if (!items.length) return;
        var total = d['nb_' + rb[0]] || items.length;
        h += sec(rb[0], rb[1], '<p class="lead">' + rb[2] + ' ' + nb(total) + ' adresse' + (total > 1 ? 's' : '') + '.</p><ul class="places">' + items.slice(0, 8).map(lieu).join('') + '</ul>'
          + (items.length > 8 ? '<button type="button" class="tout-voir" data-rub="' + rb[0] + '" data-n="' + items.length + '">Voir les ' + nb(items.length) + ' adresses, avec recherche et filtres</button>' : ''));
      });
    } else {
      h += sec('lieux', 'Lieux, adresses et visites', '<p class="empty">Les robots n’ont pas encore exploré ' + E(d.nom) + ' : monuments, restaurants, hôtels et boutiques apparaîtront ici après leur passage.</p>');
    }
    // Conseils officiels aux voyageurs
    if (d.conseils) {
      var CN = ['#2F7D6D', '#C99A00', '#D9822B', '#B5485D'];
      h += sec('conseils', 'Conseils officiels aux voyageurs', '<p class="alerte" style="--a:' + (CN[d.conseils.niveau] || '#56707A') + '"><b>' + E(d.pays) + ' : ' + E(d.conseils.texte) + '.</b></p>'
        + (d.conseils.zones.length ? '<p class="lead">Zones à éviter ou à risque dans le pays :</p><ul class="unesco">' + d.conseils.zones.map(function (z) { return '<li>' + E(z) + '</li>'; }).join('') + '</ul>' : '')
        + '<p><a class="tout-voir" style="display:inline-block;text-decoration:none" href="' + root + 'pays/' + d.cc.toLowerCase() + '/conseils/">Sécurité, santé et vaccins, lois et coutumes, transports, catastrophes naturelles : tous les conseils</a></p>'
        + '<p class="note">Source : gouvernement du Canada (données ouvertes). Pour les voyageurs français, la <a href="https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/conseils-par-pays-destination/' + E(d.conseils.fd) + '/" rel="noopener" target="_blank">fiche du ministère des Affaires étrangères</a> fait foi.</p>');
    }
    if (d.conseils_ville && d.conseils_ville.length) h += sec('conseils-ville', 'Ce que disent les conseils officiels de ' + E(d.nom), '<ul>' + d.conseils_ville.map(function (x) { return '<li>' + E(x) + '</li>'; }).join('') + '</ul>');
    if (d.arnaques && d.arnaques.length) h += sec('arnaques', 'Arnaques signalées dans le pays', '<ul>' + d.arnaques.map(function (x) { return '<li>' + E(x) + '</li>'; }).join('') + '</ul><p><a href="' + root + 'pays/' + d.cc.toLowerCase() + '/conseils/#arnaques">Toutes les arnaques signalées</a></p>');
    var avisCorps = 'Lieu : ' + d.nom + '\nIdentifiant : ville\nVille : ' + d.slug + '\n\nNote (de 1 à 5) : \n\nVotre avis :\n\n\nDate de la visite (mois et année) : \n';
    h += sec('avis-lecteurs', 'Avis des lecteurs', (d.avis_ville && d.avis_ville.length ? d.avis_ville.map(function (a) { return '<p class="avis-l"><b>' + a.note + '/5</b> · « ' + E(a.texte) + ' » <small>' + E(a.date || '') + '</small></p>'; }).join('') : '<p class="lead">Pas encore d’avis sur ' + E(d.nom) + '. Vous y êtes allé ? Partagez votre expérience.</p>')
      + '<p><a class="tout-voir" style="display:inline-block;text-decoration:none" target="_blank" rel="noopener" href="https://github.com/' + depot() + '/issues/new?title=' + encodeURIComponent('Avis – ' + d.nom + ' – ' + d.nom) + '&body=' + encodeURIComponent(avisCorps) + '">Donner mon avis sur ' + E(d.nom) + '</a></p><p class="note">Avis publiés après relecture (compte GitHub gratuit nécessaire).</p>');
    if (d.phrases) h += sec('langue', 'Quelques mots utiles en ' + E(d.phrases.langue), '<div class="table-scroll"><table><tbody>' + d.phrases.lignes.map(function (x) { var i = x.indexOf(':'); return i > 0 ? '<tr><td>' + E(x.slice(0, i).trim()) + '</td><td><b>' + E(x.slice(i + 1).trim()) + '</b></td></tr>' : '<tr><td colspan="2">' + E(x) + '</td></tr>'; }).join('') + '</tbody></table></div><p class="note">D’après le <a href="' + E(d.phrases.url) + '" rel="noopener" target="_blank">' + E(d.phrases.titre) + '</a> de Wikivoyage (licence CC BY-SA).</p>');
    if (d.transports && d.transports.lignes) {
      var NM = [['metro', 'métro'], ['tram', 'tram'], ['bus', 'bus'], ['train', 'train'], ['ferry', 'ferry']];
      h += sec('transports-communs', 'Transports en commun', '<p class="lead">' + NM.filter(function (x) { return d.transports.lignes[x[0]]; }).map(function (x) { var k = d.transports.lignes[x[0]]; return '<b>' + nb(k) + '</b> ligne' + (k > 1 ? 's' : '') + ' de ' + x[1]; }).join(', ') + '.</p>'
        + (d.transports.reseaux && d.transports.reseaux.length ? '<p>Réseaux et exploitants : ' + E(d.transports.reseaux.join(', ')) + '.</p>' : '')
        + '<p class="note">D’après OpenStreetMap. Pour comparer avion, train, bus et voiture : <a href="' + root + 'trajets/#de=' + d.slug + '">comparateur de trajets</a>.</p>');
    }
    // Santé et urgences
    if ((d.urgences && d.urgences.length) || (d.sante && d.sante.length) || (d.representations && d.representations.length)) {
      var TR = { embassy: 'Ambassade', consulate: 'Consulat', consulate_general: 'Consulat général', honorary_consul: 'Consul honoraire' };
      var NR = { FR: 'France', BE: 'Belgique', CH: 'Suisse', CA: 'Canada' };
      var hs = '';
      if (d.urgences && d.urgences.length) hs += '<div class="urgences"><p class="lead"><b>Numéros d’urgence (' + E(d.pays) + ')</b></p><ul>' + d.urgences.map(function (x) { return '<li><a href="tel:' + E(x.numero.replace(/\s/g, '')) + '"><b>' + E(x.numero) + '</b></a>' + (x.services.length ? ' : ' + E(x.services.join(', ')) : '') + '</li>'; }).join('') + '</ul></div>';
      if (d.sante && d.sante.length) {
        var it = tous.filter(function (x) { return x.rubrique === 'sante'; });
        hs += '<h3>Soins autour de ' + E(d.nom) + '</h3><ul class="places">' + d.sante.map(function (x) { return '<li style="--c:var(--sante)"><h3>' + E(x.nom) + '</h3><div class="m">' + E(x.type) + (x.urgences === 'oui' ? ' · service d’urgences' : '') + '</div>' + (x.adresse ? '<div class="i">' + E(x.adresse) + '</div>' : '') + (x.telephone ? '<div class="i"><a href="tel:' + E(x.telephone.replace(/\s/g, '')) + '">' + E(x.telephone) + '</a></div>' : '') + '</li>'; }).join('') + '</ul>'
          + (it.length > 8 ? '<button type="button" class="tout-voir" data-rub="sante" data-n="' + it.length + '">Voir les ' + nb(d.nb_sante || it.length) + ' adresses de santé</button>' : '');
      }
      if (d.representations && d.representations.length) hs += '<h3>Ambassades et consulats</h3><div class="table-scroll"><table><tbody>' + d.representations.map(function (x) { return '<tr><td>' + NR[x.pays] + '</td><td><b>' + E(x.nom || TR[x.type] || 'Représentation') + '</b><br><small>' + E(TR[x.type] || '') + (x.adresse ? ' · ' + E(x.adresse) : '') + '</small></td><td class="num">' + nb(x.km) + ' km</td><td>' + (x.telephone ? '<a href="tel:' + E(x.telephone.replace(/\s/g, '')) + '">' + E(x.telephone) + '</a>' : '') + '</td></tr>'; }).join('') + '</tbody></table></div>';
      hs += '<p class="note">Santé en voyage : voir les Conseils aux voyageurs et le <a href="https://www.pasteur.fr/fr/centre-medical/preparer-son-voyage" rel="noopener" target="_blank">centre médical de l’Institut Pasteur</a>. Assurance et rapatriement : <a href="' + root + 'assurance/">notre guide</a>.</p>';
      h += sec('sante', 'Santé et urgences', hs);
    }
    var gal = tous.filter(function (x) { return x.histoire && x.histoire.f && x.histoire.f.photo; }).sort(function (a, b) { return (b.patrimoine_mondial ? 1 : 0) - (a.patrimoine_mondial ? 1 : 0); }).slice(0, 12);
    if (gal.length) h += sec('galerie', E(d.nom) + ' en images', '<div class="galerie">' + gal.map(function (x) { var p_ = x.histoire.f.photo; return '<figure><img src="' + E(p_.u) + '" alt="' + E(x.nom) + '" loading="lazy" decoding="async"><figcaption><b>' + E(x.nom) + '</b><br><a href="' + E(p_.page) + '" rel="noopener" target="_blank">' + E(p_.a) + (p_.l ? ' · ' + E(p_.l) : '') + '</a></figcaption></figure>'; }).join('') + '</div><p class="note">Photos : Wikimedia Commons, sous licences libres.</p>');
    var au = c.alentours || [], pr = (d.proches || []).filter(function (p) { return p.km >= 15 && p.km <= 150; }).slice(0, 4);
    if (au.length || pr.length) {
      h += sec('alentours', 'Aux alentours', '<ul class="excursions">' + au.slice(0, 12).map(function (f) { return '<li><b>' + E(f.nom) + (f.patrimoine_mondial ? '<span class="unesco-tag">Patrimoine mondial</span>' : '') + '</b><span class="d">' + E(f.type) + ' · ' + v(f.km) + ' km ' + E(f.direction) + ' · ≈ ' + duree(f.km) + ' de route</span></li>'; }).join('')
        + pr.map(function (p) { return '<li><b><a href="' + root + 'villes/' + p.slug + '/">' + E(p.nom) + '</a></b><span class="d">Ville voisine · ' + nb(p.km) + ' km · ≈ ' + duree(p.km) + ' de route</span></li>'; }).join('') + '</ul>');
    }
    if (d.cout) h += sec('budget', 'Budget', '<p class="lead">Pays : ' + E(d.pays) + '. Les prix y sont en moyenne à <b>' + Math.round(d.cout.indice * 100) + ' %</b> de ceux de la France.</p><div class="table-scroll"><table><tbody>'
      + Object.keys(d.cout.prix).map(function (k) { return '<tr><td>' + E(k.charAt(0).toUpperCase() + k.slice(1)) + '</td><td class="num">≈ ' + v(d.cout.prix[k]) + ' €</td></tr>'; }).join('') + '</tbody></table></div><p class="note">Estimation à partir du niveau des prix national (Banque mondiale, ' + E(d.cout.annee) + ').</p>');
    if (d.formalites) h += sec('formalites', 'Formalités et sécurité', '<div class="table-scroll"><table><tbody>' + Object.keys(d.formalites).map(function (k) { return '<tr><td>' + E(k) + '</td><td>' + E(d.formalites[k]) + '</td></tr>'; }).join('') + '</tbody></table></div>'
      + (d.securite ? '<p class="alerte" style="--a:#2F7D6D"><b>Niveau de sécurité : ' + d.securite.niveau + ' sur 4, ' + E(d.securite.libelle.toLowerCase()) + '.</b></p>' : '')
      + '<p class="note">Vérifiez toujours avant de partir sur les <a href="https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs/conseils-par-pays-destination/" rel="noopener" target="_blank">Conseils aux voyageurs</a>.</p>');
    if ((d.unesco && d.unesco.length) || txt.patrimoine) h += sec('patrimoine', 'Patrimoine', (d.unesco && d.unesco.length ? '<p class="lead">Patrimoine mondial de l’UNESCO :</p><ul class="unesco">' + d.unesco.map(function (u) { return '<li>' + E(u) + '</li>'; }).join('') + '</ul>' : '') + (txt.patrimoine ? prose(txt.patrimoine) : ''));
    if (txt.gastronomie) h += sec('gastronomie', 'Gastronomie', prose(txt.gastronomie));
    if (d.jumelages) h += sec('jumelages', 'Villes jumelées', '<p class="lead">' + E(d.jumelages.join(', ')) + '.</p>');
    if (d.feries) h += sec('feries', 'Jours fériés à venir', '<div class="table-scroll"><table><tbody>' + d.feries.map(function (f) { return '<tr><td>' + E(f.date) + '</td><td>' + E(f.nom) + '</td></tr>'; }).join('') + '</tbody></table></div>');
    if (d.proches) h += sec('proches', 'Villes proches', '<div class="near">' + d.proches.map(function (p) { return '<a href="' + root + 'villes/' + p.slug + '/">' + E(p.nom) + '<span>' + nb(p.km) + ' km</span></a>'; }).join('') + '</div>');
    if (c.guide_source && c.guide_source.url) h += '<p class="note">Rubriques du guide reprises de l’article <a href="' + E(c.guide_source.url) + '" rel="noopener" target="_blank">' + E(c.guide_source.titre) + '</a> de Wikivoyage (licence CC BY-SA).</p>';
    if (c.wikipedia && c.wikipedia.url) h += '<p class="note">Textes repris de l’article <a href="' + E(c.wikipedia.url) + '" rel="noopener" target="_blank">' + E(c.wikipedia.titre) + '</a> de Wikipédia (licence CC BY-SA 4.0). Lieux : © contributeurs OpenStreetMap.</p>';
    h += '<p class="note" style="margin-top:2rem">Fiche mise à jour le ' + E(d.maj) + '.</p>';
    zone.innerHTML = h;
    if (window.DME_initVivant) window.DME_initVivant(zone);
    if (window.DME_lierBoutons) window.DME_lierBoutons(zone);
    if (window.DME_lierCarte) window.DME_lierCarte(zone);
    zone.dataset.pret = '1';
    if (window.DME_onglets) window.DME_onglets();
  }).catch(function () {
    zone.innerHTML = '<p class="empty">Cette fiche n’a pas pu être chargée. Votre navigateur est peut-être trop ancien : essayez une version récente de Chrome, Firefox, Safari ou Edge.</p>';
  });
})();
