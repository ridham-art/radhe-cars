(function () {
    'use strict';

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

    document.addEventListener('ap:page:load', function (e) {
        if (e.detail && e.detail.pageKey === 'inquiry_detail') {
            pollNavBadges();
        }
    });
})();
