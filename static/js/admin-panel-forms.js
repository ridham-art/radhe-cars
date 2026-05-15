(function () {
    'use strict';

    function isAjaxForm(form) {
        if (!form || form.method.toLowerCase() !== 'post') return false;
        if (form.id === 'ap-logout-form' || form.id === 'reject-form') return false;
        if (form.hasAttribute('data-ap-full')) return false;
        var action = form.getAttribute('action') || window.location.href;
        try {
            var u = new URL(action, window.location.origin);
            return u.pathname.indexOf('/admin-panel/') !== -1;
        } catch (_e) {
            return false;
        }
    }

    function reloadListPartial(url) {
        if (!url || !window.AdminPanelAjax) return Promise.resolve();
        var root = document.querySelector('[data-ap-partial-root]');
        if (!root) {
            if (window.AdminPanel && window.AdminPanel.navigateTo) {
                window.AdminPanel.navigateTo(url);
            } else {
                window.location.href = url;
            }
            return Promise.resolve();
        }
        root.classList.add('is-loading');
        return window.AdminPanelAjax.fetchHtml(window.AdminPanelAjax.partialListUrl(url))
            .then(function (html) {
                root.innerHTML = html;
                window.AdminPanelAjax.pushUrl(url, true);
                document.dispatchEvent(
                    new CustomEvent('ap:partial:load', { detail: { url: url, root: root } })
                );
                if (window.AdminPanel) {
                    var key = document.body.getAttribute('data-ap-page-key');
                    if (key) window.AdminPanel.runInit(key);
                }
            })
            .finally(function () {
                root.classList.remove('is-loading');
            });
    }

    function pollNavBadges() {
        fetch('/admin-panel/api/inquiries/unread-count/', {
            credentials: 'same-origin',
            headers: { Accept: 'application/json' },
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (d) {
                var n = (typeof d.inquiries === 'number' ? d.inquiries : d.count) || 0;
                var el = document.getElementById('nav-inquiry-badge');
                if (el) {
                    el.textContent = n;
                    el.classList.toggle('is-hidden', n === 0);
                }
                var s = (typeof d.sell_inquiries === 'number' ? d.sell_inquiries : 0) || 0;
                var sellEl = document.getElementById('nav-sell-badge');
                if (sellEl) {
                    sellEl.textContent = s;
                    sellEl.classList.toggle('is-hidden', s === 0);
                }
            })
            .catch(function () {});
    }

    function handleAjaxResponse(data) {
        if (data && data.ok === false) {
            var err = new Error(data.message || 'Request failed');
            err.payload = data;
            throw err;
        }
        if (data.message && window.AdminPanelAjax) {
            window.AdminPanelAjax.showMessage(data.message, data.level || 'success');
        }
        if (data.reload) {
            return reloadListPartial(data.reload);
        }
        if (data.redirect && window.AdminPanel && window.AdminPanel.navigateTo) {
            window.AdminPanel.navigateTo(data.redirect);
            return Promise.resolve();
        }
        return Promise.resolve();
    }

    function onSubmit(e) {
        var form = e.target;
        if (!isAjaxForm(form)) return;

        var confirmMsg = form.getAttribute('data-confirm');
        if (!confirmMsg) {
            var submitBtn = e.submitter;
            if (submitBtn) confirmMsg = submitBtn.getAttribute('data-confirm');
        }
        if (confirmMsg && !window.confirm(confirmMsg)) {
            e.preventDefault();
            e.stopPropagation();
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        var action = form.getAttribute('action') || window.location.href;
        var body = new FormData(form);
        var submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        window.AdminPanelAjax.fetchPost(action, body, { accept: 'application/json' })
            .then(handleAjaxResponse)
            .then(function () {
                pollNavBadges();
                document.dispatchEvent(new CustomEvent('ap:form:success'));
            })
            .catch(function (err) {
                var msg = (err && err.message) || 'Request failed. Please try again.';
                if (window.AdminPanelAjax) {
                    window.AdminPanelAjax.showMessage(msg, 'error');
                }
            })
            .finally(function () {
                if (submitBtn) submitBtn.disabled = false;
            });
    }

    function init() {
        document.addEventListener('submit', onSubmit, true);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
