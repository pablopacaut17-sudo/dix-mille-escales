/* Dix Mille Escales – navigation pratique : barre du bas sur téléphone (recherche), retour en haut, partage d'une fiche. */
(function () {
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
