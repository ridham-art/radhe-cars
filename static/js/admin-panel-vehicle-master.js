(function () {
    'use strict';

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

    function destroy() {}

    function init() {
        if (!document.getElementById('vm-make-form')) return;

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

        var bulkDeleteBackdrop = document.getElementById('vm-variant-bulk-delete-modal');
        var bulkDeleteText = document.getElementById('vm-variant-bulk-delete-text');
        var bulkDeleteSubmit = document.getElementById('vm-variant-bulk-delete-submit');

        function syncBulkDeleteSubmit() {
            if (bulkDeleteSubmit && bulkDeleteText) {
                bulkDeleteSubmit.disabled = !bulkDeleteText.value.trim();
            }
        }

        if (bulkDeleteBackdrop) {
            bulkDeleteBackdrop.addEventListener('click', function (e) {
                if (e.target === bulkDeleteBackdrop) closeModal('vm-variant-bulk-delete-modal');
            });
            qsa('[data-close="vm-variant-bulk-delete-modal"]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    closeModal('vm-variant-bulk-delete-modal');
                });
            });
            qsa('[data-open-variant-bulk-delete-modal]').forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (bulkDeleteText) bulkDeleteText.value = '';
                    syncBulkDeleteSubmit();
                    openModal('vm-variant-bulk-delete-modal');
                    if (bulkDeleteText) bulkDeleteText.focus();
                });
            });
            if (bulkDeleteText) {
                bulkDeleteText.addEventListener('input', syncBulkDeleteSubmit);
            }
            var bulkDeleteNamesForm = document.getElementById('vm-variant-bulk-delete-names-form');
            if (bulkDeleteNamesForm) {
                bulkDeleteNamesForm.addEventListener('submit', function (e) {
                    if (!window.confirm('Delete the listed variants for this model?')) {
                        e.preventDefault();
                    }
                });
            }
        }

        var selectAll = document.getElementById('vm-variant-select-all');
        var deleteSelected = document.getElementById('vm-variant-delete-selected');
        var bulkDeleteForm = document.getElementById('vm-variant-bulk-delete-form');

        function variantCheckboxes() {
            return qsa('.vm-variant-cb');
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
            selectAll.addEventListener('change', function () {
                variantCheckboxes().forEach(function (cb) {
                    cb.checked = selectAll.checked;
                });
                syncVariantSelection();
            });
        }

        variantCheckboxes().forEach(function (cb) {
            cb.addEventListener('change', syncVariantSelection);
            cb.addEventListener('click', function (e) {
                e.stopPropagation();
            });
        });

        if (bulkDeleteForm) {
            bulkDeleteForm.addEventListener('submit', function (e) {
                var msg = deleteSelected && deleteSelected.getAttribute('data-confirm');
                if (msg && !window.confirm(msg)) {
                    e.preventDefault();
                }
            });
        }

        syncVariantSelection();
    }

    if (window.AdminPanel) {
        window.AdminPanel.register('vehicle_master', { init: init, destroy: destroy });
    }
})();
