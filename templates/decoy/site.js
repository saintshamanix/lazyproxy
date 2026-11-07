'use strict';
(() => {
  const theme = document.getElementById('theme');
  const filters = document.getElementById('filters');
  const count = document.getElementById('count');
  const notes = [...document.querySelectorAll('[data-topic]')];
  theme.hidden = false;
  filters.hidden = false;
  function setTheme(dark) {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    theme.setAttribute('aria-pressed', String(dark));
    theme.textContent = dark ? 'Morning light' : 'Evening light';
  }
  setTheme(window.matchMedia('(prefers-color-scheme: dark)').matches);
  theme.addEventListener('click', () => {
    setTheme(document.documentElement.dataset.theme !== 'dark');
  });
  filters.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-filter]');
    if (!button) return;
    for (const item of filters.querySelectorAll('button')) {
      item.setAttribute('aria-pressed', String(item === button));
    }
    let visible = 0;
    for (const note of notes) {
      note.hidden = button.dataset.filter !== 'all' && note.dataset.topic !== button.dataset.filter;
      if (!note.hidden) visible++;
    }
    count.hidden = false;
    count.textContent = `${visible} ${visible === 1 ? 'note' : 'notes'}`;
  });
  document.getElementById('season').textContent = new Intl.DateTimeFormat('en', {month: 'long', year: 'numeric'}).format(new Date());
})();
