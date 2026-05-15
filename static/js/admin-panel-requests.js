(function () {
    'use strict';

    var escHandler = null;

    function destroy() {
        if (escHandler) {
            document.removeEventListener('keydown', escHandler);
            escHandler = null;
        }
    }

    function init() {
        destroy();

        var backdrop = document.getElementById('reject-modal-backdrop');
        var form = document.getElementById('reject-form');
        var reasonEl = document.getElementById('reject-reason');
        var confirmBtn = document.getElementById('reject-confirm');
        var subtitleEl = document.getElementById('reject-modal-subtitle');

        if (!backdrop || !form || !reasonEl) return;

        function syncConfirm() {
            if (confirmBtn) {
                confirmBtn.disabled = !reasonEl.value.trim();
            }
        }

        function openModal(actionUrl, subtitle) {
            form.action = actionUrl;
            reasonEl.value = '';
            if (subtitleEl) subtitleEl.textContent = subtitle || '';
            syncConfirm();
            backdrop.classList.add('is-open');
            backdrop.setAttribute('aria-hidden', 'false');
            reasonEl.focus();
        }

        function closeModal() {
            backdrop.classList.remove('is-open');
            backdrop.setAttribute('aria-hidden', 'true');
        }

        document.querySelectorAll('[data-reject-url]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                openModal(
                    btn.getAttribute('data-reject-url'),
                    btn.getAttribute('data-reject-subtitle') || ''
                );
            });
        });

        document.querySelectorAll('[data-reject-close]').forEach(function (el) {
            el.addEventListener('click', closeModal);
        });

        backdrop.addEventListener('mousedown', function (e) {
            if (e.target === backdrop) closeModal();
        });

        reasonEl.addEventListener('input', syncConfirm);

        document.querySelectorAll('[data-reject-preset]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                reasonEl.value = btn.getAttribute('data-reject-preset') || '';
                syncConfirm();
            });
        });

        escHandler = function (e) {
            if (e.key === 'Escape' && backdrop.classList.contains('is-open')) {
                closeModal();
            }
        };
        document.addEventListener('keydown', escHandler);

        form.addEventListener('submit', function (e) {
            if (!window.AdminPanelAjax) return;
            e.preventDefault();
            e.stopPropagation();
            var body = new FormData(form);
            var btn = confirmBtn;
            if (btn) btn.disabled = true;
            window.AdminPanelAjax.fetchPost(form.action, body, { accept: 'application/json' })
                .then(function (data) {
                    closeModal();
                    if (data.message) {
                        window.AdminPanelAjax.showMessage(data.message, data.level || 'warning');
                    }
                    if (data.reload) {
                        var root = document.querySelector('[data-ap-partial-root]');
                        if (root) {
                            return window.AdminPanelAjax.fetchHtml(
                                window.AdminPanelAjax.partialListUrl(data.reload)
                            ).then(function (html) {
                                root.innerHTML = html;
                                window.AdminPanelAjax.pushUrl(data.reload, true);
                                document.dispatchEvent(
                                    new CustomEvent('ap:partial:load', {
                                        detail: { url: data.reload, root: root },
                                    })
                                );
                                if (window.AdminPanel) window.AdminPanel.runInit('requests');
                            });
                        }
                    }
                })
                .catch(function (err) {
                    var msg = (err && err.message) || 'Rejection failed.';
                    window.AdminPanelAjax.showMessage(msg, 'error');
                })
                .finally(function () {
                    if (btn) btn.disabled = !reasonEl.value.trim();
                });
        });
    }

    document.addEventListener('ap:partial:load', function () {
        if (window.AdminPanel) window.AdminPanel.runInit('requests');
    });

    if (window.AdminPanel) {
        window.AdminPanel.register('requests', { init: init, destroy: destroy });
    } else {
        init();
    }
})();
