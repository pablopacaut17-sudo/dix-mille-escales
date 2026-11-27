/* Dix Mille Escales – boîte à questions.
   Comprend une question en français sur n'importe quelle ville du guide, trouve la ville citée
   (ou celle de la page), charge le fichier donnees.json de sa fiche et répond. Sans IA, sans frais. */
(function () {
  var boites = document.querySelectorAll('.questions');
  if (!boites.length) return;
  var root = document.body.getAttribute('data-root') || '';
  var MOIS = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre'];
  var MOIS_AFF = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  var VIDES = ('a au aux avec ce ces dans de des du en est et il ils je la le les leur ma me mes mon ne on ou par pas pour qu que quel quelle quelles quels qui sa se ses son sur ta te tes ton tu un une va vos votre y faut il fait faire voir aller temps prix cout visa meteo heure quand partir bien bon belle beau grand grande ville villes pays combien comment pourquoi est-ce ca cela mois jour jours nuit plage ski tour port mer centre rio sale bar mons bonne').split(' ');
  var vide = {}; VIDES.forEach(function (m) { vide[m] = 1; });
  var index = null, noms = null, paysNoms = null, cache = {};

  function norm(t) { return (t || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[’'`\-|?!.,;:()«»"]/g, ' ').replace(/\s+/g, ' ').trim(); }
  function E(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function nb(n) { return new Intl.NumberFormat('fr-FR').format(n); }
  function virg(x) { return String(x).replace('.', ','); }

  function poids(r) { return r[3] + (r[5] ? 1e10 : 0); }  // homonymes : la ville phare d'abord, puis la plus peuplée
  function chargerIndex(cb) {
    if (index) return cb();
    fetch(root + 'static/index.json').then(function (r) { return r.json(); }).then(function (d) {
      index = d; noms = {}; paysNoms = {};
      d.forEach(function (r) { var k = norm(r[2]); if (k && (!paysNoms[k] || paysNoms[k][3] < r[3])) paysNoms[k] = r; });
      d.forEach(function (r) {
        var cand = [r[0]].concat((r[4] || '').split('|'));
        cand.forEach(function (n) {
          var k = norm(n); if (!k) return;
          var sans = k.replace(/^(le|la|les|l) /, '');
          [k, sans].forEach(function (x) { if (x.length >= 3 && (!noms[x] || poids(noms[x]) < poids(r))) noms[x] = r; });
        });
      });
      cb();
    }).catch(function () { cb('erreur'); });
  }

  function trouverVille(q) {
    var mots = norm(q).split(' '), meilleur = null, long = 0;
    for (var i = 0; i < mots.length; i++) {
      for (var l = Math.min(5, mots.length - i); l >= 1; l--) {
        var g = mots.slice(i, i + l).join(' ');
        if (l === 1 && (vide[g] || g.length < 3)) continue;
        if (noms[g] && (l > long || (l === long && poids(noms[g]) > poids(meilleur)))) { meilleur = noms[g]; long = l; break; }
      }
    }
    if (meilleur) return meilleur;
    // Pas de ville citée : un pays ? On prend sa plus grande ville du guide.
    for (i = 0; i < mots.length; i++) {
      for (l = Math.min(4, mots.length - i); l >= 1; l--) {
        g = mots.slice(i, i + l).join(' ');
        if (paysNoms[g]) return paysNoms[g];
      }
    }
    return null;
  }

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
  function charger(slug, cb) {
    if (cache[slug]) return cb(cache[slug]);
    lireJson(root + 'villes/' + slug + '/donnees.json.gz')
      .then(function (d) { cache[slug] = d; cb(d); }).catch(function () { cb(null); });
  }

  function aV(nom, maj) {  // « à Lisbonne », « au Caire », « aux Sables », « à la Havane »
    var r = /^Le /.test(nom) ? 'au ' + nom.slice(3) : /^Les /.test(nom) ? 'aux ' + nom.slice(4) : /^La /.test(nom) ? 'à la ' + nom.slice(3) : /^L[’']/.test(nom) ? 'à l’' + nom.slice(2) : 'à ' + nom;
    r = E(r); return maj ? r.charAt(0).toUpperCase() + r.slice(1) : r;
  }
  function deV(nom) {  // « de Lisbonne », « du Caire », « des Sables », « d’Athènes »
    var r = /^Le /.test(nom) ? 'du ' + nom.slice(3) : /^Les /.test(nom) ? 'des ' + nom.slice(4) : /^La /.test(nom) ? 'de la ' + nom.slice(3) : /^L[’']/.test(nom) ? 'de l’' + nom.slice(2) : /^[AEIOUYÉÈÂÎÔH]/i.test(nom) ? 'd’' + nom : 'de ' + nom;
    return E(r);
  }
  function cpt(n, un, plusieurs) { return nb(n) + ' ' + (n > 1 ? plusieurs : un); }
  function lien(d, ancre, txt) { return ' <a href="' + root + 'villes/' + d.slug + '/' + (ancre ? '#' + ancre : '') + '">' + (txt || 'Voir la fiche ' + deV(d.nom)) + '</a>'; }
  function liste(l, f) { return '<ul>' + l.map(function (x) { return '<li>' + f(x) + '</li>'; }).join('') + '</ul>'; }
  function manque(d, quoi) { return 'Les robots n’ont pas encore collecté ' + quoi + ' pour ' + E(d.nom) + '. Ils passent régulièrement : revenez bientôt.' + lien(d); }

  function soleil(d) {
    var R = Math.PI / 180, jd = Date.now() / 864e5 + 2440587.5, n = Math.round(jd - 2451545 - 0.0009 + d.lon / 360), Js = n + 0.0009 - d.lon / 360;
    var M = (357.5291 + 0.98560028 * Js) % 360, C = 1.9148 * Math.sin(M * R) + 0.02 * Math.sin(2 * M * R) + 0.0003 * Math.sin(3 * M * R);
    var L = (M + C + 282.9372) % 360, Jt = 2451545 + Js + 0.0053 * Math.sin(M * R) - 0.0069 * Math.sin(2 * L * R);
    var sd = Math.sin(L * R) * Math.sin(23.4397 * R), cd = Math.cos(Math.asin(sd));
    var cw = (Math.sin(-0.833 * R) - Math.sin(d.lat * R) * sd) / (Math.cos(d.lat * R) * cd);
    if (cw < -1) return 'Le soleil ne se couche pas en ce moment ' + aV(d.nom) + ' (soleil de minuit).';
    if (cw > 1) return 'Le soleil ne se lève pas en ce moment ' + aV(d.nom) + ' (nuit polaire).';
    var w = Math.acos(cw) / R, f = function (j) { return new Intl.DateTimeFormat('fr-FR', { timeZone: d.fuseau, hour: '2-digit', minute: '2-digit' }).format(new Date((j - 2440587.5) * 864e5)); };
    var duree = w / 180 * 24;
    return 'Aujourd’hui ' + aV(d.nom) + ', le soleil se lève vers <b>' + f(Jt - w / 360) + '</b> et se couche vers <b>' + f(Jt + w / 360) + '</b> (heure locale), soit environ ' + Math.floor(duree) + ' h ' + String(Math.round(duree % 1 * 60)).padStart(2, '0') + ' de jour.';
  }

  function heure(d) {
    var now = new Date(), h = new Intl.DateTimeFormat('fr-FR', { timeZone: d.fuseau, weekday: 'long', hour: '2-digit', minute: '2-digit' }).format(now);
    function t(z) { var o = {}; new Intl.DateTimeFormat('en-US', { timeZone: z, hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).formatToParts(now).forEach(function (x) { o[x.type] = x.value; }); return Date.UTC(+o.year, +o.month - 1, +o.day, +o.hour % 24, +o.minute); }
    var dec = (t(d.fuseau) - t('Europe/Paris')) / 36e5;
    var txt = dec === 0 ? 'la même heure qu’à Paris' : (Math.abs(dec) + ' h ' + (dec > 0 ? 'de plus' : 'de moins') + ' qu’à Paris').replace('.5 h', ' h 30');
    return aV(d.nom, 1) + ', il est <b>' + h + '</b>, soit ' + txt + '.';
  }

  function moisCite(q) { for (var i = 0; i < 12; i++) if ((' ' + q + ' ').indexOf(' ' + MOIS[i] + ' ') > -1) return i; return -1; }

  function climatMois(d, i) {
    var m = d.climat[i];
    return 'En ' + MOIS_AFF[i] + ' ' + aV(d.nom) + ' : environ <b>' + Math.round(m.tmax) + ' °C</b> l’après-midi et ' + Math.round(m.tmin) + ' °C la nuit, '
      + m.pluie_mm + ' mm de pluie' + (m.jours_pluie != null ? ' en ' + m.jours_pluie + ' jours' : '') + (m.soleil_h != null ? ', ' + virg(m.soleil_h) + ' h de soleil par jour' : '') + '. '
      + (d.meilleurs_mois && d.meilleurs_mois.indexOf(MOIS_AFF[i]) > -1 ? 'C’est l’un des meilleurs mois pour y aller.' : (d.meilleurs_mois && d.meilleurs_mois.length ? 'Les mois les plus agréables sont : ' + d.meilleurs_mois.join(', ') + '.' : ''));
  }

  var VIDES = ' le la les un une des du de d l a au aux et ou en dans sur pour par avec sans est sont etre faut il elle on y quel quelle quels quelles que qui quoi comment combien pourquoi ou quand ce cet cette ces mon ma mes ton ta tes son sa ses leur leurs je tu nous vous ils elles peut peux pouvoir faire fait se ne pas plus moins tres bien bon bonne avoir ville est-ce ';
  function mots(t, ville) {
    var v = ' ' + norm(ville || '') + ' ';
    return norm(t).replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(function (w) { return w.length >= 3 && VIDES.indexOf(' ' + w + ' ') < 0 && v.indexOf(' ' + w + ' ') < 0; })
      .map(function (w) { return w.length > 4 ? w.replace(/(x|s)$/, '') : w; });
  }
  function carac(c) {
    if (!c) return '';
    var p = [];
    function m(x) { return (x < 100 ? String(Math.round(x * 10) / 10).replace('.', ',') : nb(Math.round(x))) + ' m'; }
    if (c.hauteur) p.push('hauteur ' + m(c.hauteur)); if (c.longueur) p.push('longueur ' + m(c.longueur));
    if (c.superficie) p.push('superficie ' + (c.superficie >= 1e6 ? String(Math.round(c.superficie / 1e4) / 100).replace('.', ',') + ' km²' : c.superficie >= 1e4 ? nb(Math.round(c.superficie / 1e4)) + ' ha' : nb(Math.round(c.superficie)) + ' m²'));
    var dt = c.creation || c.debut || c.ouverture; if (dt) p.push('date : ' + (dt < 0 ? (-dt) + ' av. J.-C.' : dt));
    if (c.architecte) p.push('architecte : ' + c.architecte.join(', ')); if (c.style) p.push('style : ' + c.style.join(', '));
    if (c.visiteurs_an) p.push(nb(c.visiteurs_an) + ' visiteurs par an');
    return p.join(' · ');
  }
  /* Lieux célèbres de tout le guide (titres Wikipédia) : répond à « hauteur de la tour Montparnasse » sans ville citée */
  var LIENS = { de: 1, du: 1, des: 1, la: 1, le: 1, les: 1, l: 1, d: 1, et: 1, a: 1, au: 1, aux: 1, en: 1, sur: 1, sous: 1, the: 1, of: 1 };
  var CLES = { ha: 'hauteur', lo: 'longueur', su: 'superficie', la: 'largeur', al: 'altitude', vi: 'visiteurs_an', cr: 'creation', ou: 'ouverture', ar: 'architecte' };
  var celebresCache = {};
  var GENERIQUES = { avenue: 1, rue: 1, boulevard: 1, place: 1, quai: 1, parc: 1, jardin: 1, jardins: 1, square: 1, cours: 1, esplanade: 1 };
  function motsLieu(t) { return norm(t).replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(function (m) { return m && !LIENS[m]; }); }
  function chercherCelebre(q) {
    var mq = motsLieu(q), present = {};
    mq.forEach(function (m) { present[m] = 1; present[m.replace(/s$/, '')] = 1; });
    var cles = mq.filter(function (m) { return m.length >= 3; }).map(function (m) { return m.slice(0, 2); })
      .filter(function (c, i, l) { return l.indexOf(c) === i; }).slice(0, 14);
    if (!cles.length) return Promise.resolve(null);
    return Promise.all(cles.map(function (c) {
      return celebresCache[c] ? Promise.resolve(celebresCache[c]) : lireJson(root + 'static/celebres/' + c + '.json.gz').then(function (l) { celebresCache[c] = l; return l; }).catch(function () { celebresCache[c] = []; return []; });
    })).then(function (listes) {
      var meilleur = null, lg = 0;
      listes.forEach(function (l) {
        l.forEach(function (x) {
          var mt = motsLieu(x[0]);
          if (mt.length > 2 && GENERIQUES[mt[0]]) mt = mt.slice(1);  // « avenue des Champs-Élysées » : « Champs-Élysées » suffit
          if (!mt.length) return;
          var s = mt.join('');
          if ((mt.length < 2 && s.length < 6) || s.length <= lg) return;
          if (mt.every(function (m) { return present[m] || present[m.replace(/s$/, '')]; })) { meilleur = x; lg = s.length; }
        });
      });
      return meilleur;
    });
  }
  function repCelebre(x) {
    var c = {}, m = x[3] || {};
    Object.keys(m).forEach(function (k) { if (CLES[k]) c[CLES[k]] = m[k]; });
    var infos = carac(c);
    return '<div class="q-ville">' + E(x[2]) + '</div><div class="q-texte"><b>' + E(x[0]) + '</b>' + (infos ? ' : ' + E(infos) + '.' : '.')
      + ' <a href="' + root + 'villes/' + x[1] + '/">Ouvrir la fiche ' + deV(x[2]) + '</a>'
      + ' · <a href="https://fr.wikipedia.org/wiki/' + encodeURIComponent(x[0].replace(/ /g, '_')) + '" target="_blank" rel="noopener">Article Wikipédia</a>'
      + '<p class="note">D’après Wikidata et Wikipédia.</p></div>';
  }
  var lieuxCache = {}, textesCache = {};
  function chargerLieux(slug) {
    if (lieuxCache[slug]) return Promise.resolve(lieuxCache[slug]);
    return lireJson(root + 'villes/' + slug + '/lieux.json.gz').then(function (x) { lieuxCache[slug] = x.lieux || []; return lieuxCache[slug]; }).catch(function () { return []; });
  }
  /* Un lieu cité dans la question (tous les mots significatifs de son nom y figurent) */
  function lieuCite(q0, lieux) {
    var qn = ' ' + norm(q0).replace(/[^a-z0-9 ]/g, ' ') + ' ', meilleur = null, lg = 0;
    lieux.forEach(function (f) {
      var ws = norm(f.nom).replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(function (w) { return w.length >= 3 && VIDES.indexOf(' ' + w + ' ') < 0; });
      if (!ws.length || ws.join('').length < 5) return;
      if (ws.every(function (w) { return qn.indexOf(' ' + w + ' ') > -1 || qn.indexOf(' ' + w.replace(/s$/, '') + ' ') > -1; }) && ws.join('').length > lg) { meilleur = f; lg = ws.join('').length; }
    });
    return meilleur;
  }
  function repLieu(f, d) {
    var h = '<b>' + E(f.nom) + '</b> · ' + E(f.type) + ((f.wikidata || f.patrimoine_mondial) ? ' · ★ incontournable' : '');
    if (f.histoire && f.histoire.f) h += '<p>' + E(carac(f.histoire.f)) + '</p>';
    if (f.histoire && f.histoire.r) h += '<p>' + E(f.histoire.r) + '</p>';
    if (f.adresse) h += '<p>Adresse : ' + E(f.adresse) + '</p>';
    if (f.horaires) h += '<p>Horaires : ' + E(f.horaires) + '</p>';
    if (f.distance_km) h += '<p>À ' + String(f.distance_km).replace('.', ',') + ' km ' + E(f.direction || '') + ' ' + deV(d.nom) + '.</p>';
    if (f.wikivoyage) h += '<p>Wikivoyage : « ' + E(f.wikivoyage) + ' »</p>';
    if (!f.histoire && !f.horaires && !f.adresse) h += '<p>Nous n’avons pas encore de détails sur ce lieu.</p>';
    return h + '<p><a href="https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(f.nom + ' ' + d.nom) + '" target="_blank" rel="noopener">Avis et photos</a></p>';
  }
  /* Recherche dans tous les textes de la ville (Wikipédia, Wikivoyage) et du pays (conseils officiels) */
  function chercherTextes(q0, d) {
    var cle = d.slug;
    var p1 = textesCache[cle] ? Promise.resolve(textesCache[cle]) : (d.complet ? Promise.resolve({ resume: d.complet.resume, textes: d.complet.textes, guide: d.complet.guide })
      : lireJson(root + 'villes/' + d.slug + '/textes.json.gz').catch(function () { return {}; }));
    var p2 = d.cc ? lireJson(root + 'pays/' + d.cc.toLowerCase() + '/conseils.json.gz').catch(function () { return null; }) : Promise.resolve(null);
    return Promise.all([p1, p2]).then(function (r) {
      textesCache[cle] = r[0];
      var T = r[0] || {}, C = r[1], passages = [];
      var NOMS = { histoire: 'Histoire', geographie: 'Géographie', culture: 'Culture', patrimoine: 'Patrimoine', gastronomie: 'Gastronomie', economie: 'Économie', sport: 'Sport', transports: 'Transports',
        comprendre: 'Comprendre', aller: 'S’y rendre', circuler: 'Se déplacer', voir: 'À voir', faire: 'À faire', manger: 'Manger', sortir: 'Sortir', loger: 'Se loger', acheter: 'Acheter', securite: 'Sécurité', sante: 'Santé', communiquer: 'Communiquer', respecter: 'Coutumes', environs: 'Aux environs',
        avertissements: 'Zones à éviter', entree_sortie: 'Entrée et sortie', lois_culture: 'Lois et coutumes', catastrophes_climat: 'Catastrophes naturelles et climat', aide: 'Aide sur place' };
      function ajouter(texte, src, rub) { (texte || '').split(/\n+/).forEach(function (p) { p = p.trim(); if (p.length > 40) passages.push({ t: p, src: src, rub: rub }); }); }
      if (T.resume) ajouter(T.resume, 'Wikipédia', 'En bref');
      Object.keys(T.textes || {}).forEach(function (k) { ajouter(T.textes[k], 'Wikipédia', NOMS[k] || k); });
      Object.keys(T.guide || {}).forEach(function (k) { ajouter(T.guide[k], 'Wikivoyage', NOMS[k] || k); });
      if (C && C.sections) Object.keys(C.sections).forEach(function (k) {
        var titre = NOMS[k] || k;
        C.sections[k].forEach(function (b) { if (b[0] === 't') titre = b[1]; else if (b[1].length > 40) passages.push({ t: b[1], src: 'Conseils aux voyageurs (Canada)', rub: titre, pays: 1 }); });
      });
      var ws = mots(q0, d.nom);
      if (!ws.length) return null;
      passages.forEach(function (p) {
        var n = norm(p.t), r_ = norm(p.rub), s = 0;
        ws.forEach(function (w) { if (n.indexOf(w) > -1) s += w.length > 6 ? 1.6 : 1; if (r_.indexOf(w) > -1) s += 1; });
        p.s = s;
      });
      var best = passages.reduce(function (m_, p) { return Math.max(m_, p.s); }, 0);
      if (best < 1) return null;
      var top = passages.filter(function (p) { return p.s >= best * 0.6; }).sort(function (a, b) { return b.s - a.s || a.t.length - b.t.length; }).slice(0, 3);
      if (!top.length) return null;
      function surligner(t) { var h = E(t.length > 450 ? t.slice(0, 450) + '…' : t); ws.forEach(function (w) { h = h.replace(new RegExp('(' + w.replace(/[^a-z0-9]/g, '') + '[a-zà-ÿ]*)', 'gi'), '<mark>$1</mark>'); }); return h; }
      return 'Voici ce que disent nos sources :' + top.map(function (p) { return '<p class="q-extrait">' + surligner(p.t) + '<br><small>' + E(p.src) + ' · ' + E(p.rub) + (p.pays ? ' (' + E(d.pays) + ')' : '') + '</small></p>'; }).join('')
        + (C ? '<p><a href="' + root + 'pays/' + d.cc.toLowerCase() + '/conseils/">Tous les conseils pour ' + E(d.pays) + '</a></p>' : '');
    });
  }

  function repondre(q0, d) {
    var q = ' ' + norm(q0) + ' ', a = function (re) { return re.test(q); };
    var m = moisCite(q.trim());
    // Questions précises que les sujets prévus comprendraient mal : directement la recherche dans les textes
    if (a(/(robinet|potable|moustique|piqure|tenue|vetement|pourboire|marchand|taxi|tuk|rickshaw|mendi|voler|vol a la tire|pickpocket|femme seule|enfant|bebe|handicap|animal|chien|chat|drone|alcool|ramadan|religieu|temple|mosquee|eglise|photo)/)) return null;
    if (a(/ (quelle heure|l heure|heure locale|decalage|fuseau)/)) return heure(d);
    if (a(/(visa|passeport|formalit| entrer | entree |frontiere|esta |autorisation)/)) {
      if (!d.formalites) return manque(d, 'les formalités');
      var p = a(/belge/) ? 'Passeport belge' : a(/suisse/) ? 'Passeport suisse' : a(/canad|quebec/) ? 'Passeport canadien' : 'Passeport français';
      return '<b>' + p + '</b> pour aller ' + aV(d.nom) + ' (' + E(d.pays) + ') : ' + E(d.formalites[p]) + '. '
        + liste(Object.keys(d.formalites).filter(function (k) { return k !== p; }), function (k) { return E(k) + ' : ' + E(d.formalites[k]); })
        + 'Vérifiez toujours avant de partir sur les Conseils aux voyageurs du ministère des Affaires étrangères.' + lien(d, 'formalites', 'Voir les formalités');
    }
    if (a(/(dangereu|danger|securi|risque|vigilance|attentat|est ce sur|est il sur|sans risque)/)) {
      if (!d.securite) return manque(d, 'le niveau de sécurité');
      return 'Niveau de sécurité du pays (' + E(d.pays) + ') : <b>' + d.securite.niveau + ' sur 4, ' + E(d.securite.libelle.toLowerCase()) + '</b>, selon l’indicateur des autorités américaines. Consultez aussi les Conseils aux voyageurs du ministère français, qui font foi.' + lien(d, 'formalites', 'Détails');
    }
    if (a(/(combien|prix|cout|coute|cher|budget|argent)/) && !a(/(habitant|km|kilometre|temps de vol|heure)/)) {
      if (!d.cout) return manque(d, 'les prix');
      var pr = d.cout.prix;
      return aV(d.nom, 1) + ', les prix sont en moyenne à <b>' + Math.round(d.cout.indice * 100) + ' %</b> de ceux de la France. Estimations par personne :'
        + liste(Object.keys(pr), function (k) { return E(k.charAt(0).toUpperCase() + k.slice(1)) + ' : ≈ ' + virg(pr[k]) + ' €'; })
        + 'Estimation à partir du niveau des prix national (Banque mondiale, ' + E(d.cout.annee) + ').' + lien(d, 'budget', 'Voir le budget');
    }
    if (a(/(monnaie|devise| change |taux|payer|euros? )/)) {
      return aV(d.nom, 1) + ', on paie en <b>' + E(d.monnaie || 'monnaie locale') + '</b>' + (d.devise ? ' (' + E(d.devise) + ')' : '') + '.'
        + (d.taux ? ' Aujourd’hui, 1 € vaut environ <b>' + virg(Math.round(d.taux * 100) / 100) + ' ' + E(d.devise) + '</b> (Banque centrale européenne).' : (d.devise === 'EUR' ? ' C’est l’euro, comme en France.' : ''));
    }
    if (a(/(langue|parle|parler)/)) return d.langues && d.langues.length ? 'Langue(s) parlée(s) ' + aV(d.nom) + ' : <b>' + E(d.langues.join(', ')) + '</b>.' : manque(d, 'les langues');
    if (a(/(indicatif|telephone)/)) return 'L’indicatif téléphonique est le <b>' + E(d.indicatif) + '</b> (' + E(d.pays) + ').';
    if (a(/capitale/)) return d.capitale === d.nom ? E(d.nom) + ' est la capitale du pays (' + E(d.pays) + ').' : 'La capitale du pays (' + E(d.pays) + ') est <b>' + E(d.capitale) + '</b>.';
    if (a(/ (maire|dirige)/)) return d.maire ? 'Le maire ' + deV(d.nom) + ' est <b>' + E(d.maire) + '</b> (source Wikidata).' : manque(d, 'le nom du maire');
    if (a(/(altitude|hauteur)/)) return d.altitude_m != null ? E(d.nom) + ' est à environ <b>' + nb(d.altitude_m) + ' m</b> d’altitude.' : manque(d, 'l’altitude');
    if (a(/(superficie|surface|km2)/)) return d.superficie_km2 ? E(d.nom) + ' s’étend sur <b>' + virg(d.superficie_km2) + ' km²</b>.' : manque(d, 'la superficie');
    if (a(/jumel/)) return d.jumelages ? E(d.nom) + ' est jumelée avec : ' + E(d.jumelages.join(', ')) + '.' : manque(d, 'les jumelages');
    if (a(/(ne a | nee | nes a|celebr|personnalit|connu)/)) return d.personnalites ? 'Personnalités nées ' + aV(d.nom) + ' :' + liste(d.personnalites, function (p) { return '<b>' + E(p.nom) + '</b>' + (p.description ? ', ' + E(p.description) : ''); }) + lien(d, 'personnalites', 'Voir la liste') : manque(d, 'les personnalités');
    if (a(/(unesco|patrimoine)/)) return d.unesco && d.unesco.length ? 'Inscrit au patrimoine mondial de l’UNESCO ' + aV(d.nom) + ' :' + liste(d.unesco, E) : 'Aucun site du patrimoine mondial n’est recensé dans ' + E(d.nom) + ' même.' + (d.alentours && d.alentours.some(function (x) { return x.patrimoine_mondial; }) ? ' Il y en a aux alentours :' + liste(d.alentours.filter(function (x) { return x.patrimoine_mondial; }), function (x) { return E(x.nom) + ' (' + virg(x.km) + ' km ' + E(x.direction) + ')'; }) : '');
    if (a(/(histoire|historique|fonde|fondation|origine|passe |ancien)/)) {
      if (!d.histoire && !d.fondation && !d.evenements) return manque(d, 'l’histoire');
      return (d.fondation ? '<b>Fondation : ' + E(d.fondation) + '.</b> ' : '') + (d.histoire ? '<p>' + E(d.histoire) + '</p>' : '')
        + (d.evenements ? 'Dates clés :' + liste(d.evenements.slice(0, 6), function (e) { return '<b>' + E(e.date || '?') + '</b> : ' + E(e.nom); }) : '') + lien(d, 'histoire', 'Lire toute l’histoire');
    }
    if (a(/(autour|alentour|excursion|environs|a proximite|aux environs|journee| pres de )/)) {
      if (!d.alentours) return manque(d, 'les sites des alentours') + (d.proches ? ' Villes voisines du guide : ' + d.proches.map(function (p) { return E(p.nom) + ' (' + p.km + ' km)'; }).join(', ') + '.' : '');
      return 'À visiter autour ' + deV(d.nom) + ' :' + liste(d.alentours, function (x) { return '<b>' + E(x.nom) + '</b>, ' + E(x.type.toLowerCase()) + ', ' + virg(x.km) + ' km ' + E(x.direction) + (x.patrimoine_mondial ? ' (patrimoine mondial)' : ''); }) + lien(d, 'alentours', 'Voir toutes les excursions');
    }
    if (m > -1 || a(/(quand partir|quand aller|meilleure periode|meilleur moment|meilleure saison|saison|climat|quel mois)/)) {
      if (!d.climat) return manque(d, 'le climat');
      if (m > -1) return climatMois(d, m) + lien(d, 'quand-partir', 'Voir le climat mois par mois');
      return (d.meilleurs_mois && d.meilleurs_mois.length ? 'Les mois les plus agréables pour visiter ' + E(d.nom) + ' : <b>' + d.meilleurs_mois.join(', ') + '</b>. ' : 'Aucun mois n’est à la fois tempéré et sec ' + aV(d.nom) + '. ')
        + (d.avis && d.avis.quand_partir ? E(d.avis.quand_partir) : '') + lien(d, 'quand-partir', 'Voir le climat mois par mois');
    }
    if (a(/(meteo|quel temps|temps fait|il fait|pleu|pluie|temperature|chaud|froid|neige|demain|cette semaine)/)) {
      if (d.meteo) return 'Prévisions pour ' + E(d.nom) + ' :' + liste(d.meteo, function (j) { return '<b>' + E(j.date.slice(8, 10) + '/' + j.date.slice(5, 7)) + '</b> : ' + E(j.ciel.toLowerCase()) + ', ' + Math.round(j.min) + ' à ' + Math.round(j.max) + ' °C' + (j.pluie ? ', ' + virg(j.pluie) + ' mm' : ''); }) + 'Mises à jour chaque nuit (Open-Meteo).';
      if (d.climat) return 'Pas encore de prévisions pour ' + E(d.nom) + ', mais voici le climat habituel. ' + climatMois(d, new Date().getMonth());
      return manque(d, 'la météo');
    }
    if (a(/ (air|pollution)/)) return d.air ? 'Qualité de l’air ' + aV(d.nom) + ' : <b>' + E(d.air.qualite) + '</b> (indice européen ' + d.air.indice + ', particules fines ' + d.air.pm25 + ' µg/m³).' : manque(d, 'la qualité de l’air');
    if (a(/(soleil|lever|coucher|duree du jour)/)) return soleil(d);
    if (a(/(ferie|fete nationale|jours? off)/)) return d.feries ? 'Prochains jours fériés (' + E(d.pays) + ') :' + liste(d.feries, function (f) { return '<b>' + E(f.date) + '</b> : ' + E(f.nom); }) : manque(d, 'les jours fériés');
    if (a(/(dormir|hotel|loger|logement|hebergement|auberge|nuit )/)) return d.dormir ? 'Où dormir ' + aV(d.nom) + ' (' + cpt(d.nb_dormir, 'adresse recensée', 'adresses recensées') + ') :' + liste(d.dormir, function (x) { return '<b>' + E(x.nom) + '</b>, ' + E(x.type.toLowerCase()) + (x.adresse ? ', ' + E(x.adresse) : ''); }) + lien(d, 'dormir', 'Voir toutes les adresses') : manque(d, 'les hébergements');
    if (a(/(manger|restaurant|resto|boire| bar |cafe|gastronom|specialit|plat |cuisine)/)) {
      var g = a(/(specialit|plat |gastronom|cuisine locale)/) && d.gastronomie ? '<p>' + E(d.gastronomie) + '</p>' : '';
      return g + (d.manger ? 'Où manger et boire ' + aV(d.nom) + ' (' + cpt(d.nb_manger, 'adresse recensée', 'adresses recensées') + ') :' + liste(d.manger, function (x) { return '<b>' + E(x.nom) + '</b>, ' + E(x.type.toLowerCase()) + (x.cuisine ? ', cuisine ' + E(x.cuisine) : ''); }) + lien(d, 'manger', 'Voir toutes les adresses') : (g || manque(d, 'les restaurants')));
    }
    if (a(/(activite|plage|baign|surf|ski|golf|sport|loisir|que faire|enfant)/)) return d.faire ? 'Activités ' + aV(d.nom) + ' :' + liste(d.faire, function (x) { return '<b>' + E(x.nom) + '</b>, ' + E(x.type.toLowerCase()); }) + lien(d, 'faire', 'Voir toutes les activités') : (d.voir ? 'Pas encore d’activités recensées, mais voici quoi voir :' + liste(d.voir.slice(0, 6), function (x) { return '<b>' + E(x.nom) + '</b>, ' + E(x.type.toLowerCase()); }) : manque(d, 'les activités'));
    if (a(/(voir|visiter|monument|musee|incontournable|site|interessant|decouvrir)/)) return d.voir ? 'À voir ' + aV(d.nom) + ' (' + cpt(d.nb_voir, 'lieu recensé', 'lieux recensés') + ') :' + liste(d.voir, function (x) { return '<b>' + E(x.nom) + '</b>, ' + E(x.type.toLowerCase()); }) + lien(d, 'voir', 'Voir tous les lieux') : manque(d, 'les lieux à visiter');
    if (a(/(conseil|astuce|eviter|erreur|avis|recommand|programme|itineraire)/)) return d.avis ? (d.avis.accroche ? '<p>' + E(d.avis.accroche) + '</p>' : '') + (d.avis.conseils ? 'Conseils :' + liste(d.avis.conseils.slice(0, 6), E) : '') + (d.avis.a_eviter ? 'À éviter :' + liste(d.avis.a_eviter, E) : '') + lien(d, 'avis', 'Lire notre avis') : manque(d, 'nos conseils');
    if (a(/(hopital|hopitaux|clinique|pharmacie|medecin|dentiste|urgence|ambulance|police|pompier|malade|sante)/)) {
      var h = '';
      if (d.urgences) h += 'Numéros d’urgence (' + E(d.pays) + ') :' + liste(d.urgences, function (x) { return '<b>' + E(x.numero) + '</b>' + (x.services.length ? ' : ' + E(x.services.join(', ')) : ''); });
      if (d.sante) h += 'Soins ' + aV(d.nom) + ' (' + cpt(d.nb_sante, 'adresse', 'adresses') + ') :' + liste(d.sante.slice(0, 5), function (x) { return '<b>' + E(x.nom) + '</b>, ' + E(x.type.toLowerCase()) + (x.urgences === 'oui' ? ', urgences' : '') + (x.telephone ? ', ' + E(x.telephone) : ''); });
      return h ? h + lien(d, 'sante', 'Voir la rubrique santé') : manque(d, 'les informations de santé');
    }
    if (a(/(arnaque|escroc|fraude|piege)/) && d.arnaques) return 'Arnaques signalées (' + E(d.pays) + ') :' + liste(d.arnaques, function (x) { return E(x); }) + '<p><a href="' + root + 'pays/' + d.cc.toLowerCase() + '/conseils/#arnaques">Toutes les arnaques signalées</a></p>';
    if (a(/(bonjour|merci|mots|phrase|dire|parler|langue|traduire|traduction)/) && d.phrases) return 'Quelques mots en ' + E(d.phrases.langue) + ' :' + liste(d.phrases.lignes.slice(0, 8), function (x) { return E(x); }) + lien(d, 'langue', 'Voir tous les mots utiles');
    if (a(/(prise|adaptateur|voltage|tension|electri)/) && d.pratique) return 'Prises ' + aV(d.nom) + ' : type ' + E((d.pratique.prises || []).join(', ')) + (d.pratique.tension ? ', ' + d.pratique.tension + ' V' : '') + '. ' + ((d.pratique.prises || []).every(function (x) { return 'CEF'.indexOf(x) > -1; }) ? 'Vos prises françaises conviennent.' : 'Prévoyez un adaptateur.');
    if (a(/(metro|tram|bus |transport en commun|transports en commun|conduite|conduire)/)) {
      var tx = '';
      if (d.transports && d.transports.lignes) tx += 'Transports en commun ' + aV(d.nom) + ' : ' + Object.keys(d.transports.lignes).map(function (k) { return d.transports.lignes[k] + ' ligne(s) de ' + k.replace('metro', 'métro'); }).join(', ') + '. ';
      if (d.pratique && d.pratique.conduite) tx += 'On conduit à ' + d.pratique.conduite + '.';
      if (tx) return tx + lien(d, 'transports-communs', 'Voir les transports');
    }
    if (a(/(danger|dangereux|zone|eviter|risque|attentat|terroris|vaccin|paludisme|loi|alcool|drogue|arnaque|seisme|cyclone|mousson)/) && d.conseils) {
      return E(d.pays) + ' : <b>' + E(d.conseils.texte) + '</b>.' + (d.conseils.zones.length ? ' Zones à éviter ou à risque :' + liste(d.conseils.zones, function (z) { return E(z); }) : '')
        + '<p><a href="' + root + 'pays/' + d.cc.toLowerCase() + '/conseils/">Tous les conseils : sécurité, santé et vaccins, lois, transports, catastrophes naturelles</a> (source : gouvernement du Canada ; la fiche du ministère français fait foi).</p>';
    }
    if (a(/(ambassade|consulat|consul)/)) {
      if (!d.representations) return manque(d, 'les ambassades et consulats');
      var NR = { FR: 'France', BE: 'Belgique', CH: 'Suisse', CA: 'Canada' };
      return 'Représentations les plus proches ' + deV(d.nom) + ' :' + liste(d.representations, function (x) { return NR[x.pays] + ' : <b>' + E(x.nom) + '</b>, ' + nb(x.km) + ' km' + (x.telephone ? ', ' + E(x.telephone) : ''); }) + lien(d, 'sante', 'Voir les détails');
    }
    if (a(/(gare|train|port |ferry|bateau|gare routiere|car )/) && d.acces) {
      var NA = { gares: 'Gares ferroviaires', routieres: 'Gares routières', ports: 'Ports (ferry)' }, out = '';
      Object.keys(NA).forEach(function (k) { if (d.acces[k]) out += NA[k] + ' :' + liste(d.acces[k], function (g) { return '<b>' + E(g.nom) + '</b>, ' + String(g.km).replace('.', ',') + ' km du centre'; }); });
      if (out) return out + lien(d, 'guide-aller', 'Voir les accès');
    }
    if (a(/(aeroport|aller a|s y rendre|comment aller|comment venir|arriver|train pour|bus pour)/)) {
      if (!d.aeroports && !d.aller) return manque(d, 'les moyens d’accès');
      return (d.aeroports ? 'Aéroports les plus proches ' + deV(d.nom).replace(/^de /, 'de ') + ' :' + liste(d.aeroports, function (x) { return '<b>' + E(x.nom) + '</b> (' + E(x.code) + '), ' + nb(x.km) + ' km' + (x.international ? ', international' : ''); }) : '')
        + (d.aller ? '<p>' + E(d.aller) + '</p>' : '') + lien(d, 'guide-aller', 'Voir comment s’y rendre');
    }
    if (a(/(distance|loin| km |kilometre|vol |avion|combien de temps|depuis paris|de paris)/)) return E(d.nom) + ' est à environ <b>' + nb(d.distance_paris) + ' km</b> de Paris à vol d’oiseau' + (d.distance_paris > 350 ? ', soit environ ' + Math.max(1, Math.round(d.distance_paris / 800 + 0.5)) + ' h de vol sans escale.' : ', faisable en train ou en voiture.');
    if (a(/(habitant|population|combien de personnes|taille de la ville|grande ville)/)) return E(d.nom) + ' compte <b>' + nb(d.population) + ' habitants</b> et se classe ' + nb(d.rang) + 'ᵉ ville du guide.';
    if (a(/(voisin|proche|ville a cote)/)) return 'Villes du guide les plus proches ' + deV(d.nom) + ' :' + liste(d.proches, function (p) { return '<a href="' + root + 'villes/' + p.slug + '/">' + E(p.nom) + '</a> (' + p.km + ' km)'; });
    return null;  // pas de sujet reconnu : recherche dans les textes (voir chercherTextes)
  }
  var reponses = null;  // réponses rédigées aux questions des lecteurs (static/reponses.json, complété chaque jour)
  function chargerReponses() {
    if (reponses) return Promise.resolve(reponses);
    return fetch(root + 'static/reponses.json').then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; })
      .then(function (l) { reponses = l || []; return reponses; });
  }
  function motsCles(t) { return norm(t).split(' ').filter(function (m) { return m.length > 2 && !vide[m]; }); }
  function reponseLecteur(q, d, liste) {
    var mq = motsCles(q), best = null, score = 0;
    if (!mq.length) return null;
    liste.forEach(function (x) {
      if (x.ville && x.ville !== d.slug) return;
      var mx = motsCles(x.q), communs = mq.filter(function (m) { return mx.indexOf(m) > -1; }).length;
      var s = communs / Math.max(mq.length, mx.length);
      if (s > score) { score = s; best = x; }
    });
    return score >= 0.6 ? best : null;
  }
  var IA_URL = '';  // relais IA de Pablo (Cloudflare) ; vide = bouton masqué
  function boutonIA(q, d) {
    if (!IA_URL) return '';
    return '<p><button type="button" class="q-btn q-ia" data-q="' + E(q) + '" data-slug="' + E(d.slug || '') + '">✨ Demander à l’IA</button></p><div class="q-ia-rep"></div>';
  }
  function miseIA(t) {
    var out = '', liste = false;
    E(t).split(/\n+/).forEach(function (l) {
      l = l.trim(); if (!l) return;
      l = l.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
      if (/^[-•]\s+/.test(l)) { if (!liste) { out += '<ul>'; liste = true; } out += '<li>' + l.replace(/^[-•]\s+/, '') + '</li>'; }
      else { if (liste) { out += '</ul>'; liste = false; } out += '<p>' + l.replace(/^#+\s/, '') + '</p>'; }
    });
    return out + (liste ? '</ul>' : '');
  }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.q-ia');
    if (!b) return;
    var zone = b.parentNode.nextElementSibling, q = b.getAttribute('data-q'), d = cache[b.getAttribute('data-slug')] || {};
    zone.innerHTML = '<p class="q-vide">L’IA rédige sa réponse…</p>';
    var ctx = d.nom ? ('Ville : ' + d.nom + ' (' + (d.pays || '') + '), ' + (d.population || '') + ' habitants. ' + (d.resume || '')).slice(0, 4000) : '';
    fetch(IA_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ site: 'dix-mille-escales', question: q, contexte: ctx }) })
      .then(function (x) { return x.json(); })
      .then(function (r) {
        zone.innerHTML = r.reponse ? miseIA(r.reponse) + '<p class="note">Réponse rédigée par une intelligence artificielle (Claude) : elle peut contenir des erreurs. Vérifiez les points importants (visas, santé, sécurité) auprès de sources officielles.</p>'
          : '<p class="q-vide">' + E(r.erreur || 'Pas de réponse.') + '</p>';
      }).catch(function () { zone.innerHTML = '<p class="q-vide">L’IA est injoignable pour le moment. Réessayez dans un instant.</p>'; });
  });
  function envoyer(q, d) {  // question sans réponse : transmise aux robots, la réponse est ajoutée au site sous 24 h
    var depot = 'pablopacaut17-sudo/dix-mille-escales', m = location.hostname.match(/^([^.]+)\.github\.io$/), seg = location.pathname.split('/').filter(Boolean);
    if (m && seg.length) depot = m[1] + '/' + seg[0];
    var url = 'https://github.com/' + depot + '/issues/new?labels=question&title=' + encodeURIComponent('Question – ' + d.nom + ' – ' + q.slice(0, 120))
      + '&body=' + encodeURIComponent('Ville : ' + d.nom + ' (' + (d.slug || '') + ')\nQuestion : ' + q + '\n\n(La réponse sera ajoutée au site sous 24 h environ, puis indiquée ici.)');
    return '<p class="q-envoi">Pas la réponse que vous cherchiez ? <a href="' + url + '" target="_blank" rel="noopener">Envoyez votre question</a> : elle sera traitée sous 24 h et sa réponse ajoutée au site (compte GitHub gratuit nécessaire).</p>';
  }
  function portrait(d) {
    return '<b>' + E(d.nom) + '</b> (' + E(d.pays) + '), ' + nb(d.population) + ' habitants.' + (d.resume ? '<p>' + E(d.resume) + '</p>' : '')
      + ' Je peux vous répondre sur : visa, météo, quand partir, budget, monnaie, langue, heure, que voir, où manger, où dormir, activités, alentours, histoire, sécurité…'
      + lien(d, '', 'Ouvrir la fiche complète') + ' <span class="q-infos">' + nb(d.infos) + ' informations dans cette fiche.</span>';
  }

  boites.forEach(function (b) {
    var input = b.querySelector('.q-input'), rep = b.querySelector('.q-rep'), form = b.querySelector('.q-form'), sugg = b.querySelector('.q-sugg');
    var villePage = b.getAttribute('data-ville') || '';
    var exemples = villePage
      ? ['Faut-il un visa ?', 'Quel temps fait-il cette semaine ?', 'Quand partir ?', 'Combien coûte un repas ?', 'Que voir ?', 'Où manger ?', 'Que faire aux alentours ?', 'Quelle heure est-il là-bas ?', 'Est-ce dangereux ?', 'Quelle langue parle-t-on ?', 'Quelle est son histoire ?', 'Qui est né ici ?']
      : ['Faut-il un visa pour Tokyo ?', 'Quel temps fait-il à New York ?', 'Quand partir à Marrakech ?', 'Combien coûte un repas à Lisbonne ?', 'Que voir à Rome ?', 'Quelle heure est-il à Sydney ?', 'Que faire autour de Barcelone ?', 'Quelle monnaie au Caire ?', 'Qui est né à Vienne ?', 'Quelle est l’histoire de Kyoto ?', 'Où dormir à Prague ?', 'Quel temps en avril à Bangkok ?'];
    sugg.innerHTML = exemples.map(function (e) { return '<button type="button">' + E(e) + '</button>'; }).join('');
    sugg.querySelectorAll('button').forEach(function (bt) { bt.addEventListener('click', function () { input.value = bt.textContent; demander(); }); });
    var derniere = villePage;
    function demander() {
      var q = input.value.trim();
      if (q.length < 3) { rep.innerHTML = '<p class="q-vide">Posez une question, par exemple « Faut-il un visa pour le Japon ? ».</p>'; return; }
      rep.innerHTML = '<p class="q-vide">Je cherche…</p>';
      chargerIndex(function (err) {
        if (err) { rep.innerHTML = '<p class="q-vide">La recherche est indisponible pour le moment. Réessayez dans un instant.</p>'; return; }
        chercherCelebre(q).catch(function () { return null; }).then(function (cel) {
        var vc = trouverVille(q);
        if (cel && !(vc && motsLieu(cel[0]).join(' ') === motsLieu(vc[0]).join(' '))) { rep.innerHTML = repCelebre(cel); return; }
        var v = trouverVille(q), slug = v ? v[1] : derniere;
        if (!slug) { rep.innerHTML = '<p class="q-vide">De quelle ville parlez-vous ? Ajoutez son nom à la question, par exemple « Quel temps fait-il à Lisbonne ? ».</p>' + boutonIA(q, {}); return; }
        derniere = slug;
        charger(slug, function (d) {
          if (!d) { rep.innerHTML = '<p class="q-vide">Impossible de charger la fiche de cette ville pour le moment.</p>'; return; }
          var tete = '<div class="q-ville">' + E(d.nom) + ' · ' + E(d.pays) + '</div><div class="q-texte">';
          chargerLieux(slug).then(function (L) {
            var f = lieuCite(q, L);
            if (f) { rep.innerHTML = tete + repLieu(f, d) + '</div>'; return; }
            var r_ = repondre(q, d);
            if (r_) { rep.innerHTML = tete + r_ + '</div>'; return; }
            chargerReponses().then(function (liste) {
            var rl = reponseLecteur(q, d, liste);
            if (rl) { rep.innerHTML = tete + '<p>' + E(rl.r).replace(/\n/g, '<br>') + '</p><p class="note">Réponse rédigée le ' + E(rl.date || '') + ' à la question d’un lecteur' + (rl.source ? ' · source : ' + E(rl.source) : '') + '.</p></div>'; return; }
            rep.innerHTML = tete + '<p class="q-vide">Je cherche dans tous les textes de ' + E(d.nom) + '…</p></div>';
            chercherTextes(q, d).then(function (h) { rep.innerHTML = tete + (h || portrait(d)) + boutonIA(q, d) + envoyer(q, d) + '</div>'; }).catch(function () { rep.innerHTML = tete + portrait(d) + boutonIA(q, d) + envoyer(q, d) + '</div>'; });
            });
          });
        });
        });
      });
    }
    form.addEventListener('submit', function (e) { e.preventDefault(); demander(); });
    input.addEventListener('focus', function () { chargerIndex(function () {}); }, { once: true });
  });
})();
