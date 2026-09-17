(() => {
  const data = window.STORYSCRO || { sources: {}, images: {} };
  const viewButtons = [...document.querySelectorAll('[data-view-target]')];
  const views = [...document.querySelectorAll('.view')];
  const drawer = document.getElementById('sourceDrawer');
  const drawerTitle = document.getElementById('sourceTitle');
  const drawerBody = document.getElementById('sourceBody');
  const editPanel = document.getElementById('editPanel');
  const editToggle = document.getElementById('editToggle');
  const imageSelect = document.getElementById('imageSelect');
  let activeView = location.hash.replace('#','') || 'narrative';

  const setView = (name, scrollTop = true) => {
    if (!document.getElementById(`view-${name}`)) name = 'narrative';
    activeView = name;
    views.forEach(v => v.classList.toggle('active', v.id === `view-${name}`));
    viewButtons.forEach(b => b.classList.toggle('active', b.dataset.viewTarget === name));
    history.replaceState(null, '', `#${name}`);
    if (scrollTop) window.scrollTo({ top: 0, behavior: 'smooth' });
    restoreHiddenSections();
  };

  viewButtons.forEach(btn => btn.addEventListener('click', () => setView(btn.dataset.viewTarget)));
  setView(activeView, false);

  const questionStages = {
    q1: ['01', 'Où sommes-nous réellement vulnérables ?', "Croiser aléas, exposition, dépendances fonctionnelles et capacités locales, sans réduire le diagnostic à une carte de risques."],
    q2: ['02', 'Quelles actions changent la trajectoire ?', "Distinguer les mesures structurantes des actions opportunistes et expliciter les arbitrages coût, impact, délai et acceptabilité."],
    q3: ['03', 'Comment rendre la feuille de route exécutable ?', "Associer responsabilités, jalons, financement, indicateurs et gouvernance pour que le plan survive à la phase d'étude."]
  };

  const phaseStages = {
    p1: ['01', 'Cadrer et objectiver', "Aligner les décisions attendues, cibler la collecte, définir les unités d'analyse et préparer les entretiens."],
    p2: ['02', 'Diagnostiquer et comparer', "Analyser les données, cartographier les dépendances, conduire les entretiens et comparer les mécanismes de mise en œuvre."],
    p3: ['03', 'Construire et arbitrer', "Mettre les scénarios en tension, tester les actions et consolider les choix avec des critères explicites."],
    p4: ['04', 'Programmer et sécuriser', "Transformer les choix en feuille de route, responsabilités, financements, indicateurs, jalons et 100 premiers jours."]
  };

  const updateScrolly = (block, stageData, step) => {
    const label = block.querySelector('.scrolly-label');
    const bg = block.querySelector('.scrolly-bg');
    if (!label || !step) return;
    const d = stageData[step.dataset.scene];
    if (!d) return;
    label.querySelector('.giant').textContent = d[0];
    label.querySelector('h3').textContent = d[1];
    label.querySelector('p').textContent = d[2];
    block.querySelectorAll('.story-step').forEach(s => s.classList.toggle('active', s === step));
    const zoom = Number(step.dataset.zoom || 1.12);
    const x = Number(step.dataset.x || 50);
    const y = Number(step.dataset.y || 50);
    if (bg) {
      bg.style.transform = `scale(${zoom})`;
      bg.style.backgroundPosition = `${x}% ${y}%`;
    }
  };

  document.querySelectorAll('.scrolly-block').forEach(block => {
    const mode = block.dataset.scrolly;
    const stageData = mode === 'phases' ? phaseStages : questionStages;
    const steps = [...block.querySelectorAll('.story-step')];
    if (steps[0]) updateScrolly(block, stageData, steps[0]);
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) updateScrolly(block, stageData, entry.target);
      });
    }, { threshold: .58 });
    steps.forEach(s => observer.observe(s));
  });

  const parallax = () => {
    const vh = window.innerHeight;
    document.querySelectorAll('.parallax').forEach(section => {
      const r = section.getBoundingClientRect();
      if (r.bottom < 0 || r.top > vh) return;
      const progress = (vh - r.top) / (vh + r.height);
      const y = (progress - .5) * 120;
      const media = section.querySelector('.parallax-media');
      if (media) media.style.setProperty('--parallax', `${y}px`);
    });
    const hero = document.querySelector('.view.active .hero-media');
    if (hero) {
      const y = Math.min(window.scrollY * .16, 90);
      hero.style.transform = `translateY(${y}px) scale(1.1)`;
    }
  };
  window.addEventListener('scroll', parallax, { passive: true });
  parallax();

  const buildGantt = (id) => {
    const g = document.getElementById(id);
    if (!g || g.children.length) return;
    const rows = [
      ['Séquence', ...Array.from({ length: 12 }, (_, i) => `S${i + 1}`)],
      ['Cadrage & collecte',1,1,0,0,0,0,0,0,0,0,0,0],
      ['Diagnostic & entretiens',0,2,2,2,2,2,0,0,0,0,0,0],
      ['Benchmark & options',0,0,0,3,3,3,3,0,0,0,0,0],
      ['Scénarios & ateliers',0,0,0,0,0,0,4,4,4,0,0,0],
      ['Feuille de route',0,0,0,0,0,0,0,0,5,5,5,0],
      ['Finalisation & transfert',0,0,0,0,0,0,0,0,0,0,6,6]
    ];
    const cls = ['', 'g-blue2', 'g-blue', 'g-green', 'g-orange', 'g-purple', 'g-dark'];
    rows.forEach((row, ri) => row.forEach((v, ci) => {
      const cell = document.createElement('div');
      cell.className = `gcell${ci === 0 ? ' grow' : ''}${ri > 0 && ci > 0 && v ? ` ${cls[v]}` : ''}`;
      if (ri === 0 || ci === 0) cell.textContent = v;
      g.appendChild(cell);
    }));
  };
  ['ganttNarrative','ganttData','ganttTldr'].forEach(buildGantt);

  const drawNetwork = () => {
    document.querySelectorAll('.network').forEach(net => {
      net.querySelectorAll('.edge').forEach(e => e.remove());
      const coreEl = net.querySelector('.node.core');
      if (!coreEl) return;
      const nr = net.getBoundingClientRect();
      const cr = coreEl.getBoundingClientRect();
      const core = { x: cr.left - nr.left + cr.width / 2, y: cr.top - nr.top + cr.height / 2 };
      net.querySelectorAll('.node:not(.core)').forEach(n => {
        const r = n.getBoundingClientRect();
        const x = r.left - nr.left + r.width / 2;
        const y = r.top - nr.top + r.height / 2;
        const dx = x - core.x;
        const dy = y - core.y;
        const edge = document.createElement('div');
        edge.className = 'edge';
        edge.style.width = `${Math.hypot(dx,dy)}px`;
        edge.style.left = `${core.x}px`;
        edge.style.top = `${core.y}px`;
        edge.style.transform = `rotate(${Math.atan2(dy,dx)}rad)`;
        net.prepend(edge);
      });
    });
  };
  window.addEventListener('load', drawNetwork);
  window.addEventListener('resize', drawNetwork);

  const openSource = (key) => {
    if (!drawer) return;
    const s = data.sources[key];
    drawerTitle.textContent = s ? s.title : 'Sources du document';
    if (s) {
      drawerBody.innerHTML = `<div class="source-card"><b>PDF, page ${s.page}</b><p>${s.text}</p></div><div class="source-card"><b>Transformation</b><p>Réorganisation éditoriale, condensation et mise en scène web. Aucun chiffre source n'est modifié et aucune donnée nouvelle n'est ajoutée.</p></div>`;
    } else {
      drawerBody.innerHTML = `<div class="source-list">${Object.entries(data.sources).map(([id,src]) => `<button class="source-link" data-source-jump="${id}"><strong>Page ${src.page}</strong><small>${src.title}</small></button>`).join('')}</div>`;
    }
    drawer.classList.add('open');
  };
  document.addEventListener('click', e => {
    const source = e.target.closest('[data-source]');
    if (source) openSource(source.dataset.source);
    const jump = e.target.closest('[data-source-jump]');
    if (jump) openSource(jump.dataset.sourceJump);
  });
  document.getElementById('sourcesToggle')?.addEventListener('click', () => openSource());
  document.getElementById('sourceClose')?.addEventListener('click', () => drawer.classList.remove('open'));

  const editableElements = () => [...document.querySelectorAll('[data-editable]')];
  const saveEdits = () => {
    const edits = {};
    editableElements().forEach(el => {
      if (el.dataset.key) edits[el.dataset.key] = el.innerHTML;
    });
    localStorage.setItem('storyscro-edits', JSON.stringify(edits));
  };
  const restoreEdits = () => {
    try {
      const edits = JSON.parse(localStorage.getItem('storyscro-edits') || '{}');
      editableElements().forEach(el => {
        if (el.dataset.key && edits[el.dataset.key] != null) el.innerHTML = edits[el.dataset.key];
      });
    } catch (_) {}
  };
  restoreEdits();

  const installSectionControls = () => {
    document.querySelectorAll('section[data-section-id]').forEach(section => {
      if (section.querySelector('.section-edit')) return;
      const btn = document.createElement('button');
      btn.className = 'section-edit';
      btn.textContent = 'Masquer';
      btn.addEventListener('click', e => {
        e.stopPropagation();
        section.classList.add('hidden-section');
        saveHiddenSections();
      });
      section.appendChild(btn);
    });
  };
  installSectionControls();

  const saveHiddenSections = () => {
    const ids = [...document.querySelectorAll('.hidden-section[data-section-id]')].map(s => s.dataset.sectionId);
    localStorage.setItem('storyscro-hidden', JSON.stringify(ids));
  };
  function restoreHiddenSections(){
    let ids = [];
    try { ids = JSON.parse(localStorage.getItem('storyscro-hidden') || '[]'); } catch (_) {}
    document.querySelectorAll('[data-section-id]').forEach(s => s.classList.toggle('hidden-section', ids.includes(s.dataset.sectionId)));
  }
  restoreHiddenSections();

  const setEditing = (on) => {
    document.body.classList.toggle('editing', on);
    editableElements().forEach(el => el.contentEditable = on ? 'true' : 'false');
    editToggle.textContent = on ? 'Fermer édition' : 'Edit';
    if (!on) saveEdits();
  };
  editToggle?.addEventListener('click', () => setEditing(!document.body.classList.contains('editing')));

  document.getElementById('densityToggle')?.addEventListener('click', () => document.body.classList.toggle('compact'));
  document.getElementById('restoreSections')?.addEventListener('click', () => {
    localStorage.removeItem('storyscro-hidden');
    document.querySelectorAll('.hidden-section').forEach(s => s.classList.remove('hidden-section'));
  });
  document.getElementById('resetEdits')?.addEventListener('click', () => {
    localStorage.removeItem('storyscro-edits');
    localStorage.removeItem('storyscro-hidden');
    location.reload();
  });

  if (imageSelect) {
    imageSelect.addEventListener('change', () => {
      const url = data.images[imageSelect.value];
      if (url) document.documentElement.style.setProperty('--hero-image', `url('${url}')`);
    });
  }

  document.addEventListener('input', e => {
    if (document.body.classList.contains('editing') && e.target.closest('[data-editable]')) saveEdits();
  });
})();
