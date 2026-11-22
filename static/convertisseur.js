/* Dix Mille Escales – convertisseur de monnaie (taux de référence de la Banque centrale européenne). */
(function () {
  var D = window.DME, f = document.getElementById('conv');
  if (!f) return;
  var NOMS = { USD: 'dollar américain', JPY: 'yen japonais', GBP: 'livre sterling', CHF: 'franc suisse', CAD: 'dollar canadien', AUD: 'dollar australien',
    CNY: 'yuan chinois', INR: 'roupie indienne', BRL: 'réal brésilien', MXN: 'peso mexicain', TRY: 'livre turque', THB: 'baht thaïlandais', ZAR: 'rand sud-africain',
    SEK: 'couronne suédoise', NOK: 'couronne norvégienne', DKK: 'couronne danoise', PLN: 'zloty polonais', CZK: 'couronne tchèque', HUF: 'forint hongrois',
    RON: 'leu roumain', KRW: 'won sud-coréen', SGD: 'dollar de Singapour', HKD: 'dollar de Hong Kong', NZD: 'dollar néo-zélandais', IDR: 'roupie indonésienne',
    MYR: 'ringgit malaisien', PHP: 'peso philippin', ILS: 'shekel israélien', ISK: 'couronne islandaise', BGN: 'lev bulgare' };
  D.chargerMonde().then(function (M) {
    var t = Object.assign({ EUR: 1 }, M.change), codes = Object.keys(t).sort();
    var opt = codes.map(function (c) { return '<option value="' + c + '">' + c + (NOMS[c] ? ' – ' + NOMS[c] : c === 'EUR' ? ' – euro' : '') + '</option>'; }).join('');
    f.querySelector('#conv-de').innerHTML = opt; f.querySelector('#conv-vers').innerHTML = opt;
    f.querySelector('#conv-de').value = 'EUR'; f.querySelector('#conv-vers').value = t.INR ? 'INR' : 'USD';
    function calc() {
      var x = parseFloat(String(f.querySelector('#conv-montant').value).replace(',', '.')) || 0, de = f.querySelector('#conv-de').value, vers = f.querySelector('#conv-vers').value;
      var r = x / t[de] * t[vers];
      f.querySelector('#conv-res').textContent = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(x) + ' ' + de + ' = ' + new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(r) + ' ' + vers;
    }
    f.addEventListener('input', calc); f.querySelector('#conv-inverser').onclick = function () { var a = f.querySelector('#conv-de').value; f.querySelector('#conv-de').value = f.querySelector('#conv-vers').value; f.querySelector('#conv-vers').value = a; calc(); };
    f.querySelector('#conv-date').textContent = M.change_date ? 'Taux de référence de la BCE du ' + M.change_date.split('-').reverse().join('/') + '.' : '';
    calc();
  });
})();
