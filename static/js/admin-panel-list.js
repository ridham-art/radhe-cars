(function () {
    'use strict';

    var clickHandler = null;
    var submitHandler = null;
    var inflight = null;

    function normPath(pathname) {
        var p = pathname || '/';
        if (p.length > 1 && p.charAt(p.length - 1) === '/') {
            p = p.slice(0, -1);
        }
        return p;
    }

    function getRoot() {
        return document.querySelector('[data-ap-partial-root]');
    }

    function loadPartial(href, opts) {
        opts = opts || {};
        var root = getRoot();
        if (!root || !window.AdminPanelAjax) return Promise.resolve();

        if (inflight) inflight.abort();
        inflight = new AbortController();

        root.classList.add('is-loading');
        var fetchUrl = window.AdminPanelAjax.partialListUrl(href);

        return window.AdminPanelAjax
            .fetchHtml(fetchUrl, { signal: inflight.signal })
            .then(function (html) {
                root.innerHTML = html;
                if (!opts.replace) {
                    window.AdminPanelAjax.pushUrl(href);
                }
                document.dispatchEvent(
                    new CustomEvent('ap:partial:load', { detail: { url: href, root: root } })
                );
            })
            .catch(function (err) {
                if (err && err.name === 'AbortError') return;
                window.location.href = href;
            })
            .finally(function () {
                root.classList.remove('is-loading');
                inflight = null;
            });
    }

    function onClick(e) {
        var root = getRoot();
        if (!root) return;

        var a = e.target.closest('a[href]');
        if (!a || !root.contains(a) || a.hasAttribute('data-ap-full')) return;

        var u = new URL(a.href, window.location.origin);
        if (normPath(u.pathname) !== normPath(window.location.pathname)) return;

        if (u.pathname.indexOf('/csv/export') !== -1) return;
        if (u.pathname.indexOf('/cars/export/') !== -1) return;

        e.preventDefault();
        e.stopImmediatePropagation();
        loadPartial(u.href);
    }

    function onSubmit(e) {
        var root = getRoot();
        if (!root) return;

        var form = e.target;
        if (!form || form.method.toLowerCase() !== 'get') return;
        if (!root.contains(form)) return;
        if (form.hasAttribute('data-ap-full')) return;

        e.preventDefault();
        e.stopPropagation();

        var url = new URL(form.getAttribute('action') || window.location.href, window.location.origin);
        var fd = new FormData(form);
        fd.forEach(function (val, key) {
            if (val !== null && val !== '') url.searchParams.set(key, val);
        });
        loadPartial(url.href);
    }

    function init() {
        if (!getRoot()) return;

        if (!clickHandler) {
            clickHandler = onClick;
            document.addEventListener('click', clickHandler, true);
        }
        if (!submitHandler) {
            submitHandler = onSubmit;
            document.addEventListener('submit', submitHandler, true);
        }
    }

    function destroy() {}

    function register(keys) {
        if (!window.AdminPanel) return;
        keys.forEach(function (key) {
            window.AdminPanel.register(key, { init: init, destroy: destroy });
        });
    }

    register(['inventory', 'customers', 'wishlists', 'inquiries', 'requests', 'vehicle_master']);
})();
