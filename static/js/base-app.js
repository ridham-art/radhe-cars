/**
 * Site-wide: mobile menu, share buttons, clipboard fallback.
 * Loaded with defer from base.html (non-blocking).
 */
(function () {
    function initMobileMenu() {
        var menu = document.getElementById('mobile-menu');
        var panel = document.getElementById('mobile-menu-panel');
        var btn = document.getElementById('mobile-menu-btn');
        var closeBtn = document.getElementById('mobile-menu-close');
        var backdrop = document.getElementById('mobile-menu-backdrop');
        if (!menu) return;
        function openMenu() {
            menu.classList.remove('hidden');
            if (panel) panel.classList.remove('translate-x-full');
            document.body.style.overflow = 'hidden';
        }
        function closeMenu() {
            menu.classList.add('hidden');
            if (panel) panel.classList.add('translate-x-full');
            document.body.style.overflow = '';
        }
        if (btn) btn.addEventListener('click', openMenu);
        if (closeBtn) closeBtn.addEventListener('click', closeMenu);
        if (backdrop) backdrop.addEventListener('click', closeMenu);
    }
    function copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;top:0;left:0;width:2px;height:2px;padding:0;border:none;outline:none;opacity:0;z-index:-1;';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, text.length);
        try {
            var ok = document.execCommand('copy');
            document.body.removeChild(ta);
            return ok ? Promise.resolve() : Promise.reject();
        } catch (e) {
            document.body.removeChild(ta);
            return Promise.reject(e);
        }
    }
    window.doShare = function (btn) {
        if (!btn) return;
        var path = btn.dataset.shareUrl || btn.getAttribute('data-share-url');
        var title = btn.dataset.shareTitle || btn.getAttribute('data-share-title') || 'Check out this car';
        var url = path ? (path.startsWith('http') ? path : window.location.origin + path) : window.location.href;
        var orig = btn.innerHTML;
        function done(msg) {
            try {
                btn.innerHTML = msg;
            } catch (e) {}
            setTimeout(function () {
                try {
                    btn.innerHTML = orig;
                } catch (e) {}
            }, 2000);
        }
        function showFallback() {
            var existing = document.getElementById('share-fallback');
            if (existing) existing.remove();
            var box = document.createElement('div');
            box.id = 'share-fallback';
            var safeUrl = String(url)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
            box.innerHTML =
                '<div class="share-box"><p class="font-semibold text-gray-900">Share link</p><div class="share-url">' +
                safeUrl +
                '</div><p class="text-sm text-gray-500 mb-2">Tap Copy to copy the link, then paste it in WhatsApp or any app.</p><button type="button" class="share-copy">Copy Link</button><button type="button" class="share-close">Close</button></div>';
            box.onclick = function (e) {
                if (e.target === box || e.target.classList.contains('share-close')) box.remove();
            };
            var copyBtn = box.querySelector('.share-copy');
            copyBtn.onclick = function (e) {
                e.stopPropagation();
                copyToClipboard(url)
                    .then(function () {
                        copyBtn.textContent = 'Copied!';
                        copyBtn.style.background = '#22c55e';
                        setTimeout(function () {
                            copyBtn.textContent = 'Copy Link';
                            copyBtn.style.background = '';
                        }, 1500);
                    })
                    .catch(function () {
                        copyBtn.textContent = 'Select & copy manually';
                    });
            };
            copyBtn.ontouchend = function (e) {
                e.preventDefault();
                e.stopPropagation();
                copyToClipboard(url)
                    .then(function () {
                        copyBtn.textContent = 'Copied!';
                        copyBtn.style.background = '#22c55e';
                        setTimeout(function () {
                            copyBtn.textContent = 'Copy Link';
                            copyBtn.style.background = '';
                        }, 1500);
                    })
                    .catch(function () {
                        copyBtn.textContent = 'Select & copy manually';
                    });
            };
            document.body.appendChild(box);
        }
        if (navigator.share) {
            navigator
                .share({ title: title, url: url, text: title })
                .then(function () {
                    done('Shared!');
                })
                .catch(function (err) {
                    if (err && err.name === 'AbortError') return;
                    showFallback();
                });
        } else {
            copyToClipboard(url)
                .then(function () {
                    done('Copied!');
                })
                .catch(showFallback);
        }
    };
    var lastShareTap = 0;
    function handleShare(e) {
        var el = e.target;
        if (!el) return;
        if (el.nodeType === 3) el = el.parentElement;
        var btn =
            (el && el.closest ? el.closest('.share-btn') : null) ||
            (el && el.classList && el.classList.contains('share-btn') ? el : null);
        if (!btn) return;
        e.stopPropagation();
        e.preventDefault();
        if (Date.now() - lastShareTap < 500) return;
        lastShareTap = Date.now();
        window.doShare(btn);
    }
    function initShare() {
        document.addEventListener('click', handleShare, true);
        document.addEventListener('touchend', handleShare, { capture: true, passive: false });
    }
    function initBaseApp() {
        initMobileMenu();
        initShare();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBaseApp);
    } else {
        initBaseApp();
    }
})();
