/* Dix Mille Escales – script commun : thème, recherche, heure locale, filtres */
(function(){
  var root=document.documentElement, base=document.body.getAttribute('data-root')||'';
  /* Thème */
  var TH=['auto','clair','sombre'],th='auto',btn=document.getElementById('theme-btn');
  try{th=localStorage.getItem('dme-theme')||'auto';}catch(e){}
  function apply(){if(th==='clair')root.setAttribute('data-theme','light');else if(th==='sombre')root.setAttribute('data-theme','dark');else root.removeAttribute('data-theme');if(btn)btn.textContent='Thème : '+th;}
  if(btn)btn.addEventListener('click',function(){th=TH[(TH.indexOf(th)+1)%3];try{localStorage.setItem('dme-theme',th);}catch(e){}apply();});
  apply();

  function initVivant(scope){
  /* Heure locale et décalage */
  scope.querySelectorAll('[data-tz]').forEach(function(el){
    var tz=el.getAttribute('data-tz');
    function tick(){try{el.textContent=new Intl.DateTimeFormat('fr-FR',{timeZone:tz,hour:'2-digit',minute:'2-digit'}).format(new Date());}catch(e){el.textContent='–';}}
    tick();setInterval(tick,30000);
  });
  scope.querySelectorAll('[data-offset]').forEach(function(el){
    try{var now=new Date();function f(z){var o={};new Intl.DateTimeFormat('en-US',{timeZone:z,hour12:false,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}).formatToParts(now).forEach(function(x){o[x.type]=x.value;});return Date.UTC(+o.year,+o.month-1,+o.day,+o.hour%24,+o.minute);}
      var d=(f(el.getAttribute('data-offset'))-f('Europe/Paris'))/3600000;
      if(d===0)el.textContent='Même heure qu’à Paris';else{var h=Math.abs(d);el.textContent='Paris '+(d>0?'+ ':'− ')+Math.floor(h)+' h'+(h%1?' '+Math.round(h%1*60):'');}}catch(e){el.textContent='–';}
  });
  scope.querySelectorAll('[data-season]').forEach(function(el){
    var lat=+el.getAttribute('data-season'),m=new Date().getMonth();
    if(Math.abs(lat)<23.5){el.textContent='Tropical : saisons sèche et humide';return;}
    var s=['hiver','hiver','printemps','printemps','printemps','été','été','été','automne','automne','automne','hiver'][m];
    if(lat<0)s={hiver:'été',printemps:'automne','été':'hiver',automne:'printemps'}[s];
    el.textContent=s.charAt(0).toUpperCase()+s.slice(1);
  });

  /* Lever et coucher du soleil (calcul astronomique, à quelques minutes près) */
  scope.querySelectorAll('[data-sun]').forEach(function(el){
    var p=el.getAttribute('data-sun').split(','),LAT=+p[0],LON=+p[1],R=Math.PI/180,tz=el.getAttribute('data-suntz');
    var jd=Date.now()/864e5+2440587.5,n=Math.round(jd-2451545-0.0009+LON/360),Js=n+0.0009-LON/360;
    var M=(357.5291+0.98560028*Js)%360,C=1.9148*Math.sin(M*R)+0.02*Math.sin(2*M*R)+0.0003*Math.sin(3*M*R);
    var L=(M+C+282.9372)%360,Jt=2451545+Js+0.0053*Math.sin(M*R)-0.0069*Math.sin(2*L*R);
    var sd=Math.sin(L*R)*Math.sin(23.4397*R),cd=Math.cos(Math.asin(sd));
    var cw=(Math.sin(-0.833*R)-Math.sin(LAT*R)*sd)/(Math.cos(LAT*R)*cd);
    if(cw<-1){el.textContent='Soleil de minuit';return;} if(cw>1){el.textContent='Nuit polaire';return;}
    var w=Math.acos(cw)/R,f=function(j){try{return new Intl.DateTimeFormat('fr-FR',{timeZone:tz,hour:'2-digit',minute:'2-digit'}).format(new Date((j-2440587.5)*864e5));}catch(e){return '–';}};
    el.textContent='↑ '+f(Jt-w/360)+'  ↓ '+f(Jt+w/360);
  });

  /* Filtres des listes de lieux */
  scope.querySelectorAll('[data-filter-for]').forEach(function(box){
    var list=document.getElementById(box.getAttribute('data-filter-for'));if(!list)return;
    var types={};list.querySelectorAll('li[data-type]').forEach(function(li){var t=li.getAttribute('data-type');types[t]=(types[t]||0)+1;});
    var keys=Object.keys(types).sort(function(a,b){return types[b]-types[a];});if(keys.length<2)return;
    function mk(label,t){var b=document.createElement('button');b.type='button';b.className='chip';b.textContent=label;b.setAttribute('aria-pressed',t===''?'true':'false');
      b.addEventListener('click',function(){box.querySelectorAll('.chip').forEach(function(x){x.setAttribute('aria-pressed','false');});b.setAttribute('aria-pressed','true');
        list.querySelectorAll('li[data-type]').forEach(function(li){li.hidden=!!t&&li.getAttribute('data-type')!==t;});});box.appendChild(b);}
    mk('Tout',''); keys.slice(0,10).forEach(function(k){mk(k+' ('+types[k]+')',k);});
  });

  }
  window.DME_initVivant=initVivant;
  initVivant(document);

  /* Compteur de données du guide */
  document.querySelectorAll('[data-compteur]').forEach(function(el){fetch(base+'static/compteur.json').then(function(r){return r.json();}).then(function(c){el.textContent=new Intl.NumberFormat('fr-FR').format(c.informations);}).catch(function(){el.textContent='–';});});

  /* Recherche parmi toutes les villes (index chargé à la première frappe) */
  var q=document.getElementById('q'),res=document.getElementById('results');if(!q)return;
  var idx=null,hits=[],act=-1;
  function norm(t){return (t||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[’'\-|]/g,' ');}
  function load(cb){if(idx)return cb();fetch(base+'static/index.json').then(function(r){return r.json();}).then(function(d){idx=d.map(function(r){return {n:r[0],s:r[1],p:r[2],pop:r[3],k:norm(r[0]+' '+r[4])};});cb();}).catch(function(){res.innerHTML='<li><a>Recherche indisponible pour le moment.</a></li>';});}
  function run(){var t=norm(q.value).trim();act=-1;if(t.length<2){res.innerHTML='';return;}
    load(function(){hits=[];for(var i=0;i<idx.length&&hits.length<30;i++){var k=idx[i].k;if(k.indexOf(t)===0||k.indexOf(' '+t)>-1)hits.push(idx[i]);}
      hits.sort(function(a,b){return (norm(a.n).indexOf(t)===0?0:1)-(norm(b.n).indexOf(t)===0?0:1)||b.pop-a.pop;});hits=hits.slice(0,8);
      res.innerHTML=hits.length?hits.map(function(h,i){return '<li><a id="o'+i+'" href="'+base+'villes/'+h.s+'/">'+h.n+'<span>'+h.p+'</span></a></li>';}).join(''):'<li><a>Aucune ville ne correspond.</a></li>';});}
  q.addEventListener('input',run);
  q.addEventListener('keydown',function(e){var a=res.querySelectorAll('a[href]');if(e.key==='ArrowDown'||e.key==='ArrowUp'){act=Math.max(0,Math.min(a.length-1,act+(e.key==='ArrowDown'?1:-1)));a.forEach(function(x,i){x.setAttribute('aria-selected',i===act?'true':'false');});e.preventDefault();}
    else if(e.key==='Enter'){e.preventDefault();var x=a[act>-1?act:0];if(x)location.href=x.getAttribute('href');}else if(e.key==='Escape')res.innerHTML='';});
  q.addEventListener('blur',function(){setTimeout(function(){res.innerHTML='';},200);});
})();
