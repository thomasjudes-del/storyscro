(() => {
  'use strict';
  const D = window.STORYSCRO || { decisions:[], workshop:[], proof:[], images:{}, sources:{} };
  const clamp = (v,min=0,max=1) => Math.min(max,Math.max(min,v));
  const lerp = (a,b,t) => a + (b-a)*t;
  const smoothstep = t => { t = clamp(t); return t*t*(3-2*t); };
  const $ = (s,c=document) => c.querySelector(s);
  const $$ = (s,c=document) => [...c.querySelectorAll(s)];
  const vh = () => window.innerHeight || 800;

  const frenchFixes = [
    [/\bMetropole\b/g,'Métropole'],[/\bstrategie\b/gi,m=>m[0]==='S'?'Stratégie':'stratégie'],[/\badaptation\b/g,'adaptation'],
    [/\bvulnerabilites\b/gi,'vulnérabilités'],[/\bvulnerabilite\b/gi,'vulnérabilité'],[/\breellement\b/g,'réellement'],[/\baleas\b/g,'aléas'],
    [/\bdependances\b/g,'dépendances'],[/\bcapacites\b/g,'capacités'],[/\bcapacite\b/g,'capacité'],[/\breduire\b/g,'réduire'],[/\bcout\b/g,'coût'],
    [/\bdelai\b/g,'délai'],[/\bacceptabilite\b/g,'acceptabilité'],[/\bresponsabilites\b/g,'responsabilités'],[/\betude\b/g,'étude'],
    [/\bMethode\b/g,'Méthode'],[/\bmethode\b/g,'méthode'],[/\bdecisions\b/g,'décisions'],[/\bdecision\b/g,'décision'],[/\bSecuriser\b/g,'Sécuriser'],
    [/\bsecuriser\b/g,'sécuriser'],[/\bPrioriser\b/g,'Prioriser'],[/\bAccelerer\b/g,'Accélérer'],[/\baccelerer\b/g,'accélérer'],
    [/\bdonnees\b/g,'données'],[/\bpremiere\b/g,'première'],[/\bScenarios\b/g,'Scénarios'],[/\bscenarios\b/g,'scénarios'],[/\bpriorites\b/g,'priorités'],
    [/\bpriorite\b/g,'priorité'],[/\bsequencage\b/g,'séquençage'],[/\bvalide\b/g,'validé'],[/\bpartage\b/g,'partagé'],[/\bactes\b/g,'actés'],
    [/\badoptee\b/g,'adoptée'],[/\bElus\b/g,'Élus'],[/\bOperateurs\b/g,'Opérateurs'],[/\bsequences\b/g,'séquences'],[/\benchainent\b/g,'enchaînent'],
    [/\bstrategique\b/g,'stratégique'],[/\bcriticite\b/g,'criticité'],[/\bcible\b/g,'ciblé'],[/\bmecanismes\b/g,'mécanismes'],[/\bmaturite\b/g,'maturité'],
    [/\bneutralite\b/g,'neutralité'],[/\bmodeles\b/g,'modèles'],[/\beconomiques\b/g,'économiques'],[/\bEtude\b/g,'Étude'],[/\bdeveloppement\b/g,'développement'],
    [/\breglementaires\b/g,'réglementaires'],[/\bmarche\b/g,'marché'],[/\bcaracterisation\b/g,'caractérisation'],[/\bilots\b/g,'îlots'],[/\bchaine\b/g,'chaîne'],
    [/\bdeploiement\b/g,'déploiement'],[/\breferences\b/gi,'références'],[/\bcompetences\b/g,'compétences'],[/\bSpecificite\b/g,'Spécificité'],
    [/\bDemonstration\b/g,'Démonstration'],[/\bCoherence\b/g,'Cohérence'],[/\bresultat\b/g,'résultat'],[/\blimites\b/g,'limités'],[/\bmanoeuvre\b/g,'manœuvre'],
    [/\bCadrage valide\b/g,'Cadrage validé'],[/\bDiagnostic partage\b/g,'Diagnostic partagé'],[/\bArbitrages actes\b/g,'Arbitrages actés'],
    [/\bFeuille de route adoptee\b/g,'Feuille de route adoptée'],[/\bMettre en tension\b/g,'Mettre en tension'],[/\bCo-construction\b/g,'Co-construction'],
    [/\bmise en oeuvre\b/g,'mise en œuvre'],[/\bMise en oeuvre\b/g,'Mise en œuvre'],[/\bdu cadrage au passage a l'action\b/gi, m=>m[0]==='D'?"Du cadrage au passage à l'action":"du cadrage au passage à l'action"],
    [/\ba la decision\b/gi, m=>m[0]==='A'?"À la décision":"à la décision"],[/\bde la vulnerabilite a la decision\b/gi,'de la vulnérabilité à la décision'],
    [/\b6 a 10\b/g,'6 à 10'],[/\bSource P\./g,'Source p.']
  ];
  const fr = text => {
    let out = String(text ?? '');
    frenchFixes.forEach(([rx,repl]) => { out = out.replace(rx,repl); });
    return out;
  };
  function restoreFrenchTypography(root=document.body){
    if (!root) return;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    const nodes=[];
    while(walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      const parent=node.parentElement;
      if(!parent || ['SCRIPT','STYLE','NOSCRIPT'].includes(parent.tagName)) return;
      const fixed=fr(node.nodeValue);
      if(fixed!==node.nodeValue) node.nodeValue=fixed;
    });
  }
  function heldTrackPosition(p,count){
    if (p >= .9999) return count-1;
    const z=clamp(p)*(count-1);
    const i=Math.min(count-2,Math.floor(z));
    const f=z-i;
    const transition=smoothstep((f-.58)/.42);
    return i+transition;
  }

  const refinement=document.createElement('link');
  refinement.rel='stylesheet'; refinement.href='refine.css'; document.head.appendChild(refinement);

  const drawer = $('#sourceDrawer');
  const sourceTitle = $('#sourceTitle');
  const sourceBody = $('#sourceBody');
  const menu = $('#menuDrawer');
  const openDrawer = el => { el.classList.add('open'); el.setAttribute('aria-hidden','false'); };
  const closeDrawer = el => { el.classList.remove('open'); el.setAttribute('aria-hidden','true'); };

  function showSource(key){
    const source = D.sources[key];
    if (!source) {
      sourceTitle.textContent = 'Sources';
      sourceBody.innerHTML = `<div class="source-list">${Object.entries(D.sources).map(([id,s]) => `<button data-source="${id}"><strong>Page ${s.page}</strong><small>${fr(s.title)}</small></button>`).join('')}</div>`;
    } else {
      sourceTitle.textContent = fr(source.title);
      sourceBody.innerHTML = `<div class="source-card"><b>PDF | page ${source.page}</b><p>${fr(source.text)}</p></div><div class="source-card"><b>Traitement éditorial</b><p>Le contenu a été condensé, réordonné et mis en scène. Les informations factuelles proviennent du document source.</p></div>`;
    }
    restoreFrenchTypography(drawer);
    openDrawer(drawer);
  }
  document.addEventListener('click', e => {
    const src = e.target.closest('[data-source]');
    if (src) showSource(src.dataset.source);
  });
  $('#sourceClose')?.addEventListener('click',() => closeDrawer(drawer));
  $('#menuBtn')?.addEventListener('click',() => openDrawer(menu));
  $('#menuClose')?.addEventListener('click',() => closeDrawer(menu));
  $$('#menuDrawer a').forEach(a => a.addEventListener('click',() => closeDrawer(menu)));

  const progressBar = $('#progressBar');
  const heroImage = $('#heroImage');
  const decisionSection = $('[data-scene="decisions"]');
  const vulnerabilitySection = $('[data-scene="vulnerabilities"]');
  const matrixSection = $('[data-scene="matrix"]');
  const methodSection = $('[data-scene="method"]');
  const planningSection = $('[data-scene="planning"]');
  const workshopSection = $('[data-scene="workshops"]');
  const deliverablesSection = $('[data-scene="deliverables"]');
  const proofSection = $('[data-scene="proof"]');

  function sectionProgress(section){
    if (!section) return 0;
    const start = section.offsetTop;
    const span = Math.max(1, section.offsetHeight - vh());
    return clamp((window.scrollY - start) / span);
  }

  function updateDecision(p){
    const index = Math.min(2,Math.floor(clamp(p*.999)*3));
    const local = p*3-index;
    const copy = D.decisions[index] || D.decisions[0];
    const box = $('#decisionCopy');
    if (box && box.dataset.index !== String(index)) {
      box.dataset.index = String(index);
      box.animate([{opacity:.18,transform:'translateY(14px)'},{opacity:1,transform:'translateY(0)'}],{duration:380,easing:'ease-out'});
      $('.scene-kicker',box).textContent = fr(copy.kicker);
      $('h3',box).textContent = fr(copy.title);
      $$('p',box).find(x => !x.classList.contains('scene-kicker')).textContent = fr(copy.text);
    }
    const path = $('#decisionLine');
    if (path) path.style.strokeDashoffset = String(1600*(1-clamp(.15+p*.9)));
    $$('.decision-label').forEach((el,i) => el.classList.toggle('active',i===index));
    $$('.decision-path circle').forEach((el,i) => el.classList.toggle('active',i<=index));
    const photo = $('.decision-photo');
    if (photo) {
      const scale = 1.08 + p*.15;
      const x = lerp(48,63,p);
      photo.style.transform = `scale(${scale}) translate3d(${(p-.5)*1.5}%,0,0)`;
      photo.style.backgroundPosition = `${x}% center`;
      photo.style.filter = `saturate(${.72+local*.16}) contrast(1.03)`;
    }
  }

  function updateVulnerabilities(p){
    const mosaic = $('#mosaic');
    const intro = $('#mosaicIntro');
    if (!mosaic) return;
    const threshold = .16;
    if (p < threshold) {
      mosaic.classList.remove('focused');
      $$('.mosaic-tile',mosaic).forEach(t => t.classList.remove('active'));
      if (intro) intro.style.opacity = String(1-p/threshold);
      return;
    }
    const q = clamp((p-threshold)/(1-threshold));
    const index = Math.min(3,Math.floor(q*4*.999));
    mosaic.classList.add('focused');
    $$('.mosaic-tile',mosaic).forEach((t,i) => t.classList.toggle('active',i===index));
    if (intro) intro.style.opacity = '0';
    const tile = $$('.mosaic-tile',mosaic)[index];
    const img = tile ? $('.tile-image',tile) : null;
    if (img) {
      const local = q*4-index;
      img.style.transform = `scale(${1.04+local*.06}) translate3d(0,${(local-.5)*1.5}%,0)`;
    }
  }

  function updateMatrix(p){
    const m = $('#matrixVisual');
    if (!m) return;
    m.classList.toggle('axes',p>.08);
    m.classList.toggle('points',p>.44);
    m.classList.toggle('zoom',p>.72);
    const quads = $$('.mquad',m);
    quads.forEach((q,i) => q.classList.toggle('active',p > .18 + i*.09));
    const cap = $('#matrixCaption');
    if (cap) {
      const strong = $('strong',cap); const span = $('span',cap);
      if (p < .26) { strong.textContent="Urgence × capacité d'action"; span.textContent="Rendre les critères de choix visibles."; }
      else if (p < .52) { strong.textContent='Sécuriser. Prioriser.'; span.textContent="Les options ne demandent ni le même horizon, ni la même posture."; }
      else if (p < .78) { strong.textContent='Surveiller. Accélérer.'; span.textContent="Chaque action prend place dans une logique d'arbitrage explicite."; }
      else { strong.textContent='Tester les arbitrages.'; span.textContent="Entretiens et ateliers servent à confronter urgence, capacité d'action et dépendances."; }
    }
  }

  function updateMethod(p){
    const track = $('#methodTrack');
    if (!track) return;
    const pos=heldTrackPosition(p,4);
    const x = pos * window.innerWidth;
    track.style.transform = `translate3d(${-x}px,0,0)`;
    const heading=$('.method-heading');
    if(heading){
      const intro=clamp(1-p/.12);
      heading.style.opacity=String(intro);
      heading.style.transform=`translate3d(0,${(1-intro)*-18}px,0)`;
      heading.style.pointerEvents=intro>.2?'auto':'none';
    }
    const panels = $$('.method-panel',track);
    panels.forEach((panel,i) => {
      const local = clamp(1-Math.abs(pos-i));
      const bg = $('.panel-bg',panel);
      if (bg) bg.style.transform = `scale(${1.1-local*.04}) translate3d(${(i-pos)*1.2}%,0,0)`;
    });
  }

  const gantt = [
    {label:'Cadrage & collecte',start:0,end:2,cls:'bar-blue2'},
    {label:'Diagnostic & entretiens',start:1,end:6,cls:'bar-blue'},
    {label:'Benchmark & options',start:3,end:7,cls:'bar-green'},
    {label:'Scénarios & ateliers',start:6,end:9,cls:'bar-orange'},
    {label:'Feuille de route',start:8,end:11,cls:'bar-purple'},
    {label:'Finalisation & transfert',start:10,end:12,cls:'bar-dark'}
  ];
  function buildPlanning(){
    const weeks = $('#weekRow'); const lines = $('#ganttLines');
    if (!weeks || !lines || weeks.children.length) return;
    const lead = document.createElement('div'); lead.className='week'; lead.textContent='Séquence'; weeks.appendChild(lead);
    for(let i=1;i<=12;i++){ const w=document.createElement('div'); w.className='week'; w.textContent=`S${i}`; weeks.appendChild(w); }
    gantt.forEach((row,i) => {
      const r=document.createElement('div'); r.className='gantt-row'; r.dataset.row=String(i);
      const label=document.createElement('div'); label.className='gantt-label'; label.textContent=fr(row.label); r.appendChild(label);
      const bar=document.createElement('div'); bar.className=`gantt-bar ${row.cls}`; bar.dataset.start=String(row.start); bar.dataset.end=String(row.end); bar.style.marginLeft=`${(row.start/12)*100}%`; bar.style.width=`${((row.end-row.start)/12)*100}%`; r.appendChild(bar); lines.appendChild(r);
    });
    $$('.milestone').forEach(m => { const at=Number(m.dataset.at||0); m.style.left=`${at*100}%`; });
  }
  buildPlanning();
  function updatePlanning(p){
    $$('.gantt-bar').forEach(bar => {
      const start=Number(bar.dataset.start), end=Number(bar.dataset.end);
      const t=clamp((p*12-start)/(end-start));
      bar.style.transform=`scaleX(${t})`;
    });
    $$('.milestone').forEach(m => m.classList.toggle('active',p>=Number(m.dataset.at||0)));
  }

  function updateWorkshop(p){
    const index=Math.min(2,Math.floor(clamp(p*.999)*3));
    const w=D.workshop[index]||D.workshop[0];
    const word=$('#workshopWord');
    if (word && word.dataset.index!==String(index)) {
      word.dataset.index=String(index);
      $('b',word).textContent=w.n; $('span',word).textContent=fr(w.title); $('small',word).textContent=fr(w.text);
      word.animate([{opacity:.15,transform:'translateY(12px)'},{opacity:1,transform:'translateY(0)'}],{duration:360,easing:'ease-out'});
    }
    const orbit=$('#orbit'); if(!orbit) return;
    const pull=.05+.2*p;
    const cx=orbit.clientWidth/2, cy=orbit.clientHeight/2;
    $$('.actor',orbit).forEach((a,i) => {
      const ax=a.offsetLeft+a.offsetWidth/2, ay=a.offsetTop+a.offsetHeight/2;
      const tx=(cx-ax)*pull, ty=(cy-ay)*pull;
      const float=Math.sin((p*7+i)*1.1)*4;
      a.style.transform=`translate3d(${tx}px,${ty+float}px,0) scale(${1-p*.08})`;
    });
    const bg=$('.workshop-bg');
    if(bg) bg.style.transform=`scale(${1.08+p*.08}) translate3d(${p*2}%,0,0)`;
  }

  function updateDeliverables(p){
    const track=$('#deliverableTrack'); if(!track) return;
    const pos=heldTrackPosition(p,6);
    const x=pos*window.innerWidth;
    track.style.transform=`translate3d(${-x}px,0,0)`;
    const title=$('.deliverable-title');
    if(title){
      const intro=clamp(1-p/.1);
      title.style.opacity=String(intro);
      title.style.transform=`translate3d(0,${(1-intro)*-16}px,0)`;
      title.style.pointerEvents=intro>.2?'auto':'none';
    }
    $$('.delivery',track).forEach((d,i) => {
      const local=clamp(1-Math.abs(pos-i));
      d.style.opacity=String(.50+.50*local);
    });
  }

  function updateProof(p){
    const index=Math.min(3,Math.floor(clamp(p*.999)*4));
    const item=D.proof[index]||D.proof[0];
    const box=$('#proofCopy'); const bg=$('#proofBg');
    if (box && box.dataset.index!==String(index)) {
      box.dataset.index=String(index);
      $('.scene-kicker',box).textContent=fr(item.meta);
      $('h3',box).textContent=fr(item.title);
      $$('p',box).find(x=>!x.classList.contains('scene-kicker')).textContent=fr(item.text);
      box.animate([{opacity:.12,transform:'translateY(16px)'},{opacity:1,transform:'translateY(0)'}],{duration:400,easing:'ease-out'});
    }
    const image=D.images[item.image];
    if (bg && image && bg.dataset.image!==item.image) {
      bg.dataset.image=item.image;
      bg.style.backgroundImage=`linear-gradient(90deg,rgba(3,16,24,.84),rgba(3,16,24,.25),rgba(3,16,24,.64)),url('${image}')`;
    }
    if (bg) bg.style.transform=`scale(${1.08+p*.08}) translate3d(${(p-.5)*1.8}%,0,0)`;
  }

  let ticking=false;
  function update(){
    ticking=false;
    const doc=document.documentElement;
    const total=Math.max(1,doc.scrollHeight-vh());
    const global=clamp(window.scrollY/total);
    if(progressBar) progressBar.style.width=`${global*100}%`;
    if(heroImage && window.scrollY<vh()*1.1) heroImage.style.transform=`scale(${1.1+global*.25}) translate3d(0,${Math.min(window.scrollY*.12,75)}px,0)`;
    updateDecision(sectionProgress(decisionSection));
    updateVulnerabilities(sectionProgress(vulnerabilitySection));
    updateMatrix(sectionProgress(matrixSection));
    updateMethod(sectionProgress(methodSection));
    updatePlanning(sectionProgress(planningSection));
    updateWorkshop(sectionProgress(workshopSection));
    updateDeliverables(sectionProgress(deliverablesSection));
    updateProof(sectionProgress(proofSection));
  }
  function requestUpdate(){ if(!ticking){ ticking=true; requestAnimationFrame(update); } }
  window.addEventListener('scroll',requestUpdate,{passive:true});
  window.addEventListener('resize',requestUpdate,{passive:true});

  const dotMap = new Map($$('#chapterDots a').map(a=>[a.getAttribute('href').slice(1),a]));
  const chapterObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if(entry.isIntersecting){
        const id=entry.target.id;
        if(id && dotMap.has(id)) $$('#chapterDots a').forEach(a=>a.classList.toggle('active',a===dotMap.get(id)));
      }
    });
  },{threshold:.15,rootMargin:'-35% 0px -55% 0px'});
  $$('.chapter[id]').forEach(s=>chapterObserver.observe(s));

  restoreFrenchTypography(document.body);
  requestUpdate();
})();
