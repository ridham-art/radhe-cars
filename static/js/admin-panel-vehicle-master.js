(function () {
    function qs(sel, root) {
        return (root || document).querySelector(sel);
    }

    function qsa(sel, root) {
        return Array.prototype.slice.call((root || document).querySelectorAll(sel));
    }

    function openModal(id) {
        var el = document.getElementById(id);
        if (el) {
            el.classList.add('is-open');
            el.setAttribute('aria-hidden', 'false');
            var input = el.querySelector('input[type="text"], select');
            if (input) input.focus();
        }
    }

    function closeModal(id) {
        var el = document.getElementById(id);
        if (el) {
            el.classList.remove('is-open');
            el.setAttribute('aria-hidden', 'true');
        }
    }

    function syncConfirm(form, btnSel) {
        var formEl = typeof form === 'string' ? document.getElementById(form) : form;
        if (!formEl) return;
        var btn = formEl.querySelector(btnSel || '.btn-confirm');
        if (!btn) return;
        var nameInput = formEl.querySelector('input[name="name"]');
        var fuels = formEl.querySelectorAll('input[name="supported_fuels"]:checked');
        var disabled = false;
        if (nameInput && !nameInput.value.trim()) disabled = true;
        if (formEl.id === 'vm-model-form' && fuels.length === 0) disabled = true;
        btn.disabled = disabled;
    }

    function wireModal(backdropId, openSelectors) {
        var backdrop = document.getElementById(backdropId);
        if (!backdrop) return;
        var form = backdrop.querySelector('form');

        backdrop.addEventListener('click', function (e) {
            if (e.target === backdrop) closeModal(backdropId);
        });

        qsa('[data-close="' + backdropId + '"]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                closeModal(backdropId);
            });
        });

        openSelectors.forEach(function (sel) {
            qsa(sel).forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (form) {
                        if (btn.dataset.editName !== undefined) {
                            var nameInput = form.querySelector('input[name="name"]');
                            if (nameInput) nameInput.value = btn.dataset.editName;
                        }
                        if (btn.dataset.editId) {
                            var action = btn.dataset.editAction;
                            if (action) form.action = action;
                        }
                        if (btn.dataset.editFuels) {
                            var fuels = btn.dataset.editFuels.split(',');
                            qsa('input[name="supported_fuels"]', form).forEach(function (cb) {
                                cb.checked = fuels.indexOf(cb.value) !== -1;
                                cb.closest('.vm-check').classList.toggle('on', cb.checked);
                            });
                        }
                        if (btn.dataset.variantFuel) {
                            var fuelSel = form.querySelector('select[name="fuel_type"]');
                            if (fuelSel) fuelSel.value = btn.dataset.variantFuel;
                        }
                        if (btn.dataset.variantTrans) {
                            var transSel = form.querySelector('select[name="transmission"]');
                            if (transSel) transSel.value = btn.dataset.variantTrans;
                        }
                        if (!btn.dataset.editId && form.dataset.addAction) {
                            form.action = form.dataset.addAction;
                            var nameInput2 = form.querySelector('input[name="name"]');
                            if (nameInput2 && !btn.dataset.editName) nameInput2.value = '';
                        }
                        syncConfirm(form);
                    }
                    openModal(backdropId);
                });
            });
        });

        if (form) {
            form.addEventListener('input', function () {
                syncConfirm(form);
            });
            form.addEventListener('change', function () {
                syncConfirm(form);
            });
            syncConfirm(form);
        }
    }

    qsa('.vm-check input').forEach(function (cb) {
        cb.addEventListener('change', function () {
            cb.closest('.vm-check').classList.toggle('on', cb.checked);
        });
    });

    qsa('form.vm-delete-form').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            var msg = form.getAttribute('data-confirm');
            if (msg && !window.confirm(msg)) e.preventDefault();
        });
    });

    qsa('.vm-acts button, .vm-acts form').forEach(function (el) {
        el.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    });

    wireModal('vm-make-modal', ['[data-open-make-modal]']);
    wireModal('vm-model-modal', ['[data-open-model-modal]']);
    wireModal('vm-variant-modal', ['[data-open-variant-modal]']);

    var bulkBackdrop = document.getElementById('vm-variant-bulk-modal');
    var bulkForm = document.getElementById('vm-variant-bulk-form');
    var bulkText = document.getElementById('vm-variant-bulk-text');
    var bulkSubmit = document.getElementById('vm-variant-bulk-submit');

    function syncBulkSubmit() {
        if (bulkSubmit && bulkText) {
            bulkSubmit.disabled = !bulkText.value.trim();
        }
    }

    if (bulkBackdrop && bulkForm) {
        bulkBackdrop.addEventListener('click', function (e) {
            if (e.target === bulkBackdrop) closeModal('vm-variant-bulk-modal');
        });
        qsa('[data-close="vm-variant-bulk-modal"]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                closeModal('vm-variant-bulk-modal');
            });
        });
        qsa('[data-open-variant-bulk-modal]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (bulkText) bulkText.value = '';
                syncBulkSubmit();
                openModal('vm-variant-bulk-modal');
            });
        });
        if (bulkText) {
            bulkText.addEventListener('input', syncBulkSubmit);
        }
    }
})();
