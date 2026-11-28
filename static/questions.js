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

  function soleil(d, mois) {
    var quand = Date.now(), dit = 'Aujourd’hui';
    if (mois > -1) {  // « lever du soleil à Reykjavik en juin » : le 15 du mois cité (à venir)
      var n0 = new Date(), an = n0.getFullYear() + (mois < n0.getMonth() ? 1 : 0);
      quand = Date.UTC(an, mois, 15, 12); dit = 'Le 15 ' + MOIS_AFF[mois];
    }
    var R = Math.PI / 180, jd = quand / 864e5 + 2440587.5, n = Math.round(jd - 2451545 - 0.0009 + d.lon / 360), Js = n + 0.0009 - d.lon / 360;
    var M = (357.5291 + 0.98560028 * Js) % 360, C = 1.9148 * Math.sin(M * R) + 0.02 * Math.sin(2 * M * R) + 0.0003 * Math.sin(3 * M * R);
    var L = (M + C + 282.9372) % 360, Jt = 2451545 + Js + 0.0053 * Math.sin(M * R) - 0.0069 * Math.sin(2 * L * R);
    var sd = Math.sin(L * R) * Math.sin(23.4397 * R), cd = Math.cos(Math.asin(sd));
    var cw = (Math.sin(-0.833 * R) - Math.sin(d.lat * R) * sd) / (Math.cos(d.lat * R) * cd);
    if (cw < -1) return (mois > -1 ? 'En ' + MOIS_AFF[mois] + ', le' : 'Le') + ' soleil ne se couche pas ' + (mois > -1 ? '' : 'en ce moment ') + aV(d.nom) + ' (soleil de minuit).';
    if (cw > 1) return (mois > -1 ? 'En ' + MOIS_AFF[mois] + ', le' : 'Le') + ' soleil ne se lève pas ' + (mois > -1 ? '' : 'en ce moment ') + aV(d.nom) + ' (nuit polaire).';
    var w = Math.acos(cw) / R, f = function (j) { return new Intl.DateTimeFormat('fr-FR', { timeZone: d.fuseau, hour: '2-digit', minute: '2-digit' }).format(new Date((j - 2440587.5) * 864e5)); };
    var duree = w / 180 * 24;
    return dit + ' ' + aV(d.nom) + ', le soleil se lève vers <b>' + f(Jt - w / 360) + '</b> et se couche vers <b>' + f(Jt + w / 360) + '</b> (heure locale), soit environ ' + Math.floor(duree) + ' h ' + String(Math.round(duree % 1 * 60)).padStart(2, '0') + ' de jour.';
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
    if (c.superficie && !(c.hauteur && c.superficie >= 1e4)) p.push('superficie ' + (c.superficie >= 1e6 ? String(Math.round(c.superficie / 1e4) / 100).replace('.', ',') + ' km²' : c.superficie >= 1e4 ? nb(Math.round(c.superficie / 1e4)) + ' ha' : nb(Math.round(c.superficie)) + ' m²'));
    var dt = c.creation || c.debut || c.ouverture; if (dt) p.push('date : ' + (dt < 0 ? (-dt) + ' av. J.-C.' : dt));
    if (c.architecte) p.push((c.architecte.length > 1 ? 'architectes : ' : 'architecte : ') + c.architecte.join(' et ')); if (c.style) p.push('style : ' + c.style.join(', '));
    if (c.frequentation) p.push('fréquentation : ' + nb(c.frequentation) + ' voyageurs par an' + (c.frequentation_annee ? ' (' + c.frequentation_annee + ')' : ''));
    if (c.visiteurs_an) p.push(nb(c.visiteurs_an) + ' visiteurs par an' + (c.visiteurs_annee ? ' (' + c.visiteurs_annee + ')' : ''));
    if (c.capacite) p.push('capacité : ' + nb(c.capacite) + ' places');
    return p.join(' · ');
  }
  /* Lieux célèbres de tout le guide (titres Wikipédia) : répond à « hauteur de la tour Montparnasse » sans ville citée */
  var LIENS = { de: 1, du: 1, des: 1, la: 1, le: 1, les: 1, l: 1, d: 1, et: 1, a: 1, au: 1, aux: 1, en: 1, sur: 1, sous: 1, the: 1, of: 1 };
  var CLES = { ha: 'hauteur', lo: 'longueur', su: 'superficie', la: 'largeur', al: 'altitude', vi: 'visiteurs_an', va: 'visiteurs_annee', cr: 'creation', ou: 'ouverture', ar: 'architecte', fr: 'frequentation', fa: 'frequentation_annee', ca: 'capacite' };
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
      var meilleur = null, lg = 0, pmax = -1;
      listes.forEach(function (l) {
        l.forEach(function (x) {
          var mt = motsLieu(x[0]);
          if (mt.length > 2 && GENERIQUES[mt[0]]) mt = mt.slice(1);  // « avenue des Champs-Élysées » : « Champs-Élysées » suffit
          if (!mt.length) return;
          var s0 = mt.join('');
          if (mt.length < 2 && s0.length < 6) return;
          if (!mt.every(function (m) { return present[m] || present[m.replace(/s$/, '')]; })) return;
          // les mots du nom qui ne sont que le nom de la ville comptent peu : « Monument de la Paix à Washington » n'est pas le « Washington Monument »
          var mv = {}; motsLieu(x[2]).forEach(function (m) { mv[m] = 1; });
          var s = mt.filter(function (m) { return !mv[m]; }).join('') || s0.slice(0, 5);
          if (s.length < lg) return;
          // à nom égal (« Gare centrale »), la ville citée dans la question l'emporte, puis le lieu le plus fréquenté
          var me = x[3] || {}, poids = (motsLieu(x[2]).every(function (m) { return present[m]; }) ? 1e12 : 0) + (me.fr || 0) + (me.vi || 0) + (me.ca || 0);
          if (s.length > lg || poids > pmax) { meilleur = x; lg = s.length; pmax = poids; }
        });
      });
      return meilleur;
    });
  }
  function repCelebre(x) {
    var c = {}, m = x[3] || {};
    Object.keys(m).forEach(function (k) { if (CLES[k]) c[CLES[k]] = m[k]; });
    var infos = carac(c);
    var photo = m.ph ? '<figure class="q-photo" style="margin:.4rem 0 .8rem"><img src="https://commons.wikimedia.org/wiki/Special:FilePath/' + encodeURIComponent(m.ph) + '?width=640" alt="' + E(x[0]) + '" loading="lazy" decoding="async" style="width:100%;max-height:300px;object-fit:cover;border-radius:12px">'
      + '<figcaption class="note">Photo : <a href="https://commons.wikimedia.org/wiki/File:' + encodeURIComponent(m.ph) + '" target="_blank" rel="noopener">Wikimedia Commons (auteur et licence)</a></figcaption></figure>' : '';
    return '<div class="q-ville">' + E(x[2]) + '</div>' + photo + '<div class="q-texte"><b>' + E(x[0]) + '</b>' + (infos ? ' : ' + E(infos) + '.' : '.')
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
  function lieuCite(q0, lieux, ville) {
    var qn = ' ' + norm(q0).replace(/[^a-z0-9 ]/g, ' ') + ' ', meilleur = null, lg = 0;
    var vn = ' ' + norm(ville || '').replace(/[^a-z0-9 ]/g, ' ') + ' ';
    lieux.forEach(function (f) {
      var ws = norm(f.nom).replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(function (w) { return w.length >= 3 && VIDES.indexOf(' ' + w + ' ') < 0; });
      if (!ws.length || ws.join('').length < 5) return;
      if (ws.every(function (w) { return vn.indexOf(' ' + w + ' ') > -1; })) return;  // « Quimper » (la gare) : c'est le nom de la ville, pas un lieu cité
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
  /* « Que faire en 2 jours à Lisbonne ? » : programme jour par jour à partir des lieux à voir de la fiche,
     regroupés par proximité (un quartier par jour), avec une adresse pour manger près de chaque étape. Rien n'est stocké. */
  var NB_JOURS = { un: 1, une: 1, deux: 2, trois: 3, quatre: 4, cinq: 5 };
  function joursDemandes(q) {
    var n = norm(q), m = n.match(/\b([1-5]|un|une|deux|trois|quatre|cinq) (jours?|journees?)\b/);
    var k = m ? (NB_JOURS[m[1]] || +m[1]) : /week ?end/.test(n) ? 2 : 0;
    if (!k || !/(faire|visiter|voir|programme|itineraire|sejour|passer|decouvrir|circuit|week ?end)/.test(n)) return 0;
    return k;
  }
  function kmEntre(a, b) {
    var r = Math.PI / 180, x = (b.lon - a.lon) * r * Math.cos((a.lat + b.lat) * r / 2), y = (b.lat - a.lat) * r;
    return 6371 * Math.sqrt(x * x + y * y);
  }
  function programme(q, d, L) {
    var k = joursDemandes(q);
    if (!k) return null;
    var centre = d.lat != null ? { lat: d.lat, lon: d.lon } : null;
    var voir = L.filter(function (f) { return f.rubrique === 'voir' && f.lat != null && f.lon != null && (!centre || kmEntre(centre, f) < 12); });
    if (voir.length < 2) return null;
    // incontournables d'abord (Wikidata ou patrimoine mondial), puis l'ordre de la fiche (les plus renseignés)
    voir = voir.map(function (f, i) { return [f, (f.patrimoine_mondial ? 0 : f.wikidata ? 1 : 2) * 1e4 + i]; }).sort(function (a, b) { return a[1] - b[1]; }).map(function (x) { return x[0]; });
    var parJour = 4, choix = voir.slice(0, Math.min(voir.length, k * parJour * 2));
    k = Math.max(1, Math.min(k, Math.floor(choix.length / 2)));
    // un point de départ par jour : les lieux les mieux classés, assez éloignés les uns des autres
    var germes = [];
    choix.forEach(function (f) { if (germes.length < k && germes.every(function (g) { return kmEntre(g, f) > 1.2; })) germes.push(f); });
    choix.forEach(function (f) { if (germes.length < k && germes.indexOf(f) < 0) germes.push(f); });
    var jours = germes.map(function (g) { return [g]; });
    choix.forEach(function (f) {
      if (germes.indexOf(f) > -1) return;
      var best = -1, dm = 1e9;
      jours.forEach(function (j, i) { var dd = kmEntre(j[0], f); if (j.length < parJour && dd < dm) { dm = dd; best = i; } });
      if (best > -1 && dm < 6) jours[best].push(f);
    });
    // dans chaque journée, on va de proche en proche
    jours = jours.map(function (j) {
      var reste = j.slice(1), ordre = [j[0]];
      while (reste.length) { var der = ordre[ordre.length - 1], iMin = 0; reste.forEach(function (f, i) { if (kmEntre(der, f) < kmEntre(der, reste[iMin])) iMin = i; }); ordre.push(reste.splice(iMin, 1)[0]); }
      return ordre;
    });
    var manger = L.filter(function (f) { return f.rubrique === 'manger' && f.lat != null && f.lon != null; }), pris = {};
    var h = (k > 1 ? 'Proposition de programme sur <b>' + k + ' jours</b> ' : 'Proposition de programme pour <b>une journée</b> ') + aV(d.nom) + ', un secteur par jour pour limiter les trajets :';
    jours.forEach(function (j, i) {
      var tot = 0; for (var x = 1; x < j.length; x++) tot += kmEntre(j[x - 1], j[x]);
      var mid = j[Math.floor((j.length - 1) / 2)], resto = null, dr = 1e9;
      manger.forEach(function (f) { var dd = kmEntre(mid, f); if (!pris[f.nom] && dd < dr) { dr = dd; resto = f; } });
      if (resto && dr < 1.5) pris[resto.nom] = 1; else resto = null;
      h += '<p><b>' + (k > 1 ? 'Jour ' + (i + 1) : 'Le programme') + '</b> (' + (tot < 1 ? 'moins d’1 km' : 'environ ' + virg(Math.round(tot * 10) / 10) + ' km') + ' entre les étapes)</p>'
        + liste(j, function (f) { return '<b>' + E(f.nom) + '</b>, ' + E((f.type || '').toLowerCase()) + ((f.wikidata || f.patrimoine_mondial) ? ' ★' : '') + (f.horaires ? ' · ' + E(f.horaires) : ''); })
        + (resto ? '<p class="note">Pour manger près de là : ' + E(resto.nom) + (resto.cuisine ? ' (' + E(resto.cuisine) + ')' : '') + ', à ' + (dr < 0.1 ? 'quelques pas' : virg(Math.round(dr * 10) / 10) + ' km') + '.</p>' : '');
    });
    return h + '<p class="note">Programme calculé à partir des lieux de la fiche (OpenStreetMap, Wikidata), regroupés par proximité ; ★ = incontournable. Vérifiez les horaires avant de partir.</p>' + lien(d, 'voir', 'Voir tous les lieux');
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
    if (a(/(lever du soleil|coucher du soleil|se leve|se couche|duree du jour|longueur du jour|nuit polaire|soleil de minuit)/)) return soleil(d, m);
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
    if (a(/(lever|coucher|duree du jour|longueur du jour|nuit polaire|soleil de minuit)/) || (a(/soleil/) && !a(/heures? de soleil|ensoleill/))) return soleil(d, m);
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


  /* Deux villes dans la même question (« distance Paris Rome », « Séville ou Malaga en avril ? », « décalage horaire
     entre Paris et Tokyo ») : la réponse est calculée à partir des fiches des deux villes. */
  function deuxVilles(q) {
    var mots = norm(q).split(' '), trouves = [], i = 0;
    while (i < mots.length && trouves.length < 3) {
      var pris = 0;
      for (var l = Math.min(5, mots.length - i); l >= 1; l--) {
        var g = mots.slice(i, i + l).join(' ');
        if (l === 1 && (vide[g] || g.length < 3)) continue;
        if (noms[g]) { if (!trouves.some(function (r) { return r[1] === noms[g][1]; })) trouves.push(noms[g]); pris = l; break; }
      }
      i += pris || 1;
    }
    return trouves.length === 2 ? trouves : null;
  }
  var COMPARE = /(distance|km|kilometre|loin|combien de temps|duree|trajet|vol |en avion| ou | vs |versus|compar|difference|decalage|plus chaud|plus froid|plus de soleil|moins de pluie|plus de pluie|mieux|entre )/;
  function decalage(z1, z2) {
    var now = new Date();
    function t(z) { var o = {}; new Intl.DateTimeFormat('en-US', { timeZone: z, hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).formatToParts(now).forEach(function (x) { o[x.type] = x.value; }); return Date.UTC(+o.year, +o.month - 1, +o.day, +o.hour % 24, +o.minute); }
    try { return (t(z2) - t(z1)) / 36e5; } catch (e) { return null; }
  }
  function comparer(a, b, q0) {
    var q = ' ' + norm(q0) + ' ', R = Math.PI / 180, h = '';
    if (a.lat != null && b.lat != null) {
      var x = Math.sin((b.lat - a.lat) * R / 2), y = Math.sin((b.lon - a.lon) * R / 2);
      var km = 2 * 6371 * Math.asin(Math.sqrt(x * x + Math.cos(a.lat * R) * Math.cos(b.lat * R) * y * y));
      var vol = km / 820 + 0.5, hv = Math.floor(vol), mv = Math.round((vol - hv) * 60 / 5) * 5;
      if (mv === 60) { hv++; mv = 0; }
      h += '<p>Distance à vol d’oiseau entre ' + E(a.nom) + ' et ' + E(b.nom) + ' : <b>' + nb(Math.round(km)) + ' km</b>.'
        + (km > 250 ? ' En avion, un vol direct dure environ <b>' + hv + ' h ' + String(mv).padStart(2, '0') + '</b> (estimation à 820 km/h de moyenne ; la durée réelle dépend de la route suivie et des vents).' : '')
        + (km < 700 ? ' Sur une telle distance, le train ou la route sont souvent aussi rapides que l’avion, de centre-ville à centre-ville.' : '') + '</p>';
    }
    if (a.fuseau && b.fuseau) {
      var dec = decalage(a.fuseau, b.fuseau);
      if (dec != null) h += '<p>Décalage horaire : ' + (dec === 0 ? 'aucun, c’est la même heure.' : '<b>' + (Math.abs(dec) + ' h').replace('.5 h', ' h 30') + '</b> ' + (dec > 0 ? 'de plus' : 'de moins') + ' ' + aV(b.nom) + ' qu’' + aV(a.nom).replace(/^à /, 'à ') + ' en ce moment.') + '</p>';
    }
    var m = moisCite(q.trim()); if (m < 0) m = new Date().getMonth();
    if (a.climat && b.climat && a.climat[m] && b.climat[m]) {
      var ca = a.climat[m], cb = b.climat[m];
      var plus = Math.abs(ca.tmax - cb.tmax) < 1 ? 'la même chaleur dans les deux villes' : (ca.tmax > cb.tmax ? E(a.nom) : E(b.nom)) + ' est la plus chaude';
      h += '<p>En ' + MOIS_AFF[m] + ' : ' + E(a.nom) + ' ' + Math.round(ca.tmax) + ' °C l’après-midi et ' + ca.pluie_mm + ' mm de pluie' + (ca.soleil_h != null ? ', ' + virg(ca.soleil_h) + ' h de soleil par jour' : '')
        + ' ; ' + E(b.nom) + ' ' + Math.round(cb.tmax) + ' °C et ' + cb.pluie_mm + ' mm' + (cb.soleil_h != null ? ', ' + virg(cb.soleil_h) + ' h de soleil' : '') + '. <b>' + plus + '</b>'
        + (Math.abs(ca.pluie_mm - cb.pluie_mm) >= 10 ? ', et ' + (ca.pluie_mm < cb.pluie_mm ? E(a.nom) : E(b.nom)) + ' est la moins pluvieuse' : '') + '.</p>';
    }
    return h ? h + '<p>' + lien(a, '', 'Fiche ' + deV(a.nom)) + ' · ' + lien(b, '', 'Fiche ' + deV(b.nom)) + '</p>' : '';
  }

  /* Question chiffrée sur un lieu (« fréquentation de la gare de Lyon ») : si le site n'a pas ce chiffre, il le dit
     franchement et propose l'IA, au lieu de répondre à côté avec un autre lieu ou les textes de la ville. */
  var CHIFFRES = [['fr', /(frequentation|voyageurs|passagers|trafic)/, 'la fréquentation'], ['ca', /(capacite|nombre de places|combien de places|spectateurs|jauge)/, 'la capacité'],
    ['vi', /(visiteurs|combien de visites|entrees par an)/, 'le nombre de visiteurs'], ['ha', /(hauteur|combien de metres|quelle taille|mesure t)/, 'la hauteur'],
    ['su', /(superficie|surface)/, 'la superficie'], ['lo', /(longueur|long fait|combien de kilometres de long)/, 'la longueur'],
    ['cr', /(date de construction|construit|construite|batie?|inaugur|annee d ouverture|ouvert en|quand a ete)/, 'la date de construction']];
  var MOTS_LIEUX = /(gare|aeroport|stade|arena|tour |musee|pont |cathedrale|chateau|salle |theatre|opera|monument|basilique|eglise|gratte ciel|immeuble|batiment|zoo|parc d attraction|statue|barrage|phare|palais|mosquee|temple|abbaye|viaduc|tunnel|port |station)/;
  function chiffreDemande(q0) {
    var q = ' ' + norm(q0).replace(/[^a-z0-9 ]/g, ' ') + ' ';
    for (var i = 0; i < CHIFFRES.length; i++) if (CHIFFRES[i][1].test(q)) return CHIFFRES[i];
    return null;
  }
  function lieuDemande(q0) {
    var mots = q0.replace(/[?!.]+\s*$/, '').trim().split(/\s+/);
    for (var i = 0; i < mots.length; i++) {
      var reste = ' ' + norm(mots.slice(i).join(' ')).replace(/[^a-z0-9 ]/g, ' ').replace(/^(l|d) /, '') + ' ', m = reste.match(MOTS_LIEUX);
      if (!m) return '';
      if (reste.indexOf(m[1]) === 1) return mots.slice(i).join(' ').replace(/^[ldLD][’']/, '').trim();
    }
    return '';
  }
  function pasLeChiffre(ch, quoi) {
    return '<p class="q-vide">Je n’ai pas encore ' + ch[2] + ' ' + deLieu(quoi) + ' dans le guide. Plutôt que de vous répondre à côté, je vous propose de demander à l’IA.</p>';
  }
  function deLieu(t) { t = String(t || '').trim(); var n = norm(t); return /^(le|la|les|l )/.test(n) ? 'de ' + E(t) : /^(du |de |des |d )/.test(n) ? E(t) : 'de « ' + E(t) + ' »'; }
  var IA_URL = 'https://relais-ia.pablopacaut17.workers.dev';  // relais IA de Pablo (Cloudflare) ; vide = bouton masqué
  function boutonIA(q, d, petit) {
    if (!IA_URL) return '';
    var faux = ' <button type="button" class="q-btn q-faux" data-q="' + E(q) + '" data-slug="' + E(d.slug || '') + '">Signaler une erreur</button>';
    if (petit) return '<p class="note">Pas la réponse attendue ? <button type="button" class="q-btn q-ia" data-q="' + E(q) + '" data-slug="' + E(d.slug || '') + '">✨ Demander à l’IA</button>' + faux + '</p><div class="q-ia-rep"></div>';
    return '<p><button type="button" class="q-btn q-ia" data-q="' + E(q) + '" data-slug="' + E(d.slug || '') + '">✨ Demander à l’IA</button></p><div class="q-ia-rep"></div>';
  }
  function miseIA(t) {
    var out = '', liste = false;
    E(t).split(/\n+/).forEach(function (l) {
      l = l.trim(); if (!l) return;
      l = l.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
      if (/^([-•*]|\d+[.)])\s+/.test(l)) { if (!liste) { out += '<ul>'; liste = true; } out += '<li>' + l.replace(/^([-•*]|\d+[.)])\s+/, '') + '</li>'; }
      else { if (liste) { out += '</ul>'; liste = false; } out += '<p>' + l.replace(/^#+\s/, '') + '</p>'; }
    });
    return out + (liste ? '</ul>' : '');
  }
  /* Questions sans réponse et erreurs signalées : notées gratuitement par le relais (version 3 et plus), puis traitées
     en priorité par les tâches d'amélioration et le chasseur d'erreurs. Rien n'est envoyé si le relais est plus ancien. */
  var relaisV3 = null;
  function versionRelais() {
    if (!relaisV3) relaisV3 = fetch(IA_URL + '?version=1').then(function (r) { return r.ok ? r.json() : {}; }).then(function (j) { return (j.version || 0) >= 3; }).catch(function () { return false; });
    return relaisV3;
  }
  function noter(type, q, slug, extra) {
    if (!IA_URL || !window.fetch) return Promise.resolve(false);
    return versionRelais().then(function (ok) {
      if (!ok) return false;
      var b = { site: 'dix-mille-escales', type: type, question: q, slug: slug || '' };
      for (var k in extra || {}) b[k] = extra[k];
      return fetch(IA_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }).then(function () { return true; });
    }).catch(function () { return false; });
  }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.q-faux');
    if (!b) return;
    var zone = b.closest('.q-rep') || document.body, note = window.prompt('Qu’est-ce qui est faux ? (facultatif)', '') ;
    if (note === null) return;
    noter('signal', b.getAttribute('data-q'), b.getAttribute('data-slug'), { reponse: (zone.innerText || '').slice(0, 600), note: note }).then(function (ok) {
      b.textContent = ok ? 'Merci, c’est noté : ce sera vérifié.' : 'Signalement impossible pour le moment.'; b.disabled = true;
    });
  });
  /* Mémoire du relais IA : si la même question a déjà été posée à l'IA, sa réponse s'affiche tout de suite, gratuitement */
  function memoireIA(rep, q, d) {
    if (!IA_URL || !window.fetch) return;
    noter('sansreponse', q, (d && d.slug) || '');
    fetch(IA_URL + '?site=dix-mille-escales&q=' + encodeURIComponent(q) + '&slug=' + encodeURIComponent((d && d.slug) || ''))
      .then(function (x) { return x.ok ? x.json() : null; })
      .then(function (r) {
        var z = rep.querySelector('.q-ia-rep');
        if (!r || !r.reponse || !z || z.innerHTML) return;
        z.innerHTML = '<p class="note">Réponse de l’IA (Claude) à la même question, donnée le ' + E(dateFr(r.date)) + ' :</p>' + miseIA(r.reponse)
          + '<p class="note">Réponse rédigée par une intelligence artificielle : elle peut contenir des erreurs. Vérifiez les points importants auprès de sources officielles.</p>';
        var b = rep.querySelector('.q-ia'); if (b) b.parentNode.style.display = 'none';
      }).catch(function () {});
  }
  function dateFr(iso) { return iso ? String(iso).slice(8, 10) + '/' + String(iso).slice(5, 7) + '/' + String(iso).slice(0, 4) : ''; }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.q-ia');
    if (!b) return;
    var zone = b.parentNode.nextElementSibling, q = b.getAttribute('data-q'), d = cache[b.getAttribute('data-slug')] || {};
    zone.innerHTML = '<p class="q-vide">L’IA rédige sa réponse…</p>';
    var ctx = d.nom ? ('Ville : ' + d.nom + ' (' + (d.pays || '') + '), ' + (d.population || '') + ' habitants. ' + (d.resume || '')).slice(0, 4000) : '';
    fetch(IA_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ site: 'dix-mille-escales', question: q, contexte: ctx, slug: d.slug || '' }) })
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
    // Question à voix haute (téléphones et navigateurs qui le permettent)
    var Reco = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (Reco && input && !b.querySelector('.q-micro')) {
      var mic = document.createElement('button');
      mic.type = 'button'; mic.className = 'q-btn q-micro'; mic.title = 'Poser la question à voix haute'; mic.setAttribute('aria-label', 'Poser la question à voix haute'); mic.textContent = '🎤';
      input.insertAdjacentElement('afterend', mic);
      mic.addEventListener('click', function () {
        try {
          var r = new Reco(); r.lang = 'fr-FR'; r.interimResults = false; r.maxAlternatives = 1;
          mic.textContent = '…';
          r.onresult = function (e) { input.value = e.results[0][0].transcript; mic.textContent = '🎤'; demander(); };
          r.onerror = r.onend = function () { mic.textContent = '🎤'; };
          r.start();
        } catch (e) { mic.textContent = '🎤'; }
      });
    }
    var villePage = b.getAttribute('data-ville') || '';
    var exemples = villePage
      ? ['Faut-il un visa ?', 'Quel temps fait-il cette semaine ?', 'Quand partir ?', 'Combien coûte un repas ?', 'Que voir ?', 'Que faire en 2 jours ?', 'Où manger ?', 'Que faire aux alentours ?', 'Quelle heure est-il là-bas ?', 'Est-ce dangereux ?', 'Quelle langue parle-t-on ?', 'Quelle est son histoire ?', 'Qui est né ici ?']
      : ['Faut-il un visa pour Tokyo ?', 'Quel temps fait-il à New York ?', 'Quand partir à Marrakech ?', 'Combien coûte un repas à Lisbonne ?', 'Que voir à Rome ?', 'Que faire en 2 jours à Lisbonne ?', 'Quelle heure est-il à Sydney ?', 'Que faire autour de Barcelone ?', 'Quelle monnaie au Caire ?', 'Qui est né à Vienne ?', 'Quelle est l’histoire de Kyoto ?', 'Où dormir à Prague ?', 'Quel temps en avril à Bangkok ?'];
    sugg.innerHTML = exemples.map(function (e) { return '<button type="button">' + E(e) + '</button>'; }).join('');
    sugg.querySelectorAll('button').forEach(function (bt) { bt.addEventListener('click', function () { input.value = bt.textContent; demander(); }); });
    if (sugg.querySelectorAll('button').length > 5) {  // sur téléphone, 5 exemples d'abord, les autres sur demande
      var plus = document.createElement('button'); plus.type = 'button'; plus.className = 'q-plus'; plus.textContent = 'Plus d’exemples';
      plus.addEventListener('click', function () { sugg.classList.add('tout'); plus.remove(); });
      sugg.appendChild(plus);
    }
    var derniere = villePage;
    function demander() {
      var q = input.value.trim();
      if (q.length < 3) { rep.innerHTML = '<p class="q-vide">Posez une question, par exemple « Faut-il un visa pour le Japon ? ».</p>'; return; }
      rep.innerHTML = '<div aria-label="Je cherche…" role="status"><span class="sk l"></span><span class="sk c"></span><span class="sk b"></span></div>';
      chargerIndex(function (err) {
        if (err) { rep.innerHTML = '<p class="q-vide">La recherche est indisponible pour le moment. Réessayez dans un instant.</p>'; return; }
        chercherCelebre(q).catch(function () { return null; }).then(function (cel) {
        var vc = trouverVille(q);
        var ch = chiffreDemande(q);
        if (cel && !(vc && motsLieu(cel[0]).join(' ') === motsLieu(vc[0]).join(' '))) {
          var aLe = !ch || (cel[3] || {})[ch[0]] != null || (ch[0] === 'cr' && (cel[3] || {}).ou != null);
          rep.innerHTML = repCelebre(cel) + (aLe ? boutonIA(q, {}, 1) : pasLeChiffre(ch, cel[0]) + boutonIA(q, {})); if (!aLe) memoireIA(rep, q, {}); return;
        }
        var dv = COMPARE.test((' ' + norm(q) + ' ').replace(/^ ou /, ' ')) ? deuxVilles(q) : null;
        if (dv) {
          charger(dv[0][1], function (a) { charger(dv[1][1], function (b) {
            var h = a && b ? comparer(a, b, q) : '';
            rep.innerHTML = h ? '<div class="q-ville">' + E(a.nom) + ' · ' + E(b.nom) + '</div><div class="q-texte">' + h + boutonIA(q, {}, 1) + '</div>'
              : '<p class="q-vide">Je n’ai pas pu comparer ces deux villes pour le moment.</p>' + boutonIA(q, {});
          }); });
          return;
        }
        var ld = ch ? lieuDemande(q) : '';
        var v = trouverVille(q), slug = v ? v[1] : derniere;
        if ((ch && ld) || !slug) {
          // réponses vérifiées (lecteurs, ou réponses de l'IA relues et ajoutées au site) avant de renvoyer vers l'IA
          chargerReponses().catch(function () { return []; }).then(function (liste) {
            var rg = reponseLecteur(q, { slug: v ? v[1] : '' }, liste || []);
            if (rg) { rep.innerHTML = '<div class="q-texte"><p>' + E(rg.r).replace(/\n/g, '<br>') + '</p><p class="note">Réponse vérifiée le ' + E(rg.date || '') + (rg.source ? ' · source : ' + E(rg.source) : '') + '.</p>' + boutonIA(q, {}, 1) + '</div>'; return; }
            if (ch && ld) rep.innerHTML = pasLeChiffre(ch, ld) + boutonIA(q, {});
            else rep.innerHTML = '<p class="q-vide">De quelle ville parlez-vous ? Ajoutez son nom à la question, par exemple « Quel temps fait-il à Lisbonne ? ».</p>' + boutonIA(q, {});
            memoireIA(rep, q, {});
          });
          return;
        }
        derniere = slug;
        charger(slug, function (d) {
          if (!d) { rep.innerHTML = '<p class="q-vide">Impossible de charger la fiche de cette ville pour le moment.</p>'; return; }
          var tete = '<div class="q-ville">' + E(d.nom) + ' · ' + E(d.pays) + '</div><div class="q-texte">';
          chargerLieux(slug).then(function (L) {
            var f = lieuCite(q, L, d.nom);
            var pg = programme(q, d, L);
            if (pg) { rep.innerHTML = tete + pg + boutonIA(q, d, 1) + '</div>'; return; }
            if (f) { rep.innerHTML = tete + repLieu(f, d) + boutonIA(q, d, 1) + '</div>'; return; }
            var r_ = repondre(q, d);
            if (r_) { rep.innerHTML = tete + r_ + boutonIA(q, d, 1) + '</div>'; return; }
            chargerReponses().then(function (liste) {
            var rl = reponseLecteur(q, d, liste);
            if (rl) { rep.innerHTML = tete + '<p>' + E(rl.r).replace(/\n/g, '<br>') + '</p><p class="note">Réponse rédigée le ' + E(rl.date || '') + ' à la question d’un lecteur' + (rl.source ? ' · source : ' + E(rl.source) : '') + '.</p>' + boutonIA(q, d, 1) + '</div>'; return; }
            rep.innerHTML = tete + '<p class="q-vide">Je cherche dans tous les textes de ' + E(d.nom) + '…</p></div>';
            chercherTextes(q, d).then(function (h) { rep.innerHTML = tete + (h || portrait(d)) + boutonIA(q, d) + envoyer(q, d) + '</div>'; memoireIA(rep, q, d); }).catch(function () { rep.innerHTML = tete + portrait(d) + boutonIA(q, d) + envoyer(q, d) + '</div>'; });
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
