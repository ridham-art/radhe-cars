/**
 * Home page: body-type filter, featured/recent car rows, hero carousel.
 * Requires #home-root with data-api-cars URL (set in home.html).
 */
(function () {
    function getApiUrl() {
        var root = document.getElementById('home-root');
        return (root && root.dataset.apiCars) || '';
    }

    function initHomePage() {
        var state = {};
        var apiHomeCars = getApiUrl();

        function isMobile() {
            return window.innerWidth < 768;
        }

        function setBodyTypeActive(btn) {
            var btns = document.querySelectorAll('.body-type-btn');
            btns.forEach(function (b) {
                if (b === btn) {
                    b.classList.remove('bg-white', 'border', 'border-gray-200', 'text-gray-600', 'hover:border-blue-200', 'hover:text-blue-600');
                    b.classList.add('bg-blue-600', 'text-white', 'border-0', 'hover:bg-blue-700', 'hover:text-white');
                    b.setAttribute('data-selected', 'true');
                } else {
                    b.classList.remove('bg-blue-600', 'text-white', 'border-0', 'hover:bg-blue-700', 'hover:text-white');
                    b.classList.add('bg-white', 'border', 'border-gray-200', 'text-gray-600', 'hover:border-blue-200', 'hover:text-blue-600');
                    b.removeAttribute('data-selected');
                }
            });
        }

        document.querySelectorAll('.body-type-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var bodyType = btn.getAttribute('data-body-type') || '';
                setBodyTypeActive(btn);
                var track = document.getElementById('recent-track');
                var loading = document.getElementById('recent-cars-loading');
                if (!track || !loading || !apiHomeCars) return;
                loading.classList.remove('hidden');
                fetch(apiHomeCars + '?body_type=' + encodeURIComponent(bodyType), {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                })
                    .then(function (r) {
                        return r.json();
                    })
                    .then(function (data) {
                        track.innerHTML = data.html || '';
                        loading.classList.add('hidden');
                        if (window.reinitRecentCarousel) window.reinitRecentCarousel();
                    })
                    .catch(function () {
                        loading.classList.add('hidden');
                    });
            });
        });

        function init(id) {
            var track = document.getElementById(id + '-track');
            if (!track) return;
            if (isMobile()) return;
            var card = track.children[0];
            if (!card) return;
            var gap = 24;
            var cardW = card.offsetWidth + gap;
            if (cardW <= 0) return;
            var visible = Math.max(1, Math.round(track.parentElement.offsetWidth / cardW));
            var origCount = track.children.length;

            if (!track.dataset.cloned) {
                var clones = [];
                for (var i = 0; i < visible; i++) {
                    clones.push(track.children[i % origCount].cloneNode(true));
                }
                for (var j = 0; j < clones.length; j++) {
                    track.appendChild(clones[j]);
                }
                track.dataset.cloned = 'true';
            }

            state[id] = {
                track: track,
                cardW: cardW,
                index: 0,
                origCount: origCount,
                visible: visible,
                moving: false,
            };
        }

        function moveTo(id, anim) {
            var s = state[id];
            var style = anim ? 'transform 1.2s cubic-bezier(0.4, 0, 0.2, 1)' : 'none';
            s.track.style.transition = style;
            s.track.style.transform = 'translateX(-' + s.index * s.cardW + 'px)';
        }

        function onEnd(id) {
            var s = state[id];
            s.moving = false;
            if (s.index >= s.origCount) {
                s.index = 0;
                moveTo(id, false);
            }
        }

        window.cardSlide = function (id, dir) {
            if (isMobile()) return;
            var s = state[id];
            if (!s || s.moving) return;
            s.moving = true;
            s.index += dir * s.visible;

            if (s.index < 0) {
                var lastPage = Math.floor((s.origCount - 1) / s.visible) * s.visible;
                s.index = lastPage;
                s.track.style.transition = 'none';
                s.track.style.transform = 'translateX(-' + (lastPage + s.origCount) * s.cardW + 'px)';
                s.track.offsetHeight;
                s.moving = false;
                moveTo(id, true);
                return;
            }

            if (s.index >= s.origCount) {
                s.index = 0;
            }

            moveTo(id, true);
        };

        function setupTransitionEnd(id) {
            var s = state[id];
            if (!s) return;
            s.track.addEventListener('transitionend', function () {
                onEnd(id);
            });
        }

        function addSwipe(id) {
            if (isMobile()) return;
            var s = state[id];
            if (!s) return;
            var container = s.track.parentElement;
            var startX = 0,
                startY = 0,
                dragging = false,
                moved = false;

            container.addEventListener(
                'touchstart',
                function (e) {
                    startX = e.touches[0].clientX;
                    startY = e.touches[0].clientY;
                    dragging = true;
                    moved = false;
                },
                { passive: true }
            );

            container.addEventListener(
                'touchmove',
                function (e) {
                    if (!dragging) return;
                    var dx = e.touches[0].clientX - startX;
                    var dy = e.touches[0].clientY - startY;
                    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) {
                        moved = true;
                        e.preventDefault();
                    }
                },
                { passive: false }
            );

            container.addEventListener(
                'touchend',
                function (e) {
                    if (!dragging) return;
                    dragging = false;
                    var dx = e.changedTouches[0].clientX - startX;
                    if (moved && Math.abs(dx) > 50) window.cardSlide(id, dx < 0 ? 1 : -1);
                },
                { passive: true }
            );
        }

        init('featured');
        init('recent');
        setupTransitionEnd('featured');
        setupTransitionEnd('recent');
        addSwipe('featured');
        addSwipe('recent');

        window.reinitRecentCarousel = function () {
            var track = document.getElementById('recent-track');
            if (track && track.dataset) delete track.dataset.cloned;
            if (state['recent']) delete state['recent'];
            init('recent');
            setupTransitionEnd('recent');
            addSwipe('recent');
        };

        var cardTimers = {};
        function startAutoScroll(id) {
            clearInterval(cardTimers[id]);
            cardTimers[id] = setInterval(function () {
                window.cardSlide(id, 1);
            }, 5000);
        }
        startAutoScroll('featured');
        startAutoScroll('recent');

        var origCardSlide = window.cardSlide;
        window.cardSlide = function (id, dir) {
            origCardSlide(id, dir);
            startAutoScroll(id);
        };

        window.addEventListener('resize', function () {
            init('featured');
            init('recent');
        });

        // Hero infinite carousel (do not early-return whole init if #hero-track missing)
        var track = document.getElementById('hero-track');
        if (track) {
        var dots = document.querySelectorAll('.hero-dot');
        var pos = 1,
            real = 0,
            total = 3,
            moving = false,
            timer;

        function move(p, anim) {
            track.style.transition = anim ? 'transform 700ms ease-in-out' : 'none';
            track.style.transform = 'translateX(-' + p * 100 + '%)';
        }

        track.addEventListener('transitionend', function () {
            moving = false;
            if (pos === 0) {
                pos = total;
                move(pos, false);
            } else if (pos === total + 1) {
                pos = 1;
                move(pos, false);
            }
        });

        function updateDots() {
            for (var i = 0; i < dots.length; i++) {
                var on = i === real;
                dots[i].style.opacity = on ? '1' : '0.5';
                dots[i].setAttribute('aria-selected', on ? 'true' : 'false');
                dots[i].setAttribute('tabindex', on ? '0' : '-1');
            }
        }

        window.heroSlide = function (dir) {
            if (moving) return;
            moving = true;
            pos += dir;
            real = ((pos - 1) % total + total) % total;
            updateDots();
            move(pos, true);
            resetTimer();
        };

        window.heroGoTo = function (i) {
            if (moving) return;
            moving = true;
            pos = i + 1;
            real = i;
            updateDots();
            move(pos, true);
            resetTimer();
        };

        function resetTimer() {
            clearInterval(timer);
            timer = setInterval(function () {
                window.heroSlide(1);
            }, 5000);
        }
        resetTimer();
        updateDots();

        var heroEl = track.parentElement;
        var hsx = 0,
            hsy = 0,
            hd = false,
            hm = false;
        heroEl.addEventListener(
            'touchstart',
            function (e) {
                hsx = e.touches[0].clientX;
                hsy = e.touches[0].clientY;
                hd = true;
                hm = false;
            },
            { passive: true }
        );
        heroEl.addEventListener(
            'touchmove',
            function (e) {
                if (!hd) return;
                var dx = e.touches[0].clientX - hsx,
                    dy = e.touches[0].clientY - hsy;
                if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) {
                    hm = true;
                    e.preventDefault();
                }
            },
            { passive: false }
        );
        heroEl.addEventListener(
            'touchend',
            function (e) {
                if (!hd) return;
                hd = false;
                var dx = e.changedTouches[0].clientX - hsx;
                if (hm && Math.abs(dx) > 50) window.heroSlide(dx < 0 ? 1 : -1);
            },
            { passive: true }
        );
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHomePage);
    } else {
        initHomePage();
    }
})();
