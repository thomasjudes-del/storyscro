(() => {
  'use strict';
  const clamp = (v,min=0,max=1) => Math.min(max,Math.max(min,v));
  let navEnhanced = false;
  let scrubbing = false;

  function progress(el){
    if(!el) return 0;
    const top = el.getBoundingClientRect().top + window.scrollY;
    const span = Math.max(1, el.offsetHeight - window.innerHeight);
    return clamp((window.scrollY - top) / span);
  }

  function refineHorizontalScene(scene, itemSelector, copySelector, headingSelector, trackSelector){
    if(!scene) return;
    const items = [...scene.querySelectorAll(itemSelector)];
    if(!items.length) return;
    const p = progress(scene);
    const pos = p * Math.max(1, items.length - 1);
    const active = Math.round(pos);
    const narrow = matchMedia('(max-width:820px)').matches;
    const track = scene.querySelector(trackSelector);
    const heading = scene.querySelector(headingSelector);

    if(track){
      if(narrow){
        track.style.setProperty('transform','none','important');
        track.style.setProperty('position','absolute');
        track.style.setProperty('inset','0');
      } else {
        track.style.removeProperty('position');
        track.style.removeProperty('inset');
        if(track.style.getPropertyPriority('transform') === 'important') track.style.removeProperty('transform');
      }
    }

    if(heading){
      const fade = narrow
        ? (p < .055 ? 1 : clamp(1 - (p - .055) / .07))
        : (p < .08 ? 1 : clamp(1 - (p - .08) / .13));
      heading.style.opacity = String(fade);
      heading.style.transform = `translate3d(0,${(1-fade)*-10}px,0)`;
      heading.style.pointerEvents = fade < .08 ? 'none' : 'auto';
    }

    items.forEach((item,i) => {
      const copy = item.querySelector(copySelector);
      const isActive = i === active;
      if(narrow){
        item.style.setProperty('position','absolute','important');
        item.style.setProperty('inset','0','important');
        item.style.setProperty('width','100vw','important');
        item.style.setProperty('opacity',isActive ? '1' : '0','important');
        item.style.setProperty('pointer-events',isActive ? 'auto' : 'none','important');
        item.style.setProperty('transform','none','important');
      } else {
        for(const prop of ['position','inset','width','opacity','pointer-events','transform']){
          if(item.style.getPropertyPriority(prop) === 'important' || item.style.getPropertyValue(prop)) item.style.removeProperty(prop);
        }
      }
      if(!copy) return;
      copy.style.opacity = isActive ? '1' : '0';
      copy.style.transform = `translate3d(${isActive ? 0 : (i < active ? -22 : 22)}px,0,0)`;
      copy.style.pointerEvents = isActive ? 'auto' : 'none';
    });
  }

  function refineNarrativeTracks(){
    document.querySelectorAll('.horizontal-stage').forEach(stage => {
      refineHorizontalScene(stage.closest('.story-scene') || stage, '.horizontal-panel', '.panel-copy', '.horizontal-heading', '.horizontal-track');
    });
    document.querySelectorAll('.deliverable-stage').forEach(stage => {
      refineHorizontalScene(stage.closest('.story-scene') || stage, '.delivery-card', '.delivery-copy', '.deliverable-heading', '.deliverable-track');
    });
  }

  function scenes(){ return [...document.querySelectorAll('.story-scene')]; }

  function currentSceneIndex(){
    const all = scenes();
    if(!all.length) return 0;
    const y = window.innerHeight * .46;
    let containing = -1;
    let nearest = 0;
    let nearestDistance = Infinity;
    all.forEach((el,i) => {
      const r = el.getBoundingClientRect();
      if(r.top <= y && r.bottom >= y) containing = i;
      const distance = r.bottom < y ? y - r.bottom : (r.top > y ? r.top - y : 0);
      if(distance < nearestDistance){ nearestDistance = distance; nearest = i; }
    });
    return containing >= 0 ? containing : nearest;
  }

  function syncNavigation(){
    const all = scenes();
    if(!all.length) return;
    const cur = all[currentSceneIndex()];
    if(!cur) return;
    const chapter = cur.dataset.chapter;
    document.querySelectorAll('.micro-dot').forEach(dot => dot.classList.toggle('active', dot.dataset.target === cur.id));
    document.querySelectorAll('.micro-chapter').forEach(group => group.classList.toggle('active', group.dataset.chapter === chapter));
    document.querySelectorAll('.chapter-nav a').forEach(link => link.classList.toggle('active', link.dataset.chapter === chapter));
  }

  function moveScene(delta){
    const all = scenes();
    if(!all.length) return;
    const idx = clamp(currentSceneIndex() + delta, 0, all.length - 1);
    all[idx].scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block:'start'});
  }

  function globalProgress(){
    const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    return clamp(window.scrollY / max);
  }

  function scrubTo(clientY){
    const track = document.getElementById('microTrack');
    if(!track) return;
    const rail = track.querySelector('.micro-scrub-rail');
    const r = (rail || track).getBoundingClientRect();
    const p = clamp((clientY - r.top) / Math.max(1,r.height));
    const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    window.scrollTo({top:p * max, behavior:'auto'});
  }

  function updateScrubber(){
    const track = document.getElementById('microTrack');
    const handle = track?.querySelector('.micro-scrub-handle');
    if(!track || !handle) return;
    const rail = track.querySelector('.micro-scrub-rail');
    const h = (rail || track).clientHeight;
    handle.style.top = `${globalProgress() * h}px`;
  }

  function enhanceMicroNav(){
    const track = document.getElementById('microTrack');
    if(!track || navEnhanced || !track.querySelector('.micro-dot')) return;
    navEnhanced = true;
    document.getElementById('microNav')?.classList.add('micro-nav-enhanced');

    track.querySelectorAll('.micro-chapter').forEach(group => {
      const chapterLabel = group.querySelector('.micro-chapter-label');
      const firstDot = group.querySelector('.micro-dot');
      if(chapterLabel && firstDot){
        chapterLabel.setAttribute('role','button');
        chapterLabel.setAttribute('tabindex','0');
        chapterLabel.setAttribute('title','Aller au chapitre');
        const go = () => firstDot.click();
        chapterLabel.addEventListener('click',go);
        chapterLabel.addEventListener('keydown',e=>{
          if(e.key==='Enter' || e.key===' '){ e.preventDefault(); go(); }
        });
      }
      group.querySelectorAll('.micro-dot').forEach(dot => {
        if(dot.querySelector('.micro-scene-label')) return;
        const span = document.createElement('span');
        span.className = 'micro-scene-label';
        span.textContent = dot.getAttribute('aria-label') || 'Scène';
        dot.appendChild(span);
      });
    });

    const rail = document.createElement('div');
    rail.className = 'micro-scrub-rail';
    rail.setAttribute('aria-hidden','true');
    const handle = document.createElement('div');
    handle.className = 'micro-scrub-handle';
    handle.setAttribute('role','slider');
    handle.setAttribute('aria-label','Position dans le récit');
    handle.setAttribute('aria-valuemin','0');
    handle.setAttribute('aria-valuemax','100');
    rail.appendChild(handle);
    track.appendChild(rail);

    rail.addEventListener('pointerdown',e=>{
      scrubbing = true;
      rail.setPointerCapture?.(e.pointerId);
      scrubTo(e.clientY);
      e.preventDefault();
    });
    rail.addEventListener('pointermove',e=>{
      if(!scrubbing) return;
      scrubTo(e.clientY);
      e.preventDefault();
    });
    const stop = () => { scrubbing = false; };
    rail.addEventListener('pointerup',stop);
    rail.addEventListener('pointercancel',stop);
    updateScrubber();
  }

  function update(){
    refineNarrativeTracks();
    enhanceMicroNav();
    syncNavigation();
    requestAnimationFrame(syncNavigation);
    updateScrubber();
    const handle = document.querySelector('.micro-scrub-handle');
    if(handle) handle.setAttribute('aria-valuenow',String(Math.round(globalProgress()*100)));
  }

  document.addEventListener('keydown',e=>{
    if(e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)) return;
    if(e.key==='ArrowDown'){ e.preventDefault(); moveScene(1); }
    if(e.key==='ArrowUp'){ e.preventDefault(); moveScene(-1); }
  });

  const observer = new MutationObserver(() => { enhanceMicroNav(); update(); });
  const target = document.getElementById('microTrack');
  if(target) observer.observe(target,{childList:true,subtree:true});

  addEventListener('scroll', update, {passive:true});
  addEventListener('resize', update);
  addEventListener('load', () => requestAnimationFrame(update));
  requestAnimationFrame(() => requestAnimationFrame(update));
})();
