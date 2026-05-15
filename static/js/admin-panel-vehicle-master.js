(function () {
    'use strict';

    var MODAL_IDS = [
        'vm-make-modal',
        'vm-model-modal',
        'vm-variant-modal',
        'vm-brand-bulk-modal',
        'vm-brand-bulk-delete-modal',
        'vm-model-bulk-modal',
        'vm-model-bulk-delete-modal',
        'vm-variant-bulk-modal',
        'vm-variant-bulk-delete-modal',
    ];
    var modalsWired = false;
    var partialAbort = null;

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
            var input = el.querySelector('input[type="text"], select, textarea');
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

    function closeAllModals() {
        MODAL_IDS.forEach(closeModal);
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

    function setHidden(form, name, value) {
        var el = form && form.querySelector('input[name="' + name + '"]');
        if (el) el.value = value || '';
    }

    function syncModalFields() {
        var state = document.getElementById('vm-state');
        var makeId = '';
        var makeName = '';
        var modelId = '';
        var modelName = '';
        var qMake = '';
        var qModel = '';
        var qVariant = '';

        if (state) {
            makeId = state.getAttribute('data-make') || '';
            makeName = state.getAttribute('data-make-name') || '';
            modelId = state.getAttribute('data-model') || '';
            modelName = state.getAttribute('data-model-name') || '';
            qMake = state.getAttribute('data-q-make') || '';
            qModel = state.getAttribute('data-q-model') || '';
            qVariant = state.getAttribute('data-q-variant') || '';
        } else {
            var params = new URLSearchParams(window.location.search);
            makeId = params.get('make') || '';
            modelId = params.get('model') || '';
            qMake = params.get('q_make') || '';
            qModel = params.get('q_model') || '';
            qVariant = params.get('q_variant') || '';
        }

        var forms = [
            'vm-make-form',
            'vm-model-form',
            'vm-variant-form',
            'vm-brand-bulk-form',
            'vm-brand-bulk-delete-form',
            'vm-model-bulk-form',
            'vm-model-bulk-delete-form',
            'vm-variant-bulk-form',
            'vm-variant-bulk-delete-names-form',
        ];
        forms.forEach(function (id) {
            var form = document.getElementById(id);
            if (!form) return;
            setHidden(form, 'make', makeId);
            setHidden(form, 'model', modelId);
            setHidden(form, 'q_make', qMake);
            setHidden(form, 'q_model', qModel);
            setHidden(form, 'q_variant', qVariant);
            setHidden(form, 'brand_id', makeId);
            setHidden(form, 'car_model_id', modelId);
        });

        var makeLabel = document.getElementById('vm-model-modal-make');
        if (makeLabel) makeLabel.textContent = makeName || '—';
        ['vm-model-bulk-modal-brand', 'vm-model-bulk-delete-modal-brand'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.textContent = makeName || '—';
        });
        ['vm-variant-modal-model', 'vm-variant-bulk-modal-model', 'vm-variant-bulk-delete-modal-model'].forEach(
            function (id) {
                var el = document.getElementById(id);
                if (el) el.textContent = modelName || '—';
            }
        );
    }

    function prepareFormFromButton(form, btn) {
        if (!form || !btn) return;
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
                var wrap = cb.closest('.vm-check');
                if (wrap) wrap.classList.toggle('on', cb.checked);
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
            if (nameInput2 && btn.dataset.editName === undefined) nameInput2.value = '';
        }
        syncConfirm(form);
    }

    function initModals() {
        if (modalsWired || !document.getElementById('vm-make-form')) return;
        modalsWired = true;

        qsa('.vm-check input').forEach(function (cb) {
            cb.addEventListener('change', function () {
                var wrap = cb.closest('.vm-check');
                if (wrap) wrap.classList.toggle('on', cb.checked);
            });
        });

        MODAL_IDS.forEach(function (backdropId) {
            var backdrop = document.getElementById(backdropId);
            if (!backdrop) return;
            backdrop.addEventListener('click', function (e) {
                if (e.target === backdrop) closeModal(backdropId);
            });
            qsa('[data-close="' + backdropId + '"]', backdrop).forEach(function (btn) {
                btn.addEventListener('click', function () {
                    closeModal(backdropId);
                });
            });
            var form = backdrop.querySelector('form');
            if (form) {
                form.addEventListener('input', function () {
                    syncConfirm(form);
                });
                form.addEventListener('change', function () {
                    syncConfirm(form);
                });
            }
        });

        document.addEventListener(
            'click',
            function (e) {
                var makeBtn = e.target.closest('[data-open-make-modal]');
                if (makeBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var form = document.getElementById('vm-make-form');
                    prepareFormFromButton(form, makeBtn);
                    openModal('vm-make-modal');
                    return;
                }
                var modelBtn = e.target.closest('[data-open-model-modal]');
                if (modelBtn && !modelBtn.disabled) {
                    e.preventDefault();
                    e.stopPropagation();
                    var modelForm = document.getElementById('vm-model-form');
                    prepareFormFromButton(modelForm, modelBtn);
                    openModal('vm-model-modal');
                    return;
                }
                var variantBtn = e.target.closest('[data-open-variant-modal]');
                if (variantBtn && !variantBtn.disabled) {
                    e.preventDefault();
                    e.stopPropagation();
                    var variantForm = document.getElementById('vm-variant-form');
                    prepareFormFromButton(variantForm, variantBtn);
                    openModal('vm-variant-modal');
                    return;
                }
                var brandBulkBtn = e.target.closest('[data-open-brand-bulk-modal]');
                if (brandBulkBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var brandBulkText = document.getElementById('vm-brand-bulk-text');
                    if (brandBulkText) brandBulkText.value = '';
                    syncBrandBulkSubmit();
                    openModal('vm-brand-bulk-modal');
                    return;
                }
                var brandBulkDelBtn = e.target.closest('[data-open-brand-bulk-delete-modal]');
                if (brandBulkDelBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var brandBulkDeleteText = document.getElementById('vm-brand-bulk-delete-text');
                    if (brandBulkDeleteText) {
                        brandBulkDeleteText.value = '';
                        brandBulkDeleteText.focus();
                    }
                    syncBrandBulkDeleteSubmit();
                    openModal('vm-brand-bulk-delete-modal');
                    return;
                }
                var modelBulkBtn = e.target.closest('[data-open-model-bulk-modal]');
                if (modelBulkBtn && !modelBulkBtn.disabled) {
                    e.preventDefault();
                    e.stopPropagation();
                    var modelBulkText = document.getElementById('vm-model-bulk-text');
                    if (modelBulkText) modelBulkText.value = '';
                    syncModelBulkSubmit();
                    openModal('vm-model-bulk-modal');
                    return;
                }
                var modelBulkDelBtn = e.target.closest('[data-open-model-bulk-delete-modal]');
                if (modelBulkDelBtn && !modelBulkDelBtn.disabled) {
                    e.preventDefault();
                    e.stopPropagation();
                    var modelBulkDeleteText = document.getElementById('vm-model-bulk-delete-text');
                    if (modelBulkDeleteText) {
                        modelBulkDeleteText.value = '';
                        modelBulkDeleteText.focus();
                    }
                    syncModelBulkDeleteSubmit();
                    openModal('vm-model-bulk-delete-modal');
                    return;
                }
                var bulkBtn = e.target.closest('[data-open-variant-bulk-modal]');
                if (bulkBtn && !bulkBtn.disabled) {
                    e.preventDefault();
                    e.stopPropagation();
                    var bulkText = document.getElementById('vm-variant-bulk-text');
                    if (bulkText) bulkText.value = '';
                    syncVariantBulkSubmit();
                    openModal('vm-variant-bulk-modal');
                    return;
                }
                var bulkDelBtn = e.target.closest('[data-open-variant-bulk-delete-modal]');
                if (bulkDelBtn && !bulkDelBtn.disabled) {
                    e.preventDefault();
                    e.stopPropagation();
                    var bulkDeleteText = document.getElementById('vm-variant-bulk-delete-text');
                    if (bulkDeleteText) {
                        bulkDeleteText.value = '';
                        bulkDeleteText.focus();
                    }
                    syncVariantBulkDeleteSubmit();
                    openModal('vm-variant-bulk-delete-modal');
                }
            },
            true
        );

        var brandBulkText = document.getElementById('vm-brand-bulk-text');
        if (brandBulkText) brandBulkText.addEventListener('input', syncBrandBulkSubmit);
        var brandBulkDeleteText = document.getElementById('vm-brand-bulk-delete-text');
        if (brandBulkDeleteText) brandBulkDeleteText.addEventListener('input', syncBrandBulkDeleteSubmit);
        var modelBulkText = document.getElementById('vm-model-bulk-text');
        if (modelBulkText) modelBulkText.addEventListener('input', syncModelBulkSubmit);
        var modelBulkDeleteText = document.getElementById('vm-model-bulk-delete-text');
        if (modelBulkDeleteText) modelBulkDeleteText.addEventListener('input', syncModelBulkDeleteSubmit);

        var bulkText = document.getElementById('vm-variant-bulk-text');
        if (bulkText) bulkText.addEventListener('input', syncVariantBulkSubmit);

        var bulkDeleteText = document.getElementById('vm-variant-bulk-delete-text');
        if (bulkDeleteText) bulkDeleteText.addEventListener('input', syncVariantBulkDeleteSubmit);

        var brandBulkDeleteForm = document.getElementById('vm-brand-bulk-delete-form');
        if (brandBulkDeleteForm) {
            brandBulkDeleteForm.addEventListener('submit', function (e) {
                if (!window.confirm('Delete the listed brands? Brands in use by inventory are skipped.')) {
                    e.preventDefault();
                }
            });
        }
        var modelBulkDeleteForm = document.getElementById('vm-model-bulk-delete-form');
        if (modelBulkDeleteForm) {
            modelBulkDeleteForm.addEventListener('submit', function (e) {
                if (!window.confirm('Delete the listed models for this brand?')) {
                    e.preventDefault();
                }
            });
        }
        var bulkDeleteNamesForm = document.getElementById('vm-variant-bulk-delete-names-form');
        if (bulkDeleteNamesForm) {
            bulkDeleteNamesForm.addEventListener('submit', function (e) {
                if (!window.confirm('Delete the listed variants for this model?')) {
                    e.preventDefault();
                }
            });
        }

        document.addEventListener('ap:form:success', function () {
            closeAllModals();
            qsa('#vm-make-form input[name="name"], #vm-variant-form input[name="name"]').forEach(
                function (inp) {
                    inp.value = '';
                }
            );
            ['vm-brand-bulk-text', 'vm-brand-bulk-delete-text', 'vm-model-bulk-text', 'vm-model-bulk-delete-text', 'vm-variant-bulk-text', 'vm-variant-bulk-delete-text'].forEach(
                function (id) {
                    var el = document.getElementById(id);
                    if (el) el.value = '';
                }
            );
            syncBrandBulkSubmit();
            syncBrandBulkDeleteSubmit();
            syncModelBulkSubmit();
            syncModelBulkDeleteSubmit();
            syncVariantBulkSubmit();
            syncVariantBulkDeleteSubmit();
        });
    }

    function syncBrandBulkSubmit() {
        var btn = document.getElementById('vm-brand-bulk-submit');
        var text = document.getElementById('vm-brand-bulk-text');
        if (btn && text) btn.disabled = !text.value.trim();
    }

    function syncBrandBulkDeleteSubmit() {
        var btn = document.getElementById('vm-brand-bulk-delete-submit');
        var text = document.getElementById('vm-brand-bulk-delete-text');
        if (btn && text) btn.disabled = !text.value.trim();
    }

    function syncModelBulkSubmit() {
        var btn = document.getElementById('vm-model-bulk-submit');
        var text = document.getElementById('vm-model-bulk-text');
        if (btn && text) btn.disabled = !text.value.trim();
    }

    function syncModelBulkDeleteSubmit() {
        var btn = document.getElementById('vm-model-bulk-delete-submit');
        var text = document.getElementById('vm-model-bulk-delete-text');
        if (btn && text) btn.disabled = !text.value.trim();
    }

    function syncVariantBulkSubmit() {
        var bulkSubmit = document.getElementById('vm-variant-bulk-submit');
        var bulkText = document.getElementById('vm-variant-bulk-text');
        if (bulkSubmit && bulkText) {
            bulkSubmit.disabled = !bulkText.value.trim();
        }
    }

    function syncVariantBulkDeleteSubmit() {
        var bulkDeleteSubmit = document.getElementById('vm-variant-bulk-delete-submit');
        var bulkDeleteText = document.getElementById('vm-variant-bulk-delete-text');
        if (bulkDeleteSubmit && bulkDeleteText) {
            bulkDeleteSubmit.disabled = !bulkDeleteText.value.trim();
        }
    }

    function initPartial(root) {
        if (!root) root = document.querySelector('[data-ap-partial-root]');
        if (!root) return;

        if (partialAbort) partialAbort.abort();
        partialAbort = new AbortController();
        var signal = partialAbort.signal;

        qsa('form.vm-delete-form', root).forEach(function (form) {
            form.addEventListener(
                'submit',
                function (e) {
                    var msg = form.getAttribute('data-confirm');
                    if (msg && !window.confirm(msg)) e.preventDefault();
                },
                { signal: signal }
            );
        });

        qsa('.vm-acts button, .vm-acts form', root).forEach(function (el) {
            el.addEventListener(
                'click',
                function (e) {
                    e.stopPropagation();
                },
                { signal: signal }
            );
        });

        var selectAll = root.querySelector('#vm-variant-select-all');
        var deleteSelected = root.querySelector('#vm-variant-delete-selected');
        var bulkDeleteForm = root.querySelector('#vm-variant-bulk-delete-form');

        function variantCheckboxes() {
            return qsa('.vm-variant-cb', root);
        }

        function syncVariantSelection() {
            var boxes = variantCheckboxes();
            var checked = boxes.filter(function (cb) {
                return cb.checked;
            });
            if (deleteSelected) {
                deleteSelected.disabled = checked.length === 0;
                deleteSelected.textContent = checked.length
                    ? 'Delete selected (' + checked.length + ')'
                    : 'Delete selected';
            }
            if (selectAll && boxes.length) {
                selectAll.checked = checked.length === boxes.length;
                selectAll.indeterminate = checked.length > 0 && checked.length < boxes.length;
            }
        }

        if (selectAll) {
            selectAll.addEventListener(
                'change',
                function () {
                    variantCheckboxes().forEach(function (cb) {
                        cb.checked = selectAll.checked;
                    });
                    syncVariantSelection();
                },
                { signal: signal }
            );
        }

        variantCheckboxes().forEach(function (cb) {
            cb.addEventListener('change', syncVariantSelection, { signal: signal });
            cb.addEventListener(
                'click',
                function (e) {
                    e.stopPropagation();
                },
                { signal: signal }
            );
        });

        if (bulkDeleteForm) {
            bulkDeleteForm.addEventListener(
                'submit',
                function (e) {
                    var msg = deleteSelected && deleteSelected.getAttribute('data-confirm');
                    if (msg && !window.confirm(msg)) {
                        e.preventDefault();
                    }
                },
                { signal: signal }
            );
        }

        syncVariantSelection();
        syncModalFields();
    }

    function destroy() {
        if (partialAbort) {
            partialAbort.abort();
            partialAbort = null;
        }
    }

    function init() {
        if (!document.getElementById('vm-make-form')) return;
        initModals();
        initPartial();
    }

    document.addEventListener('ap:partial:load', function (e) {
        if (e.detail && e.detail.root && e.detail.root.hasAttribute('data-ap-partial-root')) {
            initPartial(e.detail.root);
        }
    });

    if (window.AdminPanel) {
        window.AdminPanel.register('vehicle_master', { init: init, destroy: destroy });
    } else {
        init();
    }
})();
