/* Dix Mille Escales – organisation des fiches de villes.
   Range les rubriques d'une fiche dans 5 onglets, ajoute un tableau de bord « En un coup d'œil »
   et une recherche qui fouille toute la fiche, y compris les milliers d'adresses non affichées.
   Fonctionne sur les trois sortes de fiches : complètes, légères (construites dans le navigateur) et rédigées à la main. */
(function () {
  var ONGLETS = [
    { id: 'essentiel', nom: 'L’essentiel', secs: ['apercu', 'facts', 'en-bref', 'avis', 'questions', 'essentiel', 'initie', 'profils', 'faq'] },
    { id: 'visiter', nom: 'À voir et à faire', secs: ['carte-lieux', 'voir', 'faire', 'activites', 'alentours', 'patrimoine', 'itineraires', 'quartiers', 'plages', 'lieux', 'sortir', 'proches'] },
    { id: 'adresses', nom: 'Manger et dormir', secs: ['manger', 'dormir', 'acheter', 'shopping', 'donnees-robots'] },
    { id: 'pratique', nom: 'Infos pratiques', secs: ['meteo', 'quand-partir', 'climat', 'agenda', 'budget', 'formalites', 'feries', 'arriver', 'bouger', 'pratique', 'securite', 'lexique'] },
    { id: 'culture', nom: 'Histoire et culture', secs: ['histoire', 'culture', 'inspirations', 'gastronomie', 'geographie', 'economie', 'sport', 'transports', 'personnalites', 'jumelages', 'savoir', 'porto', 'quiz'] }
  ];
  var RUBRIQUE_ONGLET = { voir: 'visiter', faire: 'visiter', alentours: 'visiter', manger: 'adresses', dormir: 'adresses', acheter: 'adresses' };
  var NOMS_RUB = { voir: 'À voir', faire: 'Activité', alentours: 'Aux alentours', manger: 'Manger et boire', dormir: 'Dormir', acheter: 'Acheter' };
  var fait = false;

  function E(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function norm(t) { return (t || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }
  function nb(n) { return new Intl.NumberFormat('fr-FR').format(n); }
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

  var css = '\
.og-barre{position:sticky;top:calc(env(safe-area-inset-top,0px) + var(--og-haut,58px));z-index:8;background:var(--bg);border-bottom:1px solid var(--line);margin:1.4rem 0 0;padding:.5rem 0 0}\
.og-ligne{display:flex;gap:.8rem;align-items:center;flex-wrap:wrap}\
.og-tabs{display:flex;gap:.25rem;overflow-x:auto;scrollbar-width:none;flex:1 1 auto;min-width:0}\
.og-tabs::-webkit-scrollbar{display:none}\
.og-tab{all:unset;cursor:pointer;font-family:var(--display,system-ui);font-weight:600;font-size:.98rem;padding:.65rem .95rem;border-radius:10px 10px 0 0;color:var(--muted);white-space:nowrap;border-bottom:3px solid transparent}\
.og-tab:hover{color:var(--ink)}\
.og-tab[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--buoy);background:var(--surface)}\
.og-tab:focus-visible{outline:3px solid var(--buoy)}\
.og-tab .og-n{font-weight:400;font-size:.8rem;color:var(--muted);margin-left:.3rem}\
.og-cherche{position:relative;flex:0 1 320px;min-width:200px;margin-bottom:.4rem}\
.og-cherche input{width:100%;font-family:var(--display,system-ui);font-size:.95rem;padding:.5rem .9rem;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--ink)}\
.og-res{position:absolute;right:0;top:calc(100% + 6px);width:min(560px,92vw);max-height:70vh;overflow:auto;background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:0 14px 34px rgba(18,49,59,.18);padding:.5rem;z-index:9}\
.og-res[hidden]{display:none}\
.og-res h4{font-family:var(--display,system-ui);font-size:.8rem;color:var(--muted);margin:.6rem .5rem .2rem;font-weight:600}\
.og-res button{all:unset;display:block;cursor:pointer;width:calc(100% - 1rem);padding:.45rem .5rem;border-radius:8px;font-size:.93rem;line-height:1.4}\
.og-res button:hover,.og-res button:focus-visible{background:var(--soft,#E2ECE9)}\
.og-res b{font-family:var(--display,system-ui)}\
.og-res small{display:block;color:var(--muted);font-size:.82rem}\
.og-res mark,.og-eclat mark{background:var(--buoy);color:#12313B;border-radius:3px;padding:0 .1em}\
.og-res .og-vide{padding:.6rem;color:var(--muted);font-style:italic}\
.og-panel[hidden]{display:none}\
.og-panel{padding-top:1.4rem}\
.og-sous{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 1.6rem}\
.og-sous a{font-family:var(--display,system-ui);font-size:.86rem;padding:.3rem .8rem;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);text-decoration:none}\
.og-sous a:hover{border-color:var(--buoy)}\
.og-panel > section,.og-panel > .og-groupe > section{margin-top:0 !important;margin-bottom:3rem}\
.og-eclat{animation:og-flash 2.2s ease-out}\
@keyframes og-flash{0%{background:rgba(242,183,5,.35)}100%{background:transparent}}\
@media (prefers-reduced-motion:reduce){.og-eclat{animation:none;outline:3px solid var(--buoy)}}\
.og-apercu{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.6rem;margin:0 0 2rem}\
.og-carte{display:block;text-decoration:none;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:.85rem 1rem;border-top:4px solid var(--c,var(--sea))}\
.og-carte:hover{border-color:var(--ink)}\
.og-carte span{display:block;font-family:var(--display,system-ui);font-size:.8rem;color:var(--muted)}\
.og-carte b{display:block;font-family:var(--display,system-ui);font-size:1.12rem;line-height:1.25;margin-top:.15rem}\
.og-carte small{display:block;font-family:var(--display,system-ui);font-size:.82rem;color:var(--muted);margin-top:.25rem;line-height:1.35}\
.og-suivant{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;border-top:1px solid var(--line);padding-top:1rem;margin-top:1rem}\
.og-suivant button{all:unset;cursor:pointer;font-family:var(--display,system-ui);font-weight:600;color:var(--sea)}\
.og-suivant button:focus-visible{outline:3px solid var(--buoy)}\
@media (max-width:700px){.og-cherche{flex:1 1 100%;order:-1}.og-tab{padding:.55rem .7rem;font-size:.92rem}}';

  function principal() { return document.querySelector('main') || document.body; }

  function collecter(main) {
    var tout = Array.prototype.slice.call(main.querySelectorAll('section[id], section.facts, div.facts'));
    return tout.filter(function (s) {
      var p = s.parentElement && s.parentElement.closest('section');
      return !p || !main.contains(p) || p === main;
    }).filter(function (s) { return !s.classList.contains('hero'); });
  }

  function ongletDe(sec) {
    var id = sec.id || (sec.classList.contains('facts') ? 'facts' : '');
    for (var i = 0; i < ONGLETS.length; i++) if (ONGLETS[i].secs.indexOf(id) > -1) return ONGLETS[i].id;
    return 'essentiel';
  }

  function titre(sec) { var h = sec.querySelector('h2'); return h ? h.textContent.replace(/\s+/g, ' ').trim() : (sec.classList.contains('facts') ? 'Fiche d’identité' : ''); }

  function apercu(d, root) {
    if (!d) return null;
    var cartes = [];
    function c(titre, valeur, detail, ancre, coul) { cartes.push('<a class="og-carte" href="#' + ancre + '" style="--c:' + (coul || 'var(--sea)') + '"><span>' + E(titre) + '</span><b>' + valeur + '</b>' + (detail ? '<small>' + detail + '</small>' : '') + '</a>'); }
    if (d.meteo && d.meteo[0]) c('Météo aujourd’hui', Math.round(d.meteo[0].min) + ' à ' + Math.round(d.meteo[0].max) + ' °C', E(d.meteo[0].ciel), 'meteo', '#2E6DB4');
    else if (d.climat) { var m = d.climat[new Date().getMonth()]; c('Climat ce mois-ci', Math.round(m.tmin) + ' à ' + Math.round(m.tmax) + ' °C', m.jours_pluie + ' jours de pluie', 'quand-partir', '#2E6DB4'); }
    if (d.meilleurs_mois && d.meilleurs_mois.length) c('Meilleure période', E(d.meilleurs_mois.slice(0, 3).join(', ')) + (d.meilleurs_mois.length > 3 ? '…' : ''), '', 'quand-partir', '#2F7D6D');
    if (d.formalites && d.formalites['Passeport français']) c('Visa (passeport français)', E(d.formalites['Passeport français'].replace(/, séjour jusqu’à/, ' ·').replace('Libre circulation : carte d’identité ou passeport', 'Carte d’identité suffit')), 'Belgique, Suisse, Canada : voir le détail', 'formalites', '#7B5EA7');
    if (d.cout) c('Budget par jour', '≈ ' + d.cout.prix['budget par jour (moyen)'] + ' €', 'repas simple ≈ ' + d.cout.prix['repas simple'] + ' €', 'budget', '#C9761E');
    if (d.securite) c('Sécurité', d.securite.niveau + ' sur 4', E(d.securite.libelle), 'formalites', d.securite.niveau >= 3 ? '#B5485D' : d.securite.niveau === 2 ? '#C99A00' : '#2F7D6D');
    var nl = ['voir', 'manger', 'dormir', 'faire', 'acheter'].reduce(function (s, k) { return s + (d['nb_' + k] || 0); }, 0);
    if (nl) c('Adresses recensées', nb(nl), (d.nb_manger ? nb(d.nb_manger) + ' pour manger · ' : '') + (d.nb_voir ? nb(d.nb_voir) + ' à voir' : ''), d.nb_manger ? 'manger' : 'voir', '#B5485D');
    if (d.monnaie) c('Monnaie', E(d.monnaie.charAt(0).toUpperCase() + d.monnaie.slice(1)), d.taux ? '1 € ≈ ' + String(Math.round(d.taux * 100) / 100).replace('.', ',') + ' ' + E(d.devise) : '', 'facts', '#56707A');
    if (d.langues && d.langues.length) c('Langue', E(d.langues[0].charAt(0).toUpperCase() + d.langues[0].slice(1)), d.langues.length > 1 ? E(d.langues.slice(1).join(', ')) : '', 'facts', '#56707A');
    if (!cartes.length) return null;
    var s = document.createElement('section'); s.id = 'apercu'; s.className = 'og-apercu-sec';
    s.innerHTML = '<h2>En un coup d’œil</h2><div class="og-apercu">' + cartes.join('') + '</div>';
    return s;
  }

  function construire(d) {
    if (fait) return; fait = true;
    var main = principal(), root = document.body.getAttribute('data-root') || '../../';
    var secs = collecter(main);
    if (secs.length < 3) return;
    var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    var haut = document.querySelector('.top'); if (haut) document.documentElement.style.setProperty('--og-haut', haut.offsetHeight + 'px');
    // Ancien sommaire, chapitres et colonne de sommaire des fiches rédigées : remplacés par les onglets
    document.querySelectorAll('.sommaire, main > .chapter, .chapter').forEach(function (x) { x.remove(); });
    var toc = document.querySelector('.toc'); if (toc) { toc.style.display = 'none'; var b = toc.parentElement; if (b) { b.style.display = 'block'; } }
    var premier = secs[0], parent = premier.parentElement;
    var barre = document.createElement('div'); barre.className = 'og-barre';
    barre.innerHTML = '<div class="og-ligne"><div class="og-tabs" role="tablist" aria-label="Rubriques de la fiche"></div>'
      + '<div class="og-cherche" role="search"><label for="og-q" style="position:absolute;left:-9999px">Chercher dans cette fiche</label>'
      + '<input id="og-q" type="search" autocomplete="off" placeholder="Chercher dans cette fiche…"><div class="og-res" id="og-res" hidden></div></div></div>';
    var boite = document.createElement('div'); boite.className = 'og-panels';
    parent.insertBefore(barre, premier); parent.insertBefore(boite, premier);
    var panels = {}, tabs = barre.querySelector('.og-tabs');
    ONGLETS.forEach(function (o) {
      var p = document.createElement('div'); p.className = 'og-panel'; p.id = 'onglet-' + o.id; p.setAttribute('role', 'tabpanel'); p.hidden = true;
      p.innerHTML = '<nav class="og-sous" aria-label="Dans cet onglet"></nav>';
      panels[o.id] = p; boite.appendChild(p);
    });
    var ap = apercu(d, root);
    if (ap) panels.essentiel.appendChild(ap);
    secs.forEach(function (s) { panels[ongletDe(s)].appendChild(s); if (s.classList.contains('facts') && !s.id) s.id = 'facts'; });
    // Onglets vides retirés, compteur de rubriques, sous-sommaire
    var actifs = ONGLETS.filter(function (o) { return panels[o.id].querySelectorAll(':scope > section').length; });
    actifs.forEach(function (o, i) {
      var p = panels[o.id], liste = p.querySelectorAll(':scope > section');
      var t = document.createElement('button'); t.className = 'og-tab'; t.type = 'button'; t.setAttribute('role', 'tab'); t.id = 'tab-' + o.id;
      t.setAttribute('aria-controls', p.id); t.setAttribute('aria-selected', 'false'); t.tabIndex = -1;
      t.innerHTML = E(o.nom) + '<span class="og-n">' + liste.length + '</span>';
      t.addEventListener('click', function () { ouvrir(o.id, true); });
      tabs.appendChild(t); p.setAttribute('aria-labelledby', t.id);
      p.querySelector('.og-sous').innerHTML = Array.prototype.map.call(liste, function (s) { var tt = titre(s); return tt && s.id ? '<a href="#' + s.id + '">' + E(tt) + '</a>' : ''; }).join('');
      if (liste.length < 2) p.querySelector('.og-sous').remove();
      var suiv = document.createElement('div'); suiv.className = 'og-suivant';
      suiv.innerHTML = (i > 0 ? '<button type="button" data-o="' + actifs[i - 1].id + '">' + E(actifs[i - 1].nom) + '</button>' : '<span></span>')
        + (i < actifs.length - 1 ? '<button type="button" data-o="' + actifs[i + 1].id + '">' + E(actifs[i + 1].nom) + '</button>' : '');
      suiv.querySelectorAll('button').forEach(function (b) { b.addEventListener('click', function () { ouvrir(b.getAttribute('data-o'), true); barre.scrollIntoView(); }); });
      p.appendChild(suiv);
    });
    ONGLETS.forEach(function (o) { if (actifs.indexOf(o) < 0) panels[o.id].remove(); });
    tabs.addEventListener('keydown', function (e) {
      var l = Array.prototype.slice.call(tabs.querySelectorAll('.og-tab')), i = l.indexOf(document.activeElement);
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { var j = (i + (e.key === 'ArrowRight' ? 1 : -1) + l.length) % l.length; l[j].focus(); l[j].click(); e.preventDefault(); }
    });

    function ongletContenant(el) { var p = el && el.closest('.og-panel'); return p ? p.id.replace('onglet-', '') : null; }
    function ouvrir(id, maj) {
      actifs.forEach(function (o) {
        var on = o.id === id; panels[o.id].hidden = !on;
        var t = document.getElementById('tab-' + o.id); t.setAttribute('aria-selected', on ? 'true' : 'false'); t.tabIndex = on ? 0 : -1;
        if (on) t.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      });
      if (maj && history.replaceState) history.replaceState(null, '', '#onglet-' + id);
      if (maj) { // en changeant d'onglet plus bas dans la page, on remonte au début de l'onglet
        var y = boite.getBoundingClientRect().top + window.scrollY - barre.offsetHeight - (haut ? haut.offsetHeight : 0) - 8;
        if (window.scrollY > y) window.scrollTo(0, y);
      }
    }
    function aller(cible, eclat) {
      var o = ongletDe2(cible); if (o) ouvrir(o, false);
      if (cible.tagName === 'DETAILS') cible.open = true;
      var det = cible.closest('details'); if (det) det.open = true;
      setTimeout(function () {
        var y = cible.getBoundingClientRect().top + window.scrollY - barre.offsetHeight - (haut ? haut.offsetHeight : 0) - 12;
        window.scrollTo({ top: y, behavior: matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth' });
        if (eclat) { cible.classList.remove('og-eclat'); void cible.offsetWidth; cible.classList.add('og-eclat'); }
      }, 30);
    }
    function ongletDe2(el) { return ongletContenant(el); }
    function depuisAncre(h, eclat) {
      if (!h) return false;
      var id = decodeURIComponent(h.replace(/^#/, ''));
      if (id.indexOf('onglet-') === 0 && panels[id.slice(7)]) { ouvrir(id.slice(7), false); return true; }
      var el = document.getElementById(id);
      if (el && boite.contains(el)) { aller(el, eclat); return true; }
      return false;
    }
    document.addEventListener('click', function (e) {
      var a = e.target.closest('a[href^="#"]'); if (!a) return;
      var h = a.getAttribute('href'); if (h.length < 2) return;
      if (depuisAncre(h, true)) { e.preventDefault(); if (history.replaceState) history.replaceState(null, '', h); }
    });
    window.addEventListener('hashchange', function () { depuisAncre(location.hash, true); });
    if (!depuisAncre(location.hash, false)) ouvrir(actifs[0].id, false);

    // Recherche dans la fiche
    var q = barre.querySelector('#og-q'), res = barre.querySelector('#og-res'), minuterie = null, lieux = null, lieuxCharges = false;
    var slug = location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '').split('/').pop();
    function chargerLieux() {
      if (lieuxCharges) return Promise.resolve(lieux); lieuxCharges = true;
      return lireJson(root + 'villes/' + slug + '/lieux.json.gz').then(function (x) { lieux = x.lieux || []; return lieux; }).catch(function () { lieux = []; return lieux; });
    }
    function surligner(txt, t) {
      var n = norm(txt), i = n.indexOf(t); if (i < 0) return E(txt.slice(0, 140));
      var deb = Math.max(0, i - 50), fin = Math.min(txt.length, i + t.length + 90);
      return (deb ? '…' : '') + E(txt.slice(deb, i)) + '<mark>' + E(txt.slice(i, i + t.length)) + '</mark>' + E(txt.slice(i + t.length, fin)) + (fin < txt.length ? '…' : '');
    }
    function chercher() {
      var t = norm(q.value.trim());
      if (t.length < 2) { res.hidden = true; return; }
      var trouves = [], vus = new Set();
      boite.querySelectorAll('h2, h3, h4, p, li, td, dd, dt, summary, b').forEach(function (el) {
        if (trouves.length >= 40 || el.closest('.og-sous, .og-suivant, .q-sugg, .og-apercu')) return;
        if (el.querySelector('p, li, h3, td')) return;
        var txt = el.textContent.replace(/\s+/g, ' ').trim();
        if (txt.length < 2 || norm(txt).indexOf(t) < 0) return;
        var cle = txt.slice(0, 80); if (vus.has(cle)) return; vus.add(cle);
        var sec = el.closest('.og-panel > section'), tab = ongletContenant(el);
        trouves.push({ el: el, txt: txt, rub: sec ? titre(sec) : '', tab: tab });
      });
      var html = '';
      ONGLETS.forEach(function (o) {
        var l = trouves.filter(function (x) { return x.tab === o.id; }); if (!l.length) return;
        html += '<h4>' + E(o.nom) + '</h4>' + l.slice(0, 12).map(function (x) { return '<button type="button" data-i="' + trouves.indexOf(x) + '">' + surligner(x.txt, t) + '<small>' + E(x.rub) + '</small></button>'; }).join('');
      });
      res.innerHTML = html + '<div id="og-lieux"></div>' || '';
      res.hidden = false;
      res.querySelectorAll('button[data-i]').forEach(function (b) { b.addEventListener('click', function () { var x = trouves[+b.getAttribute('data-i')]; res.hidden = true; aller(x.el, true); }); });
      chargerLieux().then(function (L) {
        if (norm(q.value.trim()) !== t) return;
        var l = (L || []).filter(function (f) { return norm(f.nom + ' ' + (f.adresse || '') + ' ' + (f.cuisine || '') + ' ' + f.type).indexOf(t) > -1; }).slice(0, 15);
        var z = res.querySelector('#og-lieux'); if (!z) return;
        if (l.length) z.innerHTML = '<h4>Adresses (' + l.length + (l.length === 15 ? ' et plus' : '') + ')</h4>' + l.map(function (f, i) {
          return '<button type="button" data-l="' + i + '"><b>' + surligner(f.nom, t) + '</b><small>' + E((NOMS_RUB[f.rubrique] || f.type) + ' · ' + f.type + (f.adresse ? ' · ' + f.adresse : '') + (f.distance_km && f.rubrique === 'alentours' ? ' · ' + String(f.distance_km).replace('.', ',') + ' km' : '')) + '</small></button>';
        }).join('');
        else if (!trouves.length) z.innerHTML = '<p class="og-vide">Rien ne correspond à « ' + E(q.value.trim()) + ' » dans cette fiche.</p>';
        z.querySelectorAll('button[data-l]').forEach(function (b) {
          b.addEventListener('click', function () {
            var f = l[+b.getAttribute('data-l')], sec = document.getElementById(f.rubrique) || document.getElementById('donnees-robots');
            res.hidden = true;
            if (!sec) return;
            aller(sec, false);
            var btn = sec.querySelector('.tout-voir[data-rub]');
            var appliquer = function () { var inp = sec.querySelector('.recherche-lieux, #dr-q'); if (inp) { inp.value = f.nom; inp.dispatchEvent(new Event('input')); } };
            if (btn) { btn.click(); setTimeout(appliquer, 700); } else appliquer();
          });
        });
      });
    }
    q.addEventListener('input', function () { clearTimeout(minuterie); minuterie = setTimeout(chercher, 180); });
    q.addEventListener('focus', function () { if (q.value.trim().length >= 2) res.hidden = false; chargerLieux(); });
    document.addEventListener('click', function (e) { if (!e.target.closest('.og-cherche')) res.hidden = true; });
    q.addEventListener('keydown', function (e) { if (e.key === 'Escape') { res.hidden = true; q.blur(); } if (e.key === 'Enter') { var b = res.querySelector('button'); if (b) b.click(); } });
  }

  function demarrer() {
    if (!/\/villes\//.test(location.pathname)) return; // seulement sur les fiches de villes
    var dyn = document.getElementById('fiche-dyn');
    if (dyn && !dyn.dataset.pret) return; // fiche légère : fiche.js appellera DME_onglets une fois construite
    var root = document.body.getAttribute('data-root') || '../../';
    var slug = location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '').split('/').pop();
    lireJson(root + 'villes/' + slug + '/donnees.json.gz').then(construire).catch(function () { construire(null); });
  }
  window.DME_onglets = demarrer;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer); else demarrer();
})();
