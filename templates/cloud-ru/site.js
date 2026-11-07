'use strict';
(() => {
  const dialog = document.querySelector('#login-dialog');
  const form = document.querySelector('#login-form');
  const password = document.querySelector('#password');
  const error = document.querySelector('#login-error');
  const eye = document.querySelector('.eye');
  let opener;
  document.querySelectorAll('[data-login]').forEach(button => {
    button.addEventListener('click', () => {
      opener = button;
      form.reset();
      error.hidden = true;
      password.type = 'password';
      eye.setAttribute('aria-pressed', 'false');
      eye.setAttribute('aria-label', 'Показать пароль');
      dialog.showModal();
      document.querySelector('#login').focus();
    });
  });
  document.querySelector('.close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right ||
        event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => {
    form.reset();
    password.type = 'password';
    error.hidden = true;
    opener?.focus();
  });
  eye.addEventListener('click', () => {
    const visible = password.type === 'password';
    password.type = visible ? 'text' : 'password';
    eye.setAttribute('aria-pressed', String(visible));
    eye.setAttribute('aria-label', visible ? 'Скрыть пароль' : 'Показать пароль');
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    // No credential reads, requests, logging, cookies or storage.
    error.hidden = false;
    password.value = '';
    password.focus();
  });
  form.addEventListener('input', () => { error.hidden = true; });
})();
