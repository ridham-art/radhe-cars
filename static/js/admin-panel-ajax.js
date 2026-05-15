(function () {
    'use strict';

    function getCsrfToken() {
        var el = document.querySelector('[name=csrfmiddlewaretoken]');
        if (el && el.value) return el.value;
        var m = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[2]) : '';
    }

    function fetchHtml(url, opts) {
        opts = opts || {};
        return fetch(url, {
            method: opts.method || 'GET',
            credentials: 'same-origin',
            headers: Object.assign(
                {
                    Accept: 'text/html',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                opts.headers || {}
            ),
            body: opts.body || null,
            signal: opts.signal,
        }).then(function (r) {
            if (!r.ok) throw new Error('request failed');
            return r.text();
        });
    }

    function fetchPost(url, body, opts) {
        opts = opts || {};
        var headers = {
            Accept: opts.accept || 'application/json, text/html;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
        };
        if (opts.headers) {
            Object.assign(headers, opts.headers);
        }
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: headers,
            body: body,
            signal: opts.signal,
        }).then(function (r) {
            var ct = r.headers.get('content-type') || '';
            if (ct.indexOf('application/json') !== -1) {
                return r.json().then(function (data) {
                    if (!r.ok) throw data;
                    return data;
                });
            }
            if (!r.ok) throw new Error('request failed');
            return r.text();
        });
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

    function showMessage(text, level) {
        if (!text) return;
        var cls = 'info';
        if (level === 'success') cls = 'success';
        else if (level === 'error') cls = 'error';
        else if (level === 'warning') cls = 'warning';
        setMessages(
            '<div class="ap-message ' +
                cls +
                '">' +
                String(text)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;') +
                '</div>'
        );
    }

    function pushUrl(url, replace) {
        if (replace) {
            history.replaceState({ apNav: true, apPartial: true }, '', url);
        } else {
            history.pushState({ apNav: true, apPartial: true }, '', url);
        }
    }

    function partialListUrl(href) {
        var u = new URL(href, window.location.origin);
        u.searchParams.set('partial', 'list');
        return u.pathname + u.search;
    }

    window.AdminPanelAjax = {
        getCsrfToken: getCsrfToken,
        fetchHtml: fetchHtml,
        fetchPost: fetchPost,
        setMessages: setMessages,
        showMessage: showMessage,
        pushUrl: pushUrl,
        partialListUrl: partialListUrl,
    };
})();
