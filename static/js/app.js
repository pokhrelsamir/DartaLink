/* DartaLink - vanilla JS: toasts, modals, dropdowns, sidebar, notifications */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- toasts ---------- */
  var toastBox = $('#toasts');
  function toast(message, type, timeout) {
    if (!toastBox) return;
    var el = document.createElement('div');
    el.className = 'toast ' + (type || 'info');
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    var p = document.createElement('p'); p.textContent = message;
    var b = document.createElement('button'); b.type = 'button'; b.setAttribute('aria-label', 'Dismiss'); b.innerHTML = '&times;';
    el.appendChild(p); el.appendChild(b); toastBox.appendChild(el);
    function close() { el.classList.add('leaving'); setTimeout(function () { el.remove(); }, 220); }
    b.addEventListener('click', close);
    setTimeout(close, timeout || (type === 'error' ? 8000 : 5000));
  }
  window.DartaLink = { toast: toast };
  var msgNode = $('#django-messages');
  if (msgNode) {
    try {
      JSON.parse(msgNode.textContent).forEach(function (m) {
        var t = /error/.test(m.tags) ? 'error' : /success/.test(m.tags) ? 'success' : /warning/.test(m.tags) ? 'warning' : 'info';
        toast(m.message, t);
      });
    } catch (e) { /* ignore */ }
  }

  /* ---------- modals ---------- */
  var lastFocus = null;
  var modalCloseTimer = null;
  function openModal(id) {
    var m = document.getElementById(id); if (!m) return;
    if (modalCloseTimer) clearTimeout(modalCloseTimer);
    lastFocus = document.activeElement; m.classList.remove('closing'); m.classList.add('open'); m.removeAttribute('aria-hidden');
    document.body.style.overflow = 'hidden';
    var f = $('textarea, select, input:not([type=hidden])', m) || $('button', m); if (f) f.focus();
  }
  function closeModals() {
    var open = $$('.modal-backdrop.open');
    open.forEach(function (m) {
      m.classList.add('closing');
      modalCloseTimer = setTimeout(function () {
        m.classList.remove('open', 'closing'); m.setAttribute('aria-hidden', 'true');
      }, 190);
    });
    document.body.style.overflow = ''; if (lastFocus) lastFocus.focus();
  }
  document.addEventListener('click', function (e) {
    var open = e.target.closest('[data-modal-open]');
    if (open) { e.preventDefault(); openModal(open.getAttribute('data-modal-open')); return; }
    if (e.target.closest('[data-modal-close]') || (e.target.classList && e.target.classList.contains('modal-backdrop'))) { closeModals(); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeModals(); closeMenus(); closeSidebar(); }
    if (e.key === 'Tab') { /* keep focus inside an open modal */
      var m = $('.modal-backdrop.open'); if (!m) return;
      var f = $$('a[href], button:not([disabled]), input:not([type=hidden]), select, textarea', m);
      if (!f.length) return; var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  /* ---------- confirmations ---------- */
  var confirmModal = null;
  function askConfirmation(message, title, tone) {
    return new Promise(function (resolve) {
      if (confirmModal) confirmModal.remove();
      confirmModal = document.createElement('div');
      confirmModal.className = 'modal-backdrop confirm-backdrop open';
      confirmModal.setAttribute('role', 'dialog');
      confirmModal.setAttribute('aria-modal', 'true');
      confirmModal.setAttribute('aria-labelledby', 'confirm-title');
      confirmModal.innerHTML = '<div class="modal confirm-modal">' +
        '<div class="confirm-icon ' + (tone || 'warning') + '" aria-hidden="true">' + (tone === 'danger' ? '!' : '?') + '</div>' +
        '<div class="modal-head"><h2 id="confirm-title">' + (title || 'Please confirm') + '</h2></div>' +
        '<div class="modal-body"><p class="confirm-message"></p></div>' +
        '<div class="modal-foot"><button type="button" class="btn" data-confirm-cancel>Cancel</button><button type="button" class="btn btn-primary" data-confirm-ok>Continue</button></div>' +
        '</div>';
      $('.confirm-message', confirmModal).textContent = message;
      document.body.appendChild(confirmModal);
      var previous = document.activeElement;
      document.body.style.overflow = 'hidden';
      var cancel = $('[data-confirm-cancel]', confirmModal), ok = $('[data-confirm-ok]', confirmModal);
      function finish(value) {
        confirmModal.classList.add('closing');
        setTimeout(function () { if (confirmModal) confirmModal.remove(); confirmModal = null; }, 190);
        document.body.style.overflow = '';
        if (previous && previous.focus) previous.focus();
        resolve(value);
      }
      cancel.addEventListener('click', function () { finish(false); });
      ok.addEventListener('click', function () { finish(true); });
      confirmModal.addEventListener('click', function (e) { if (e.target === confirmModal) finish(false); });
      confirmModal.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') finish(false);
        if (e.key === 'Tab' && e.shiftKey && document.activeElement === cancel) { e.preventDefault(); ok.focus(); }
        else if (e.key === 'Tab' && !e.shiftKey && document.activeElement === ok) { e.preventDefault(); cancel.focus(); }
      });
      ok.focus();
    });
  }

  /* ---------- dropdowns ---------- */
  function closeMenus(except) {
    $$('.menu.open').forEach(function (m) {
      if (m === except) return; m.classList.remove('open');
      var t = m.parentElement.querySelector('[data-dropdown]'); if (t) t.setAttribute('aria-expanded', 'false');
    });
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-dropdown]');
    if (t) {
      var menu = t.parentElement.querySelector('.menu'); var willOpen = !menu.classList.contains('open');
      closeMenus(); menu.classList.toggle('open', willOpen); t.setAttribute('aria-expanded', String(willOpen)); return;
    }
    if (!e.target.closest('.menu')) closeMenus();
  });

  /* ---------- sidebar (mobile) ---------- */
  var sidebar = $('#sidebar'), scrim = $('#scrim'), menuBtn = $('#menu-btn');
  function closeSidebar() { if (!sidebar) return; sidebar.classList.remove('open'); if (scrim) scrim.classList.remove('open'); if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false'); }
  if (menuBtn) menuBtn.addEventListener('click', function () {
    var o = sidebar.classList.toggle('open'); scrim.classList.toggle('open', o); menuBtn.setAttribute('aria-expanded', String(o));
  });
  if (scrim) scrim.addEventListener('click', closeSidebar);

  /* ---------- notifications ---------- */
  var csrf = (document.querySelector('meta[name=csrf-token]') || {}).content || '';
  var badge = $('#bell-badge');
  function setUnread(n) { if (!badge) return; badge.textContent = n > 99 ? '99+' : n; badge.hidden = n < 1; }
  var markAll = $('#mark-all-read');
  if (markAll) markAll.addEventListener('click', function () {
    fetch(markAll.dataset.url, { method: 'POST', headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function () { setUnread(0); $$('.notif-item.unread').forEach(function (i) { i.classList.remove('unread'); }); toast('All notifications marked as read.', 'success'); })
      .catch(function () { toast('Could not update notifications.', 'error'); });
  });
  if (badge && badge.dataset.poll) {
    setInterval(function () {
      if (document.hidden) return;
      fetch(badge.dataset.poll, { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d) setUnread(d.unread); }).catch(function () {});
    }, 60000);
  }

  /* ---------- forms ---------- */
  var customerName = $('#id_customer_name');
  var customerContact = $('#id_customer_contact');
  if (customerName) {
    customerName.addEventListener('input', function () {
      customerName.value = Array.from(customerName.value).filter(function (character) {
        return character === ' ' || /^\p{L}$/u.test(character);
      }).join('');
    });
  }
  if (customerContact) {
    customerContact.addEventListener('input', function () {
      customerContact.value = customerContact.value.replace(/[^0-9]/g, '').slice(0, 10);
    });
  }
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (f.hasAttribute('data-confirm') && !f.dataset.confirmed) {
      e.preventDefault();
      askConfirmation(f.getAttribute('data-confirm'), f.getAttribute('data-confirm-title') || 'Confirm this action', f.getAttribute('data-confirm-tone') || 'warning')
        .then(function (confirmed) {
          if (!confirmed) return;
          f.dataset.confirmed = 'true';
          if (f.requestSubmit) f.requestSubmit();
          else f.submit();
        });
      return;
    }
    var btns = $$('button[type=submit]', f);
    setTimeout(function () { btns.forEach(function (b) { b.disabled = true; }); }, 0); // prevent double submits
  });
  window.addEventListener('pageshow', function () { $$('button[type=submit]').forEach(function (b) { b.disabled = false; }); });
  $$('input[type=file][data-filelist]').forEach(function (inp) {
    var out = document.getElementById(inp.getAttribute('data-filelist'));
    inp.addEventListener('change', function () {
      if (!out) return; out.textContent = '';
      Array.prototype.forEach.call(inp.files, function (f) {
        var li = document.createElement('div'); li.className = 'small muted';
        li.textContent = f.name + ' (' + (f.size / 1024).toFixed(0) + ' KB)'; out.appendChild(li);
      });
    });
  });

  /* ---------- page transitions ---------- */
  var pageTransition = document.createElement('div');
  pageTransition.className = 'page-transition';
  pageTransition.innerHTML = '<span class="page-spinner" aria-hidden="true"></span>';
  pageTransition.setAttribute('aria-hidden', 'true');
  document.body.appendChild(pageTransition);
  requestAnimationFrame(function () { document.body.classList.add('page-ready'); });
  document.addEventListener('click', function (e) {
    var downloadLink = e.target.closest('a[data-download]');
    if (!downloadLink || e.defaultPrevented) return;
    e.preventDefault();
    if (downloadLink.getAttribute('aria-busy') === 'true') return;
    downloadLink.setAttribute('aria-busy', 'true');
    downloadLink.setAttribute('aria-disabled', 'true');
    pageTransition.classList.add('visible');
    fetch(downloadLink.href, { credentials: 'same-origin' })
      .then(function (response) {
        if (!response.ok) throw new Error('The PDF could not be generated.');
        return response.blob();
      })
      .then(function (blob) {
        var objectUrl = URL.createObjectURL(blob);
        var saveLink = document.createElement('a');
        saveLink.href = objectUrl;
        saveLink.download = 'dartalink-request-report.pdf';
        document.body.appendChild(saveLink);
        saveLink.click();
        saveLink.remove();
        setTimeout(function () { URL.revokeObjectURL(objectUrl); }, 1000);
      })
      .catch(function (error) {
        toast(error.message, 'error');
      })
      .finally(function () {
        pageTransition.classList.remove('visible');
        downloadLink.removeAttribute('aria-busy');
        downloadLink.removeAttribute('aria-disabled');
      });
  });
  document.addEventListener('click', function (e) {
    var link = e.target.closest('a[href]');
    if (!link || link.target === '_blank' || link.hasAttribute('download') || link.hasAttribute('data-download') || link.getAttribute('href').charAt(0) === '#' || e.defaultPrevented) return;
    var url = new URL(link.href, window.location.href);
    if (url.origin !== window.location.origin || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    pageTransition.classList.add('visible');
  });
  window.addEventListener('pageshow', function () { pageTransition.classList.remove('visible'); document.body.classList.add('page-ready'); });
  document.addEventListener('submit', function (e) {
    if (!e.defaultPrevented && !e.target.hasAttribute('data-confirm')) pageTransition.classList.add('visible');
  });
})();
