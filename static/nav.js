/* Dix Mille Escales – navigation pratique : barre du bas sur téléphone (recherche), retour en haut, partage d'une fiche. */
(function () {
  // Pied de page, barre du bas et bouton « haut de page » : construits ici une seule fois (les 69 000 pages restent légères)
  var R = document.body.getAttribute('data-root') || (/\/villes\/|\/pays\/[a-z]{2}\//.test(location.pathname) ? '../../' : /\/[a-z-]+\/$/.test(location.pathname) && !/\/dix-mille-escales\/$/.test(location.pathname) ? '../' : '');
  var pied = document.getElementById('pied');
  if (pied && !pied.querySelector('.foot-cols')) {
    var col = function (t, l) { return '<div><b>' + t + '</b>' + l.map(function (x) { return '<a href="' + R + x[0] + '">' + x[1] + '</a>'; }).join('') + '</div>'; };
    pied.querySelector('.in').insertAdjacentHTML('afterbegin', '<div class="foot-cols">'
      + col('Destinations', [['pays/', 'Tous les pays'], ['#carte', 'Carte du monde'], ['ou-partir/', 'Où partir ?']])
      + col('Préparer', [['premier-voyage/', 'Guide du premier voyage'], ['itineraire/', 'Planificateur d’itinéraire'], ['preparer/', 'Liste de préparation'], ['assurance/', 'Assurance et santé']])
      + col('Outils', [['comparer/', 'Comparer des villes'], ['trajets/', 'Comparer des trajets'], ['outils/#convertisseur', 'Convertisseur'], ['carnet/', 'Mon carnet']])
      + col('Le guide', [['sources/', 'Nos sources'], ['etat/', 'État des robots'], ['mentions-legales/', 'Mentions légales']]) + '</div>');
  }
  if (!document.querySelector('.barre-bas')) {
    var ic = { a: '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>', c: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/>',
      p: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>', k: '<path d="M6 3h12v18l-6-4-6 4z"/>' };
    var sv = function (x) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + ic[x] + '</svg>'; };
    document.body.insertAdjacentHTML('beforeend', '<nav class="barre-bas" aria-label="Navigation rapide"><a href="' + (R || './') + '">' + sv('a') + 'Accueil</a>'
      + '<button type="button" id="bb-chercher">' + sv('c') + 'Chercher</button><a href="' + R + 'outils/">' + sv('p') + 'Préparer</a><a href="' + R + 'carnet/">' + sv('k') + 'Carnet</a></nav>'
      + '<button type="button" class="haut-page" id="haut-page" aria-label="Revenir en haut de la page" hidden><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 14l6-6 6 6"/></svg></button>');
  }
  var top = document.querySelector('.top'), q = document.getElementById('q');
  var bb = document.getElementById('bb-chercher');
  if (bb && top && q) bb.addEventListener('click', function () {
    top.classList.add('cherche-ouverte'); window.scrollTo({ top: 0 }); setTimeout(function () { q.focus(); }, 50);
  });
  if (q && top) q.addEventListener('blur', function () { setTimeout(function () { if (document.activeElement !== q) top.classList.remove('cherche-ouverte'); }, 200); });
  // Page active dans la barre du bas
  document.querySelectorAll('.barre-bas a').forEach(function (a) {
    try { if (new URL(a.getAttribute('href'), location.href).pathname === location.pathname.replace(/index\.html$/, '')) a.setAttribute('aria-current', 'page'); } catch (e) {}
  });
  // Retour en haut
  var hp = document.getElementById('haut-page');
  if (hp) {
    var maj = function () { hp.hidden = window.scrollY < 1200; };
    window.addEventListener('scroll', maj, { passive: true }); maj();
    hp.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth' }); });
  }
  // Partager la fiche (téléphone : menu de partage ; ordinateur : lien copié)
  var actions = document.querySelector('.carnet-btns');
  if (actions) {
    var b = document.createElement('button'); b.type = 'button'; b.textContent = 'Partager';
    b.addEventListener('click', function () {
      var titre = document.title.split(' – ')[0];
      if (navigator.share) navigator.share({ title: titre, url: location.href.split('#')[0] }).catch(function () {});
      else if (navigator.clipboard) navigator.clipboard.writeText(location.href.split('#')[0]).then(function () { b.textContent = 'Lien copié'; setTimeout(function () { b.textContent = 'Partager'; }, 2000); });
    });
    actions.appendChild(b);
  }
  // « Donner mon avis » : formulaire GitHub prérempli, fabriqué au moment du clic (les pages restent légères)
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a.donner-avis'); if (!a) return;
    e.preventDefault();
    var m = location.hostname.match(/^([^.]+)\.github\.io$/), seg = location.pathname.split('/').filter(Boolean);
    var depot = m && seg.length ? m[1] + '/' + seg[0] : 'pablopacaut17-sudo/dix-mille-escales';
    var h = document.querySelector('h1.city'), ville = h ? h.textContent.replace(/Ville phare|Fiche complète/g, '').trim() : '';
    var slug = location.pathname.replace(/\/index\.html$/, '').replace(/\/$/, '').split('/').pop();
    var corps = 'Lieu : ' + a.dataset.n + '\nIdentifiant : ' + a.dataset.i + '\nVille : ' + slug + '\n\nNote (de 1 à 5) : \n\nVotre avis :\n\n\nDate de la visite (mois et année) : \n\n(Votre avis sera publié sur Dix Mille Escales après relecture. Restez courtois et factuel.)';
    window.open('https://github.com/' + depot + '/issues/new?title=' + encodeURIComponent('Avis – ' + a.dataset.n + ' – ' + ville) + '&body=' + encodeURIComponent(corps), '_blank', 'noopener');
  });
})();
