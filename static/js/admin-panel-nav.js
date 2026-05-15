(function () {
    'use strict';

    var CFG = window.AP_NAV_CONFIG || {
        staticPrefix: '/static/',
        adminPrefix: '/admin-panel/',
    };

    var PAGE_ASSETS = {
        dashboard: {
            css: ['css/admin-panel-dashboard.css'],
            scripts: [
                {
                    url: 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
                    globalKey: 'Chart',
                },
                { url: 'js/admin-panel-dashboard.js' },
            ],
        },
        inventory: {
            css: ['css/admin-panel-inventory.css'],
            scripts: [],
        },
        car_form: {
            css: ['css/admin-panel-dashboard.css', 'css/admin-panel-car-form.css'],
            scripts: [{ url: 'js/admin-panel-car-form.js' }],
        },
        requests: {
            css: [
                'css/admin-panel-inventory.css',
                'css/admin-panel-dashboard.css',
                'css/admin-panel-requests.css',
            ],
            scripts: [{ url: 'js/admin-panel-requests.js' }],
        },
        vehicle_master: {
            css: ['css/admin-panel-dashboard.css', 'css/admin-panel-vehicle-master.css'],
            scripts: [{ url: 'js/admin-panel-vehicle-master.js' }],
        },
        lists: {
            css: [
                'css/admin-panel-inventory.css',
                'css/admin-panel-dashboard.css',
                'css/admin-panel-lists.css',
            ],
            scripts: [],
        },
        csv: {
            css: [
                'css/admin-panel-car-form.css',
                'css/admin-panel-dashboard.css',
                'css/admin-panel-lists.css',
            ],
            scripts: [],
        },
    };

    var mainEl = document.querySelector('main.page');
    var cssRoot = document.getElementById('ap-dynamic-css');
    var curPageKey = null;
    var inflightAbort = null;
    var loadedScripts = new Object();

    var AP = window.AdminPanel || {};
    AP.pages = AP.pages || {};
    AP.register =
        AP.register ||
        function (key, handlers) {
            AP.pages[key] = handlers;
        };
    AP.runDestroy =
        AP.runDestroy ||
        function (key) {
            var h = key && AP.pages[key];
            if (h && typeof h.destroy === 'function') h.destroy();
        };
    AP.runInit =
        AP.runInit ||
        function (key) {
            var h = key && AP.pages[key];
            if (h && typeof h.init === 'function') h.init();
        };
    window.AdminPanel = AP;

    function staticUrl(path) {
        if (!path) return path;
        if (/^https?:\/\//i.test(path) || path.indexOf('//') === 0) return path;
        var prefix = CFG.staticPrefix || '/static/';
        if (prefix.charAt(prefix.length - 1) !== '/') prefix += '/';
        return prefix + path.replace(/^\//, '');
    }

    function adminPrefix() {
        var p = CFG.adminPrefix || '/admin-panel/';
        return p.charAt(p.length - 1) === '/' ? p : p + '/';
    }

    function normalizePath(pathname) {
        var p = pathname || '/';
        if (p.length > 1 && p.charAt(p.length - 1) === '/') {
            p = p.slice(0, -1);
        }
        return p;
    }

    function adminRest(pathname) {
        var prefix = normalizePath(adminPrefix().replace(/\/$/, ''));
        var norm = normalizePath(pathname);
        if (norm !== prefix && norm.indexOf(prefix + '/') !== 0) return null;
        if (norm === prefix) return '';
        return norm.slice(prefix.length + 1);
    }

    function resolvePageKey(pathname) {
        var rest = adminRest(pathname);
        if (rest === null) return null;
        if (!rest || rest === '') return 'dashboard';
        if (rest === 'dashboard-preview' || rest === 'ui-preview') return 'dashboard';
        if (/^cars\/add$/.test(rest) || rest === 'cars-add-preview') return 'car_form';
        if (/^cars\/\d+\/edit$/.test(rest) || /^cars\/\d+\/edit-preview$/.test(rest)) return 'car_form';
        if (rest === 'cars' || rest === 'cars-preview') return 'inventory';
        if (rest === 'sell-car-inquiries' || rest === 'listing-requests-preview') return 'requests';
        if (rest === 'vehicle-master' || rest === 'vehicle-master-preview') return 'vehicle_master';
        if (rest.indexOf('vehicle-master/') === 0) return 'vehicle_master';
        if (rest === 'customers' || rest === 'customers-preview') return 'lists';
        if (rest === 'wishlists' || rest === 'wishlists-preview') return 'lists';
        if (rest === 'inquiries' || rest === 'inquiries-preview') return 'lists';
        if (/^inquiries\/\d+$/.test(rest) || /^inquiries-preview\/\d+$/.test(rest)) return 'lists';
        if (rest.indexOf('csv/') === 0) return 'csv';
        return null;
    }

    function isAdminUrl(url) {
        try {
            var u = new URL(url, window.location.origin);
            if (u.origin !== window.location.origin) return false;
            return resolvePageKey(u.pathname) !== null;
        } catch (_e) {
            return false;
        }
    }

    function shouldInterceptLink(a, e) {
        if (!a || !a.href) return false;
        if (a.hasAttribute('data-ap-full')) return false;
        if (a.target && a.target !== '_self') return false;
        if (a.hasAttribute('download')) return false;
        if (e && (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)) {
            return false;
        }
        var u = new URL(a.href, window.location.origin);
        if (u.pathname.indexOf('/csv/export') !== -1) return false;
        if (u.pathname.indexOf('/cars/export/') !== -1) return false;
        return isAdminUrl(a.href);
    }

    function markLoadedScripts() {
        document.querySelectorAll('script[src]').forEach(function (s) {
            loadedScripts[s.src] = true;
        });
    }

    function loadStylesheet(href) {
        if (loadedScripts[href]) return Promise.resolve();
        return new Promise(function (resolve, reject) {
            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;
            link.setAttribute('data-ap-dynamic', '1');
            link.onload = function () {
                loadedScripts[href] = true;
                resolve();
            };
            link.onerror = reject;
            (cssRoot || document.head).appendChild(link);
        });
    }

    function loadScript(desc) {
        var href = staticUrl(desc.url);
        if (desc.globalKey && window[desc.globalKey]) {
            return Promise.resolve();
        }
        if (loadedScripts[href]) {
            return Promise.resolve();
        }
        return new Promise(function (resolve, reject) {
            var s = document.createElement('script');
            s.src = href;
            s.async = false;
            s.setAttribute('data-ap-dynamic', '1');
            s.onload = function () {
                loadedScripts[href] = true;
                resolve();
            };
            s.onerror = reject;
            document.body.appendChild(s);
        });
    }

    function clearDynamicAssets() {
        document.querySelectorAll('link[data-ap-dynamic]').forEach(function (el) {
            delete loadedScripts[el.href];
            el.parentNode.removeChild(el);
        });
        document.querySelectorAll('script[data-ap-dynamic]').forEach(function (el) {
            delete loadedScripts[el.src];
            el.parentNode.removeChild(el);
        });
        document.querySelectorAll('link[rel="stylesheet"]').forEach(function (link) {
            var href = link.href || '';
            if (
                href.indexOf('admin-panel-') !== -1 &&
                href.indexOf('admin-panel-shell') === -1 &&
                !link.hasAttribute('data-ap-dynamic')
            ) {
                delete loadedScripts[href];
                link.parentNode.removeChild(link);
            }
        });
    }

    function applyPageAssets(pageKey) {
        var spec = PAGE_ASSETS[pageKey];
        if (!spec) return Promise.resolve();
        var cssJobs = (spec.css || []).map(function (path) {
            return loadStylesheet(staticUrl(path));
        });
        return Promise.all(cssJobs).then(function () {
            var chain = Promise.resolve();
            (spec.scripts || []).forEach(function (desc) {
                chain = chain.then(function () {
                    return loadScript(desc);
                });
            });
            return chain;
        });
    }

    function parsePage(html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var main = doc.querySelector('main.page');
        if (!main) return null;
        var headingEl = doc.querySelector('.topbar .crumbs .cur');
        var title = doc.querySelector('title');
        var messages = doc.querySelector('.ap-messages');
        return {
            mainHtml: main.innerHTML,
            heading: headingEl ? headingEl.textContent.trim() : '',
            title: title ? title.textContent.trim() : '',
            messagesHtml: messages ? messages.innerHTML : '',
        };
    }

    function setHeading(text) {
        var el = document.querySelector('.topbar .crumbs .cur');
        if (el && text) el.textContent = text;
    }

    function setMessages(html) {
        var host = document.querySelector('.main');
        if (!host) return;
        var box = host.querySelector('.ap-messages');
        if (!html) {
            if (box) box.remove();
            return;
        }
        if (!box) {
            box = document.createElement('div');
            box.className = 'ap-messages';
            box.id = 'ap-messages';
            var page = host.querySelector('main.page');
            if (page) host.insertBefore(box, page);
            else host.appendChild(box);
        }
        box.innerHTML = html;
    }

    function syncActiveNav(pathname) {
        var norm = normalizePath(new URL(pathname, window.location.origin).pathname);
        var pageKey = resolvePageKey(norm);
        document.querySelectorAll('#ap-sidebar nav a.nav-item[href]').forEach(function (a) {
            var hrefPath = normalizePath(new URL(a.href, window.location.origin).pathname);
            var linkKey = resolvePageKey(hrefPath);
            var active = hrefPath === norm;
            if (!active && linkKey && pageKey && linkKey === pageKey) {
                active = true;
            }
            if (!active && linkKey === 'inventory' && pageKey === 'car_form') {
                active = true;
            }
            a.classList.toggle('active', active);
        });
    }

    function setLoading(on) {
        if (!mainEl) return;
        mainEl.classList.toggle('is-loading', on);
        mainEl.setAttribute('aria-busy', on ? 'true' : 'false');
    }

    function dispatch(name, detail) {
        document.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    }

    function navigateTo(url, opts) {
        opts = opts || {};
        var absolute = new URL(url, window.location.origin);
        var pageKey = resolvePageKey(absolute.pathname);
        if (!pageKey || !mainEl) {
            window.location.href = absolute.href;
            return Promise.resolve();
        }

        if (
            !opts.force &&
            normalizePath(window.location.pathname) === normalizePath(absolute.pathname) &&
            window.location.search === absolute.search
        ) {
            return Promise.resolve();
        }

        if (inflightAbort) inflightAbort.abort();
        inflightAbort = new AbortController();
        var signal = inflightAbort.signal;

        var prevKey = curPageKey;
        dispatch('ap:page:unload', { pageKey: prevKey, url: absolute.href });
        window.AdminPanel.runDestroy(prevKey);
        setLoading(true);

        return fetch(absolute.pathname + absolute.search, {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                Accept: 'text/html',
                'X-Requested-With': 'XMLHttpRequest',
            },
            signal: signal,
        })
            .then(function (r) {
                if (!r.ok) throw new Error('fetch failed');
                return r.text();
            })
            .then(function (html) {
                var parsed = parsePage(html);
                if (!parsed) throw new Error('no main');

                clearDynamicAssets();
                return applyPageAssets(pageKey).then(function () {
                    mainEl.innerHTML = parsed.mainHtml;
                    if (parsed.title) document.title = parsed.title;
                    if (parsed.heading) setHeading(parsed.heading);
                    setMessages(parsed.messagesHtml);

                    curPageKey = pageKey;
                    if (!opts.replace) {
                        history.pushState({ apNav: true, pageKey: pageKey }, '', absolute.href);
                    }
                    syncActiveNav(absolute.pathname);
                    window.AdminPanel.runInit(pageKey);
                    dispatch('ap:page:load', { pageKey: pageKey, url: absolute.href });
                });
            })
            .catch(function (err) {
                if (err && err.name === 'AbortError') return;
                window.location.href = absolute.href;
            })
            .finally(function () {
                setLoading(false);
                inflightAbort = null;
            });
    }

    function onDocumentClick(e) {
        var a = e.target.closest('a[href]');
        if (!shouldInterceptLink(a, e)) return;
        e.preventDefault();
        navigateTo(a.href);
    }

    function onFormSubmit(e) {
        var form = e.target;
        if (!form || form.method.toLowerCase() !== 'get') return;
        if (form.hasAttribute('data-ap-full')) return;
        var action = form.getAttribute('action') || window.location.href;
        if (!isAdminUrl(action)) return;
        e.preventDefault();
        var url = new URL(action, window.location.origin);
        var fd = new FormData(form);
        fd.forEach(function (val, key) {
            if (val) url.searchParams.set(key, val);
        });
        navigateTo(url.href);
    }

    function onPopState() {
        navigateTo(window.location.href, { replace: true, force: true });
    }

    function bootstrap() {
        mainEl = document.querySelector('main.page');
        if (!mainEl) return;

        markLoadedScripts();
        curPageKey = resolvePageKey(window.location.pathname);

        document.addEventListener('click', onDocumentClick, true);
        document.addEventListener('submit', onFormSubmit, true);
        window.addEventListener('popstate', onPopState);

        if (curPageKey) {
            window.AdminPanel.runInit(curPageKey);
            dispatch('ap:page:load', {
                pageKey: curPageKey,
                url: window.location.href,
                initial: true,
            });
        }

        if (!history.state || !history.state.apNav) {
            history.replaceState(
                { apNav: true, pageKey: curPageKey },
                '',
                window.location.href
            );
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootstrap);
    } else {
        bootstrap();
    }

    window.AdminPanel.navigateTo = navigateTo;
})();
