(() => {
  'use strict';

  const $ = (s,c=document) => c.querySelector(s);
  const $$ = (s,c=document) => [...c.querySelectorAll(s)];
  const clamp = (v,min=0,max=1) => Math.min(max,Math.max(min,v));
  const smooth = t => { t=clamp(t); return t*t*(3-2*t); };
  const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const root = $('#storyRoot');
  const loading = $('#loading');
  const drawer = $('#sourceDrawer');
  const sourceTitle = $('#sourceTitle');
  const sourceBody = $('#sourceBody');
  const progress = $('#readingProgress');
  const chapterNav = $('#chapterNav');
  const microTrack = $('#microTrack');
  let STORY, GRAMMAR, assets, evidence, anchors=[];

  const motionReduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  Promise.all([
    fetch('story.json').then(r => { if(!r.ok) throw new Error(`story.json ${r.status}`); return r.json(); }),
    fetch('../engine/narrative-grammar.json').then(r => { if(!r.ok) throw new Error(`narrative-grammar.json ${r.status}`); return r.json(); })
  ]).then(([story,grammar]) => {
    STORY = story; GRAMMAR = grammar;
    validateStory(STORY);
    assets = new Map((STORY.assets||[]).map(x => [x.id,x]));
    evidence = new Map((STORY.evidence||[]).map(x => [x.id,x]));
    document.title = `${STORY.document.title} | StoryScro`;
    applyDesignSystem();
    renderStory();
    installGlobalInteractions();
    loading.remove();
  }).catch(err => {
    loading.remove();
    root.innerHTML = `<section class="error"><h1>Story Model invalide</h1><pre>${esc(err.stack||err.message)}</pre></section>`;
    console.error(err);
  });

  function validateStory(story){
    if(!story || !Array.isArray(story.chapters) || !story.chapters.length) throw new Error('No chapters in Story Model');
    const ids = new Set();
    for(const chapter of story.chapters){
      if(!chapter.id || !chapter.title || !Array.isArray(chapter.scenes)) throw new Error(`Invalid chapter ${chapter.id||'unknown'}`);
      for(const scene of chapter.scenes){
        if(!scene.id || !scene.primitive || !scene.message) throw new Error(`Invalid scene in ${chapter.id}`);
        if(ids.has(scene.id)) throw new Error(`Duplicate scene id ${scene.id}`);
        ids.add(scene.id);
        if(!GRAMMAR.primitives[scene.primitive]) throw new Error(`Unknown primitive ${scene.primitive}`);
        for(const ev of scene.source_evidence_ids||[]) if(!(story.evidence||[]).some(x=>x.id===ev)) throw new Error(`Unknown evidence ${ev} in ${scene.id}`);
        if((scene.effects||[]).length > (GRAMMAR.principles.max_primary_effects_per_scene + GRAMMAR.principles.max_secondary_effects_per_scene)) throw new Error(`Too many effects in ${scene.id}`);
      }
    }
    const mediaIds = new Set();
    for(const chapter of story.chapters){
      for(const scene of chapter.scenes){
        for(const m of scene.media||[]){
          if(!story.assets?.some(a=>a.id===m.asset_id)) throw new Error(`Unknown asset ${m.asset_id}`);
          if(mediaIds.has(m.asset_id) && !['comparison','reveal'].includes(scene.primitive)) console.warn(`Repeated media asset ${m.asset_id}; planner should normally avoid reuse.`);
          mediaIds.add(m.asset_id);
        }
      }
    }
  }

  function renderStory(){
    const frag = document.createDocumentFragment();
    STORY.chapters.forEach((chapter,ci) => {
      chapter.scenes.forEach((scene,si) => {
        const el = renderScene(scene,chapter,ci,si);
        frag.appendChild(el);
      });
    });
    root.appendChild(frag);
    buildNavigation();
    requestAnimationFrame(() => {
      anchors = $$('.story-scene').map(el => ({el,id:el.id,chapter:el.dataset.chapter,label:el.dataset.navLabel||el.id}));
      updateSceneEffects();
      updateActiveNavigation();
    });
  }

  function renderScene(scene,chapter,ci,si){
    const renderer = {
      hero: renderHero,
      full_screen_statement: renderStatement,
      scrollmation: renderScrollmation,
      mosaic: renderMosaic,
      matrix: renderMatrix,
      gantt: renderGantt,
      network: renderNetwork,
      background_scrollmation: renderBackgroundScrollmation,
      conclusion: renderConclusion,
      text_section: renderGeneric,
      text_over_media: renderGenericMedia,
      big_number: renderBigNumber,
      comparison: renderGeneric,
      timeline: renderGeneric,
      chart: renderGeneric,
      map: renderGeneric,
      gallery: renderGeneric,
      quote: renderGeneric,
      media: renderGenericMedia,
      data_table: renderGeneric,
      evidence_panel: renderGeneric,
      reveal: renderGenericMedia,
      scrollpoints: renderGenericMedia,
      process_flow: renderGeneric,
      custom: renderGeneric
    }[scene.primitive] || renderGeneric;
    const el = renderer(scene,chapter,ci,si);
    el.id = scene.id;
    el.dataset.chapter = chapter.id;
    el.dataset.navLabel = scene.nav_label || scene.title || chapter.nav_label || chapter.title;
    el.dataset.primitive = scene.primitive;
    el._storyScene = scene;
    el.classList.add('story-scene','chapter-anchor');
    return el;
  }

  function asset(id){ return assets.get(id); }
  function bgStyle(id){ const a=asset(id); return a?.uri ? `background-image:url('${a.uri.replace(/'/g,"%27")}')` : ''; }

  function applyDesignSystem(){
    const ds=STORY.design_system||{};
    const p=ds.palette||{};
    const style=document.documentElement.style;
    const set=(name,value)=>{ if(value) style.setProperty(name,value); };
    set('--brand-primary',p.primary);
    set('--brand-secondary',p.secondary);
    set('--brand-accent',p.accent);
    set('--deep',p.primary);
    set('--ink',p.text||p.primary);
    set('--blue',p.secondary||p.accent);
    set('--orange',p.accent||p.secondary);
    set('--paper',p.surface||p.background);
    set('--white',p.background);
    set('--muted',p.muted);
    const brand=ds.branding?.publisher||STORY.document.publisher;
    const brandText=$('.brand span:last-child');
    if(brand && brandText) brandText.textContent=brand;
    const theme=document.querySelector('meta[name="theme-color"]');
    if(theme && p.primary) theme.setAttribute('content',p.primary);
    document.body.dataset.sourceDesign=ds.source_strategy||'adapt';
  }

  function pacing(scene){
    return {...(GRAMMAR.scene_lifecycle?.default||{}),...(scene.pacing||{})};
  }

  function lifecycle(scene,p,count=1){
    const cfg=pacing(scene);
    const intro=clamp(Number(cfg.intro_hold??.16),0,.45);
    const outro=clamp(Number(cfg.outro_hold??.06),0,.35);
    if(p<intro) return {phase:'intro',index:-1,progress:0,local:0,cfg};
    if(p>1-outro) return {phase:'outro',index:Math.max(0,count-1),progress:1,local:1,cfg};
    const q=clamp((p-intro)/Math.max(.001,1-intro-outro));
    const pos=q*Math.max(1,count);
    const index=Math.min(Math.max(0,count-1),Math.floor(Math.min(.999999,q)*Math.max(1,count)));
    return {phase:'reveal',index,progress:q,local:pos-Math.floor(pos),cfg};
  }

  function visibleEnough(el){
    if(!el) return false;
    const cs=getComputedStyle(el), r=el.getBoundingClientRect();
    return cs.display!=='none' && cs.visibility!=='hidden' && Number(cs.opacity||1)>.16 && r.width>0 && r.height>0;
  }
  function overlaps(a,b,pad=12){
    if(!visibleEnough(a)||!visibleEnough(b)) return false;
    const x=a.getBoundingClientRect(), y=b.getBoundingClientRect();
    return x.left < y.right+pad && x.right+pad > y.left && x.top < y.bottom+pad && x.bottom+pad > y.top;
  }
  function resolveSceneCollisions(sceneEl){
    const guards=[['.proof-stage','.proof-title','.proof-copy'],['.horizontal-stage','.horizontal-heading','.panel-copy'],['.deliverable-stage','.deliverable-heading','.delivery-copy'],['.network-stage','.network-title','.workshop-copy']];
    for(const [stageSel,titleSel,copySel] of guards){
      const stage=sceneEl.querySelector(stageSel); if(!stage) continue;
      const title=stage.querySelector(titleSel);
      const copies=[...stage.querySelectorAll(copySel)].filter(visibleEnough);
      stage.classList.toggle('collision-safe',copies.some(copy=>overlaps(title,copy)));
    }
  }
  function sourceButton(scene,label='Source'){ return `<button class="source-button" type="button" data-scene-source="${esc(scene.id)}">${esc(label)}</button>`; }
  function sceneEvidence(scene){ return (scene.source_evidence_ids||[]).map(id=>evidence.get(id)).filter(Boolean); }
  function sceneAssets(scene){
    const ids=new Set((scene.media||[]).map(x=>x.asset_id).filter(Boolean));
    for(const item of scene.data?.items||[]) if(item.asset_id) ids.add(item.asset_id);
    for(const step of scene.data?.steps||[]) if(step.asset_id) ids.add(step.asset_id);
    return [...ids].map(id=>asset(id)).filter(Boolean);
  }

  function mediaMarkup(a,cls='hero-media'){
    if(!a) return `<div class="${cls}"></div>`;
    if(a.type==='video') return `<div class="${cls}"><video autoplay muted loop playsinline poster="${esc(a.fallback_image||'')}"><source src="${esc(a.uri)}"></video></div>`;
    return `<div class="${cls}" style="${bgStyle(a.id)}"></div>`;
  }

  function renderHero(scene){
    const section=document.createElement('section'); section.className='hero';
    const a=asset(scene.media?.[0]?.asset_id);
    section.innerHTML = `${mediaMarkup(a)}<div class="hero-copy"><p class="kicker">${esc(scene.kicker||'')}</p><h1>${applyEmphasis(scene.title||scene.message,scene.emphasis)}</h1>${scene.body?`<p class="hero-deck">${applyEmphasis(scene.body,scene.emphasis)}</p>`:''}${sourceButton(scene)}</div><div class="scroll-cue">Défiler</div>`;
    return section;
  }

  function applyEmphasis(text,emphasis=[]){
    let html=esc(text);
    for(const e of emphasis){
      const needle=esc(e.text); if(!needle) continue;
      const cls=e.style==='scroll_highlight'?'scroll-highlight':`em-${esc(e.style)}`;
      html=html.replace(needle,`<mark class="${cls}">${needle}</mark>`);
    }
    return html;
  }

  function renderStatement(scene){
    const section=document.createElement('section'); section.className='statement';
    const text=String(scene.body||scene.message);
    const first=text.split('. ')[0] + (text.includes('. ')?'.':'');
    const rest=text.slice(first.length).trim();
    section.innerHTML=`<div class="statement-inner"><p>${applyEmphasis(first,scene.emphasis)}</p><h2>${applyEmphasis(rest||text,scene.emphasis)}</h2>${sourceButton(scene)}</div>`;
    return section;
  }

  function renderScrollmation(scene,chapter){
    if(scene.semantic_role==='decision_sequence') return renderDecision(scene,chapter);
    if(scene.semantic_role==='ordered_method') return renderHorizontalPanels(scene,chapter,'method');
    if(scene.semantic_role==='ordered_outputs') return renderDeliverables(scene,chapter);
    return renderStickySteps(scene,chapter);
  }

  function renderDecision(scene,chapter){
    const steps=scene.data?.steps||[]; const section=document.createElement('section'); section.className='scrolly scene-dark';
    const a=asset(scene.media?.[0]?.asset_id);
    section.innerHTML=`<div class="sticky-stage decision-stage"><div class="decision-bg" style="${a?bgStyle(a.id):''}"></div><div class="scene-title"><span class="chapter-no">${esc(chapter.nav_label||'')}</span><h2>${esc(scene.title||chapter.title)}</h2></div><svg class="decision-path" viewBox="0 0 1000 700" aria-hidden="true"><path d="M170 520 C330 460 360 300 500 315 C650 330 655 500 830 210"/><circle cx="170" cy="520" r="11"/><circle cx="500" cy="315" r="11"/><circle cx="830" cy="210" r="11"/></svg><div class="decision-copy"><div class="eyebrow"></div><h3></h3><p></p>${sourceButton(scene)}</div><div class="decision-labels">${steps.map((s,i)=>`<div class="decision-label" data-i="${i}"><b>${String(i+1).padStart(2,'0')}</b><span>${esc(s.label||s.title)}</span></div>`).join('')}</div></div><div class="scroll-space"></div>`;
    section._update=p=>{
      const idx=Math.min(steps.length-1,Math.floor(clamp(p*.999)*steps.length)); const s=steps[idx]||{};
      $('.eyebrow',section).textContent=s.kicker||''; $('h3', $('.decision-copy',section)).textContent=s.title||''; $('p', $('.decision-copy',section)).textContent=s.text||'';
      $$('.decision-label',section).forEach((x,i)=>x.classList.toggle('active',i===idx));
      $$('.decision-path circle',section).forEach((x,i)=>x.classList.toggle('active',i<=idx));
      const path=$('.decision-path path',section); if(path) path.style.strokeDashoffset=String(1600*(1-clamp(.14+p*.92)));
      const bg=$('.decision-bg',section); if(bg&&!motionReduced) bg.style.transform=`scale(${1.08+p*.12}) translate3d(${(p-.5)*1.2}%,0,0)`;
    };
    return section;
  }

  function renderMosaic(scene,chapter){
    const items=scene.data?.items||[]; const section=document.createElement('section'); section.className='scrolly scene-dark';
    const mode=pacing(scene).reveal_mode||'one_at_a_time';
    section.innerHTML=`<div class="sticky-stage mosaic-stage"><div class="mosaic ${mode==='one_at_a_time'?'progressive':''}">${items.map((it,i)=>`<article class="mosaic-tile" data-i="${i}" tabindex="${scene.interaction?.hover==='focus'?'0':'-1'}"><div class="mosaic-image" style="${bgStyle(it.asset_id)}"></div><div class="mosaic-copy"><b>${String(i+1).padStart(2,'0')}</b><h3>${applyEmphasis(it.title||'',it.emphasis||scene.emphasis)}</h3><p>${applyEmphasis(it.text||'',it.emphasis||scene.emphasis)}</p></div></article>`).join('')}</div><div class="mosaic-intro"><span class="chapter-no">${esc(chapter.nav_label||'')}</span><h2>${applyEmphasis(scene.title||chapter.title,scene.emphasis)}</h2>${sourceButton(scene)}</div></div><div class="scroll-space long"></div>`;
    const tiles=$('.mosaic-tile',section);
    if(scene.interaction?.hover==='focus') tiles.forEach((tile,i)=>{
      const on=()=>{ tiles.forEach((x,j)=>x.classList.toggle('hover-active',i===j)); };
      tile.addEventListener('pointerenter',on); tile.addEventListener('focus',on);
      tile.addEventListener('pointerleave',()=>tiles.forEach(x=>x.classList.remove('hover-active')));
      tile.addEventListener('blur',()=>tiles.forEach(x=>x.classList.remove('hover-active')));
    });
    section._update=p=>{
      const intro=$('.mosaic-intro',section), mosaic=$('.mosaic',section), life=lifecycle(scene,p,items.length);
      const isIntro=life.phase==='intro'; section.classList.toggle('scene-intro',isIntro);
      intro.style.opacity=isIntro?'1':'0'; intro.style.pointerEvents=isIntro?'auto':'none';
      mosaic.classList.toggle('focused',!isIntro);
      tiles.forEach((x,i)=>{
        x.classList.toggle('active',!isIntro && i===life.index);
        x.classList.toggle('past',!isIntro && i<life.index);
      });
    };
    return section;
  }

  function renderMatrix(scene,chapter){
    const d=scene.data||{}; const qs=d.quadrants||[]; const pts=d.points||[]; const section=document.createElement('section'); section.className='scrolly';
    section.innerHTML=`<div class="sticky-stage matrix-stage"><div class="matrix-head"><span class="chapter-no">${esc(chapter.nav_label||'')}</span><h2>${esc(scene.title||chapter.title)}</h2></div><div class="matrix-visual"><div class="matrix-quad matrix-q1">${esc(qs[0]||'')}</div><div class="matrix-quad matrix-q2">${esc(qs[1]||'')}</div><div class="matrix-quad matrix-q3">${esc(qs[2]||'')}</div><div class="matrix-quad matrix-q4">${esc(qs[3]||'')}</div><div class="matrix-axis x"></div><div class="matrix-axis y"></div>${pts.map((p,i)=>`<div class="matrix-point p${i+1}"><i></i><span>${esc(p)}</span></div>`).join('')}</div><div class="matrix-caption"><strong>${esc(d.y_label||'')} × ${esc(d.x_label||'')}</strong><span>${esc(scene.message)}</span>${sourceButton(scene)}</div></div><div class="scroll-space"></div>`;
    section._update=p=>{ const m=$('.matrix-visual',section); m.classList.toggle('axes',p>.1); m.classList.toggle('points',p>.45); $$('.matrix-quad',section).forEach((x,i)=>x.classList.toggle('active',p>.18+i*.09)); };
    return section;
  }

  function renderHorizontalPanels(scene,chapter,kind='generic'){
    const steps=scene.data?.steps||[]; const section=document.createElement('section'); section.className='scrolly scene-dark';
    section.innerHTML=`<div class="sticky-stage horizontal-stage"><div class="horizontal-heading"><span class="chapter-no">${esc(chapter.nav_label||'')}</span><h2>${applyEmphasis(scene.title||chapter.title,scene.emphasis)}</h2></div><div class="horizontal-track">${steps.map((s,i)=>`<article class="horizontal-panel"><div class="panel-bg" style="${bgStyle(s.asset_id)}"></div><div class="panel-copy"><b>${esc(s.n||String(i+1).padStart(2,'0'))}</b><p>${applyEmphasis(s.title||'',s.emphasis||scene.emphasis)}</p><h3>${applyEmphasis(s.headline||s.title||'',s.emphasis||scene.emphasis)}</h3><span>${applyEmphasis(s.text||'',s.emphasis||scene.emphasis)}</span></div></article>`).join('')}</div><div class="horizontal-source">${sourceButton(scene)}</div></div><div class="scroll-space ${steps.length>4?'long':''}"></div>`;
    section._update=p=>{ const track=$('.horizontal-track',section); const pos=clamp(p)*(Math.max(1,steps.length-1)); const x=pos*innerWidth; track.style.transform=`translate3d(${-x}px,0,0)`; $$('.panel-bg',section).forEach((bg,i)=>{if(!motionReduced) bg.style.transform=`scale(1.08) translate3d(${(i-pos)*1.2}%,0,0)`;}); };
    return section;
  }

  function renderGantt(scene,chapter){
    const d=scene.data||{}, tasks=d.tasks||[], periods=d.periods||[]; const section=document.createElement('section'); section.className='scrolly';
    section.innerHTML=`<div class="sticky-stage planning-stage"><div class="planning-copy"><span class="chapter-no">${esc(chapter.nav_label||'')}</span><h2>${esc(scene.title||chapter.title)}</h2>${sourceButton(scene)}</div><div class="timeline-shell"><div class="week-row"><div class="week">Séquence</div>${periods.map(p=>`<div class="week">${esc(p)}</div>`).join('')}</div><div class="gantt-lines">${tasks.map((t,i)=>`<div class="gantt-row" data-i="${i}"><div class="gantt-label">${esc(t.label)}</div><div class="gantt-track"><div class="gantt-bar" style="left:${(t.start/periods.length)*100}%;width:${((t.end-t.start)/periods.length)*100}%"></div></div></div>`).join('')}</div><div class="milestones">${(d.milestones||[]).map(m=>`<div class="milestone" style="left:${m.at*100}%"><b>${esc(m.id)}</b><span>${esc(m.label)}</span></div>`).join('')}</div></div></div><div class="scroll-space"></div>`;
    section._update=p=>{ const count=tasks.length; $$('.gantt-row',section).forEach((r,i)=>r.classList.toggle('active',p>(i+1)/(count+2))); $$('.milestone',section).forEach((m,i)=>m.classList.toggle('active',p>(.25+i*.18))); };
    return section;
  }

  function renderNetwork(scene,chapter){
    const d=scene.data||{}, actors=d.actors||[], steps=d.steps||[]; const section=document.createElement('section'); section.className='scrolly scene-dark'; const a=asset(scene.media?.[0]?.asset_id);
    section.innerHTML=`<div class="sticky-stage network-stage"><div class="network-bg" style="${a?bgStyle(a.id):''}"></div><div class="network-title"><span class="chapter-no">${esc(chapter.nav_label||'')}</span><h2>${esc(scene.title||chapter.title)}</h2></div><div class="orbit"><div class="orbit-ring"></div><div class="orbit-ring"></div><div class="orbit-core">${esc(d.center||'')}</div>${actors.map((x,i)=>`<div class="actor a${i+1}">${esc(x)}</div>`).join('')}</div><div class="workshop-copy"><b></b><h3></h3><p></p>${sourceButton(scene)}</div></div><div class="scroll-space"></div>`;
    section._update=p=>{ const idx=Math.min(steps.length-1,Math.floor(clamp(p*.999)*steps.length)); const s=steps[idx]||{}; $('.workshop-copy b',section).textContent=s.n||''; $('.workshop-copy h3',section).textContent=s.title||''; $('.workshop-copy p',section).textContent=s.text||''; $$('.actor',section).forEach((x,i)=>x.classList.toggle('active',i <= Math.round(p*(actors.length-1)))); };
    return section;
  }

  function renderDeliverables(scene,chapter){
    const steps=scene.data?.steps||[]; const section=document.createElement('section'); section.className='scrolly';
    section.innerHTML=`<div class="sticky-stage deliverable-stage"><div class="deliverable-heading"><span class="chapter-no">${esc(chapter.nav_label||'')}</span><h2>${esc(scene.title||chapter.title)}</h2></div><div class="deliverable-track">${steps.map((s,i)=>`<article class="delivery-card" data-n="${esc(s.n||String(i+1).padStart(2,'0'))}"><div class="delivery-copy"><b>${esc(s.n||'')}</b><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p></div></article>`).join('')}</div><div class="deliverable-source">${sourceButton(scene)}</div></div><div class="scroll-space long"></div>`;
    section._update=p=>{ const track=$('.deliverable-track',section); const pos=clamp(p)*(Math.max(1,steps.length-1)); track.style.transform=`translate3d(${-pos*innerWidth}px,0,0)`; };
    return section;
  }

  function renderBackgroundScrollmation(scene,chapter){
    const steps=scene.data?.steps||[]; const section=document.createElement('section'); section.className='scrolly scene-dark';
    section.innerHTML=`<div class="sticky-stage proof-stage"><div class="proof-bg"></div><div class="proof-title"><span class="chapter-no">${esc(chapter.nav_label||'')}</span><h2>${applyEmphasis(scene.title||chapter.title,scene.emphasis)}</h2></div><div class="proof-copy" aria-live="polite"><div class="meta"></div><h3></h3><p></p>${sourceButton(scene)}</div></div><div class="scroll-space ${steps.length>3?'long':''}"></div>`;
    section._update=p=>{
      const life=lifecycle(scene,p,steps.length), stage=$('.proof-stage',section), title=$('.proof-title',section), copy=$('.proof-copy',section), bg=$('.proof-bg',section);
      const isIntro=life.phase==='intro'; stage.classList.toggle('is-intro',isIntro);
      title.style.opacity=isIntro || life.cfg.title_behavior==='persistent' ? '1' : '0';
      title.style.pointerEvents=isIntro ? 'auto':'none';
      copy.style.opacity=isIntro?'0':'1'; copy.style.pointerEvents=isIntro?'none':'auto';
      if(!isIntro && steps.length){
        const idx=Math.max(0,life.index), st=steps[idx]||{};
        if(bg.dataset.asset!==String(st.asset_id||'')){ bg.dataset.asset=st.asset_id||''; bg.style.backgroundImage=asset(st.asset_id)?.uri?`url('${asset(st.asset_id).uri}')`:''; }
        $('.proof-copy .meta',section).textContent=st.meta||'';
        $('.proof-copy h3',section).innerHTML=applyEmphasis(st.title||'',st.emphasis||scene.emphasis);
        $('.proof-copy p',section).innerHTML=applyEmphasis(st.text||'',st.emphasis||scene.emphasis);
      } else if(isIntro){
        bg.style.backgroundImage=asset(scene.media?.[0]?.asset_id)?.uri?`url('${asset(scene.media?.[0]?.asset_id).uri}')`:'';
      }
      if(!motionReduced) bg.style.transform=`scale(${1.06+life.progress*.035})`;
    };
    return section;
  }

  function renderConclusion(scene){
    const section=document.createElement('section'); section.className='finale';
    section.innerHTML=`<div class="finale-inner"><p class="kicker">${esc(scene.kicker||'')}</p><h2>${applyEmphasis(scene.title||scene.message,scene.emphasis).replace(/\. /g,'.<br>')}</h2>${sourceButton(scene)}</div>`;
    return section;
  }

  function renderStickySteps(scene,chapter){
    const steps=scene.data?.steps||[]; const section=document.createElement('section'); section.className='generic-section';
    section.innerHTML=`<div class="generic-inner"><p class="kicker">${esc(chapter.nav_label||'')}</p><h2>${esc(scene.title||scene.message)}</h2><div class="generic-grid">${steps.map((s,i)=>`<article class="generic-card"><b>${esc(s.n||String(i+1).padStart(2,'0'))}</b><h3>${esc(s.title||'')}</h3><p>${esc(s.text||'')}</p></article>`).join('')}</div>${sourceButton(scene)}</div>`; return section;
  }
  function renderGeneric(scene,chapter){ const section=document.createElement('section'); section.className='generic-section'; const body=Array.isArray(scene.body)?scene.body.join('\n'):scene.body||scene.message; section.innerHTML=`<div class="generic-inner"><p class="kicker">${esc(chapter.nav_label||'')}</p><h2>${applyEmphasis(scene.title||scene.message,scene.emphasis)}</h2><p>${applyEmphasis(body,scene.emphasis)}</p>${sourceButton(scene)}</div>`; return section; }
  function renderGenericMedia(scene,chapter){ const section=renderGeneric(scene,chapter); const a=asset(scene.media?.[0]?.asset_id); if(a?.uri) section.style.background=`linear-gradient(rgba(255,255,255,.88),rgba(255,255,255,.88)),url('${a.uri}') center/cover`; return section; }
  function renderBigNumber(scene,chapter){ const section=document.createElement('section'); section.className='generic-section'; section.innerHTML=`<div class="generic-inner"><p class="kicker">${esc(chapter.nav_label||'')}</p><div class="big-number-value">${esc(scene.data?.value||scene.message)}</div><h2>${applyEmphasis(scene.title||'',scene.emphasis)}</h2><p>${applyEmphasis(scene.body||'',scene.emphasis)}</p>${sourceButton(scene)}</div>`; return section; }

  function buildNavigation(){
    chapterNav.innerHTML=''; microTrack.innerHTML='';
    STORY.chapters.forEach(chapter=>{
      const first=chapter.scenes[0]; if(!first) return;
      const a=document.createElement('a'); a.href=`#${first.id}`; a.dataset.chapter=chapter.id; a.textContent=chapter.nav_label||chapter.title; chapterNav.appendChild(a);
      const group=document.createElement('div'); group.className='micro-chapter'; group.dataset.chapter=chapter.id;
      group.innerHTML=`<span class="micro-chapter-label">${esc(chapter.nav_label||chapter.title)}</span><div class="micro-scenes">${chapter.scenes.map(scene=>`<button class="micro-dot" type="button" data-target="${esc(scene.id)}" aria-label="${esc(scene.nav_label||scene.title||scene.id)}"></button>`).join('')}</div>`;
      microTrack.appendChild(group);
    });
  }

  function installGlobalInteractions(){
    addEventListener('scroll', onScroll, {passive:true}); addEventListener('resize',()=>{updateSceneEffects();updateActiveNavigation();});
    document.addEventListener('click',e=>{
      const src=e.target.closest('[data-scene-source]'); if(src){ showSceneSource(src.dataset.sceneSource); return; }
      const dot=e.target.closest('.micro-dot'); if(dot){ document.getElementById(dot.dataset.target)?.scrollIntoView({behavior:motionReduced?'auto':'smooth',block:'start'}); }
    });
    $('#sourceClose').addEventListener('click',closeDrawer); $('#allSourcesBtn').addEventListener('click',showAllSources);
    $('#prevScene').addEventListener('click',()=>moveScene(-1)); $('#nextScene').addEventListener('click',()=>moveScene(1));
    document.addEventListener('keydown',e=>{
      if(!STORY.navigation.keyboard_navigation || ['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)) return;
      if((e.key==='ArrowDown' || e.key==='PageDown') && (e.altKey||e.ctrlKey)){e.preventDefault();moveScene(1)}
      if((e.key==='ArrowUp' || e.key==='PageUp') && (e.altKey||e.ctrlKey)){e.preventDefault();moveScene(-1)}
    });
    const io=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('in-view')}),{threshold:.35}); $$('.story-scene').forEach(x=>io.observe(x));
    onScroll();
  }

  function sceneProgress(el){ const span=Math.max(1,el.offsetHeight-innerHeight); return clamp((scrollY-el.offsetTop)/span); }
  function updateSceneEffects(){ for(const el of $('.story-scene')) { if(typeof el._update==='function') el._update(sceneProgress(el)); resolveSceneCollisions(el); } }
  function onScroll(){ const max=Math.max(1,document.documentElement.scrollHeight-innerHeight); progress.style.width=`${clamp(scrollY/max)*100}%`; updateSceneEffects(); updateActiveNavigation(); }

  function currentAnchorIndex(){ const y=scrollY+innerHeight*.46; let idx=0; anchors.forEach((a,i)=>{if(a.el.offsetTop<=y) idx=i;}); return idx; }
  function moveScene(delta){ const idx=clamp(currentAnchorIndex()+delta,0,anchors.length-1); anchors[idx]?.el.scrollIntoView({behavior:motionReduced?'auto':'smooth',block:'start'}); }
  function updateActiveNavigation(){ if(!anchors.length) return; const idx=currentAnchorIndex(); const cur=anchors[idx]; $$('.micro-dot').forEach(x=>x.classList.toggle('active',x.dataset.target===cur.id)); $$('.micro-chapter').forEach(x=>x.classList.toggle('active',x.dataset.chapter===cur.chapter)); $$('.chapter-nav a').forEach(x=>x.classList.toggle('active',x.dataset.chapter===cur.chapter)); }

  function showSceneSource(sceneId){
    const scene = STORY.chapters.flatMap(c=>c.scenes).find(s=>s.id===sceneId); if(!scene) return;
    const evs=sceneEvidence(scene); sourceTitle.textContent=scene.title||scene.message||'Sources';
    const refs=scene.source_refs||[], media=sceneAssets(scene);
    sourceBody.innerHTML=`${refs.map(r=>`<div class="source-card"><b>${esc(r.file)} | page ${esc(r.page)}</b>${r.quote?`<p>${esc(r.quote)}</p>`:''}</div>`).join('')}${evs.map(ev=>`<div class="source-card"><b>${esc(ev.status)} | ${esc(ev.type)}</b><p>${esc(ev.text||String(ev.value??''))}</p><div class="source-evidence">${(ev.source_refs||[]).map(r=>`<span>p.${esc(r.page)}</span>`).join('')}</div></div>`).join('')}${media.map(a=>`<div class="source-card asset-credit"><b>${esc((a.origin||'media').toUpperCase())} | visuel</b><p>${esc(a.caption||a.alt||'')}</p>${a.credit?`<p><strong>Crédit:</strong> ${esc(a.credit)}</p>`:''}${a.license?`<div class="source-evidence"><span>${esc(a.license)}</span></div>`:''}</div>`).join('')}${(scene.transformations||[]).length?`<div class="source-card"><b>Transformations éditoriales</b>${scene.transformations.map(t=>`<p><strong>${esc(t.type)}</strong> - ${esc(t.description)}</p>`).join('')}</div>`:''}`;
    openDrawer();
  }
  function showAllSources(){ sourceTitle.textContent='Sources du récit'; sourceBody.innerHTML=(STORY.evidence||[]).map(ev=>`<div class="source-card"><b>${esc(ev.status)} | ${esc(ev.type)}</b><p>${esc(ev.text||String(ev.value??''))}</p><div class="source-evidence">${(ev.source_refs||[]).map(r=>`<span>${esc(r.file)} p.${esc(r.page)}</span>`).join('')}</div></div>`).join(''); openDrawer(); }
  function openDrawer(){drawer.classList.add('open');drawer.setAttribute('aria-hidden','false')}
  function closeDrawer(){drawer.classList.remove('open');drawer.setAttribute('aria-hidden','true')}
})();
