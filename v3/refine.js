(() => {
  'use strict';
  const clamp = (v,min=0,max=1) => Math.min(max,Math.max(min,v));

  function progress(el){
    if(!el) return 0;
    const top = el.getBoundingClientRect().top + window.scrollY;
    const span = Math.max(1, el.offsetHeight - window.innerHeight);
    return clamp((window.scrollY - top) / span);
  }

  function refineHorizontal(sceneId, trackSelector, itemSelector, copySelector, headingSelector){
    const scene = document.getElementById(sceneId);
    if(!scene) return;
    const items = [...scene.querySelectorAll(itemSelector)];
    if(!items.length) return;
    const p = progress(scene);
    const pos = p * Math.max(1, items.length - 1);
    const active = Math.round(pos);
    const heading = scene.querySelector(headingSelector);
    if(heading){
      const fade = p < .08 ? 1 : clamp(1 - (p - .08) / .13);
      heading.style.opacity = String(fade);
      heading.style.transform = `translate3d(0,${(1-fade)*-10}px,0)`;
      heading.style.pointerEvents = fade < .08 ? 'none' : 'auto';
    }
    items.forEach((item,i) => {
      const copy = item.querySelector(copySelector);
      if(!copy) return;
      const isActive = i === active;
      copy.style.opacity = isActive ? '1' : '0';
      copy.style.transform = `translate3d(${isActive ? 0 : (i < active ? -18 : 18)}px,0,0)`;
      copy.style.pointerEvents = isActive ? 'auto' : 'none';
    });
  }

  function update(){
    refineHorizontal('method-track','.horizontal-track','.horizontal-panel','.panel-copy','.horizontal-heading');
    refineHorizontal('deliverable-sequence','.deliverable-track','.delivery-card','.delivery-copy','.deliverable-heading');
  }

  addEventListener('scroll', update, {passive:true});
  addEventListener('resize', update);
  addEventListener('load', () => requestAnimationFrame(update));
  requestAnimationFrame(() => requestAnimationFrame(update));
})();
