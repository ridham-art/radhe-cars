(function () {
    'use strict';

    var previewObjectUrls = [];
    var cascadeBound = false;
    var variantInputBound = false;

    function destroy() {
        previewObjectUrls.forEach(function (url) {
            try {
                URL.revokeObjectURL(url);
            } catch (_e) {}
        });
        previewObjectUrls = [];
    }

    function adminPrefix() {
        var cfg = window.AP_NAV_CONFIG || {};
        var p = cfg.adminPrefix || '/admin-panel/';
        return p.charAt(p.length - 1) === '/' ? p : p + '/';
    }

    function showCfMessage(text, level) {
        if (!text || !window.AdminPanelAjax) return;
        window.AdminPanelAjax.showMessage(text, level || 'info');
    }

    function getCarFormRoot(el) {
        if (!el || !el.closest) return null;
        return el.closest('[data-ap-car-form-root]');
    }

    function readCfConfig(root) {
        var scope = root || document.querySelector('[data-ap-car-form-root]');
        if (!scope) return {};
        var el =
            scope.querySelector('[data-cf-config]') ||
            (scope.hasAttribute('data-cf-config') ? scope : null) ||
            document.getElementById('cf-config');
        if (!el) return {};
        var raw = el.getAttribute('data-cf-config');
        if (raw == null && el.textContent) raw = el.textContent;
        try {
            return JSON.parse(raw || '{}');
        } catch (_e) {
            return {};
        }
    }

    function apiTransmission(root) {
        var transEl = root.querySelector('#id_transmission');
        if (!transEl || !transEl.value) return '';
        return transEl.value === 'AT' ? 'AUTOMATIC' : 'MANUAL';
    }

    function setVariantSelectOptions(root, variants) {
        var variantSelect = root.querySelector('#cf-variant-select');
        var variantEl = root.querySelector('#id_variant');
        var modelEl = root.querySelector('#id_model');
        if (!variantSelect) return;

        var current = variantEl ? variantEl.value.trim() : '';
        variantSelect.innerHTML = '';
        var placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = variants.length
            ? '— Pick a variant —'
            : '— No variants (type custom below) —';
        variantSelect.appendChild(placeholder);

        variants.forEach(function (item) {
            var name = typeof item === 'string' ? item : item && item.name;
            if (!name) return;
            var opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            if (item && typeof item === 'object') {
                if (item.fuel_type) opt.dataset.fuel = item.fuel_type;
                if (item.transmission) opt.dataset.trans = item.transmission;
            }
            if (current && name === current) opt.selected = true;
            variantSelect.appendChild(opt);
        });

        variantSelect.disabled = !modelEl || !modelEl.value;
    }

    function applyVariantMeta(root, item) {
        if (!item) return;
        var fuelEl = root.querySelector('#id_fuel_type');
        var transEl = root.querySelector('#id_transmission');
        var fuel = item.fuel_type || (item.dataset && item.dataset.fuel);
        var trans = item.transmission || (item.dataset && item.dataset.trans);
        if (fuel && fuelEl) fuelEl.value = fuel;
        if (trans === 'Manual' && transEl) transEl.value = 'MT';
        if (trans === 'Automatic' && transEl) transEl.value = 'AT';
    }

    function loadVariants(root) {
        var variantSelect = root.querySelector('#cf-variant-select');
        var modelEl = root.querySelector('#id_model');
        if (!variantSelect || !modelEl) return;

        var modelId = modelEl.value;
        if (!modelId) {
            setVariantSelectOptions(root, []);
            return;
        }

        var url = '/api/variants/?model_id=' + encodeURIComponent(modelId);
        var t = apiTransmission(root);
        if (t) url += '&transmission=' + encodeURIComponent(t);

        variantSelect.disabled = true;
        variantSelect.innerHTML = '<option value="">Loading variants…</option>';

        fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) {
                if (!r.ok) throw new Error('Could not load variants.');
                return r.json();
            })
            .then(function (rows) {
                setVariantSelectOptions(root, rows || []);
            })
            .catch(function (err) {
                setVariantSelectOptions(root, []);
                showCfMessage((err && err.message) || 'Could not load variants.', 'error');
            });
    }

    function loadModels(root, brandId, selectedId) {
        var brandEl = root.querySelector('#id_brand');
        var modelEl = root.querySelector('#id_model');
        if (!brandEl || !modelEl) return;

        if (!brandId) {
            modelEl.innerHTML = '<option value="">---------</option>';
            setVariantSelectOptions(root, []);
            return;
        }

        var url =
            adminPrefix() + 'api/brands/' + encodeURIComponent(brandId) + '/models/';

        fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) {
                if (!r.ok) throw new Error('Could not load models for this brand.');
                return r.json();
            })
            .then(function (data) {
                var keep = selectedId ? String(selectedId) : String(modelEl.value || '');
                var models = data.models || [];
                modelEl.innerHTML = '';
                models.forEach(function (m) {
                    var opt = document.createElement('option');
                    opt.value = m.id;
                    opt.textContent = m.name;
                    if (keep && String(m.id) === keep) opt.selected = true;
                    modelEl.appendChild(opt);
                });
                if (!models.length) {
                    showCfMessage(
                        'No models for this brand. Add models in Vehicle Master first.',
                        'info'
                    );
                }
                loadVariants(root);
            })
            .catch(function (err) {
                showCfMessage((err && err.message) || 'Could not load models.', 'error');
            });
    }

    function bindCarFormCascade() {
        if (cascadeBound) return;
        cascadeBound = true;

        document.addEventListener('change', function (e) {
            var root = getCarFormRoot(e.target);
            if (!root) return;

            if (e.target.id === 'id_brand') {
                loadModels(root, e.target.value, null);
                return;
            }
            if (e.target.id === 'id_model' || e.target.id === 'id_transmission') {
                loadVariants(root);
                return;
            }
            if (e.target.id === 'cf-variant-select') {
                var opt = e.target.options[e.target.selectedIndex];
                if (!opt || !opt.value) return;
                var variantEl = root.querySelector('#id_variant');
                if (variantEl) variantEl.value = opt.value;
                applyVariantMeta(root, opt);
            }
        });
    }

    function bindVariantInput() {
        if (variantInputBound) return;
        variantInputBound = true;

        document.addEventListener('input', function (e) {
            if (e.target.id !== 'id_variant') return;
            var root = getCarFormRoot(e.target);
            if (!root) return;
            var variantSelect = root.querySelector('#cf-variant-select');
            if (!variantSelect) return;

            var v = e.target.value.trim();
            if (!v) {
                variantSelect.value = '';
                return;
            }
            for (var i = 0; i < variantSelect.options.length; i++) {
                if (variantSelect.options[i].value === v) {
                    variantSelect.selectedIndex = i;
                    return;
                }
            }
            variantSelect.value = '';
        });
    }

    function bootstrapCascade(root) {
        if (!root) return;
        var cfg = readCfConfig(root);
        var brandEl = root.querySelector('#id_brand');
        var modelEl = root.querySelector('#id_model');
        if (brandEl && brandEl.value) {
            loadModels(root, brandEl.value, cfg.modelId || (modelEl && modelEl.value));
        } else if (cfg.modelId && modelEl) {
            loadVariants(root);
        }
    }

    function applyCarFormPartial(html) {
        var root = document.querySelector('[data-ap-car-form-root]');
        if (!root || !html) return false;
        root.innerHTML = html;
        if (window.AdminPanel) {
            window.AdminPanel.runDestroy('car_form');
            window.AdminPanel.runInit('car_form');
        }
        return true;
    }

    function handleCarAjaxResponse(data) {
        if (!data || typeof data !== 'object') {
            window.location.reload();
            return Promise.resolve();
        }
        if (data.partialHtml) {
            applyCarFormPartial(data.partialHtml);
            if (data.message && window.AdminPanelAjax) {
                window.AdminPanelAjax.showMessage(data.message, data.level || 'error');
            }
            return Promise.resolve();
        }
        if (data.ok === false) {
            var err = new Error(data.message || 'Request failed');
            err.payload = data;
            return Promise.reject(err);
        }
        if (data.message && window.AdminPanelAjax) {
            window.AdminPanelAjax.showMessage(data.message, data.level || 'success');
        }
        if (data.reload && window.AdminPanel && window.AdminPanel.navigateTo) {
            return window.AdminPanel.navigateTo(data.reload);
        }
        if (data.redirect && window.AdminPanel && window.AdminPanel.navigateTo) {
            return window.AdminPanel.navigateTo(data.redirect);
        }
        return Promise.resolve();
    }

    function submitCarFormAjax(formEl, submitBtn, originalText) {
        if (!window.AdminPanelAjax) {
            formEl.submit();
            return Promise.resolve();
        }
        var body = new FormData(formEl);
        return window.AdminPanelAjax.fetchPost(formEl.action, body, { accept: 'application/json' })
            .then(handleCarAjaxResponse)
            .catch(function (err) {
                var msg = (err && err.message) || 'Could not save. Please try again.';
                if (window.AdminPanelAjax) {
                    window.AdminPanelAjax.showMessage(msg, 'error');
                }
            })
            .finally(function () {
                delete formEl.dataset.compressedOnce;
                if (submitBtn) {
                    submitBtn.disabled = false;
                    if (originalText) submitBtn.textContent = originalText;
                }
            });
    }

    function wireDropzone(root) {
        var dropzone = root.querySelector('#cf-dropzone');
        var imagesInput = root.querySelector('#admin-images-input');
        if (!dropzone || !imagesInput || dropzone.dataset.cfDropzoneBound === '1') return;
        dropzone.dataset.cfDropzoneBound = '1';

        dropzone.addEventListener('click', function () {
            imagesInput.click();
        });
        dropzone.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                imagesInput.click();
            }
        });
        dropzone.addEventListener('dragover', function (e) {
            e.preventDefault();
            dropzone.classList.add('is-dragging');
        });
        dropzone.addEventListener('dragleave', function () {
            dropzone.classList.remove('is-dragging');
        });
        dropzone.addEventListener('drop', function (e) {
            e.preventDefault();
            dropzone.classList.remove('is-dragging');
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
                imagesInput.files = e.dataTransfer.files;
                imagesInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }

    function wireImagePreview(root) {
        var imagesInput = root.querySelector('#admin-images-input');
        var previewWrap = root.querySelector('#admin-new-image-preview-wrap');
        var previewGrid = root.querySelector('#admin-new-image-preview-grid');
        if (!imagesInput || !previewWrap || !previewGrid) return;
        if (imagesInput.dataset.cfPreviewBound === '1') return;
        imagesInput.dataset.cfPreviewBound = '1';

        imagesInput.addEventListener('change', function () {
            renderNewImagePreview(root);
        });
    }

    function clearPreview(root) {
        previewObjectUrls.forEach(function (url) {
            try {
                URL.revokeObjectURL(url);
            } catch (_e) {}
        });
        previewObjectUrls = [];
        var previewGrid = root.querySelector('#admin-new-image-preview-grid');
        var previewWrap = root.querySelector('#admin-new-image-preview-wrap');
        if (previewGrid) previewGrid.innerHTML = '';
        if (previewWrap) previewWrap.classList.add('hidden');
    }

    function renderNewImagePreview(root, preferredChoice) {
        var imagesInput = root.querySelector('#admin-images-input');
        var previewWrap = root.querySelector('#admin-new-image-preview-wrap');
        var previewGrid = root.querySelector('#admin-new-image-preview-grid');
        if (!imagesInput || !previewWrap || !previewGrid) return;

        clearPreview(root);
        var files = Array.prototype.slice.call(imagesInput.files || []);
        if (!files.length) return;
        previewWrap.classList.remove('hidden');

        var selectedForForm = root.querySelector('input[name="primary_image_choice"]:checked');
        var selectedChoice = preferredChoice || (selectedForForm ? selectedForForm.value : '');
        var keepExistingChoice = selectedChoice && selectedChoice.indexOf('existing:') === 0;

        files.forEach(function (file, index) {
            var item = document.createElement('li');
            item.className = 'cf-img-card';

            var media = document.createElement('div');
            media.className = 'cf-img-media';
            var image = document.createElement('img');
            image.alt = '';
            var objectUrl = URL.createObjectURL(file);
            previewObjectUrls.push(objectUrl);
            image.src = objectUrl;
            media.appendChild(image);
            item.appendChild(media);

            var foot = document.createElement('div');
            foot.className = 'cf-img-foot';

            var name = document.createElement('span');
            name.style.fontSize = '11px';
            name.style.color = 'var(--text-muted)';
            name.style.overflow = 'hidden';
            name.style.textOverflow = 'ellipsis';
            name.style.whiteSpace = 'nowrap';
            name.textContent = file.name;
            foot.appendChild(name);

            var label = document.createElement('label');
            label.className = 'cf-primary-label';
            var radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'primary_image_choice';
            radio.value = 'new:' + index;
            radio.className = 'cf-checkbox';
            if (selectedChoice && radio.value === selectedChoice) {
                radio.checked = true;
            } else if (!selectedChoice && !keepExistingChoice && index === 0) {
                radio.checked = true;
            }
            label.appendChild(radio);
            label.appendChild(document.createTextNode(' Primary'));
            foot.appendChild(label);
            item.appendChild(foot);
            previewGrid.appendChild(item);
        });
    }

    function toWebpName(filename) {
        return filename.replace(/\.[^/.]+$/, '') + '.webp';
    }

    function drawToCanvas(imgLike, width, height) {
        var canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        var ctx = canvas.getContext('2d');
        if (!ctx) return null;
        ctx.drawImage(imgLike, 0, 0, width, height);
        return canvas;
    }

    function canvasToWebpBlob(canvas, quality) {
        return new Promise(function (resolve) {
            canvas.toBlob(function (blob) {
                resolve(blob || null);
            }, 'image/webp', quality);
        });
    }

    async function compressFile(file) {
        if (!file || !file.type || file.type.indexOf('image/') !== 0) return file;
        if (file.size <= 300 * 1024) return file;
        if (!window.createImageBitmap) return file;

        var targetMin = 200 * 1024;
        var targetMax = 300 * 1024;
        var targetMid = 250 * 1024;
        var maxSide = 1920;
        var scaleSteps = [1, 0.9, 0.8, 0.72, 0.64];
        var qualitySteps = [0.82, 0.74, 0.66, 0.58, 0.5, 0.42];

        try {
            var bitmap = await createImageBitmap(file);
            var w = bitmap.width;
            var h = bitmap.height;
            var bestFile = null;
            var bestDistance = Number.MAX_SAFE_INTEGER;

            for (var i = 0; i < scaleSteps.length; i++) {
                var baseScale = Math.min(1, maxSide / Math.max(w, h));
                var scale = Math.min(1, baseScale * scaleSteps[i]);
                var tw = Math.max(1, Math.round(w * scale));
                var th = Math.max(1, Math.round(h * scale));
                var canvas = drawToCanvas(bitmap, tw, th);
                if (!canvas) continue;

                for (var j = 0; j < qualitySteps.length; j++) {
                    var blob = await canvasToWebpBlob(canvas, qualitySteps[j]);
                    if (!blob) continue;
                    var candidate = new File([blob], toWebpName(file.name), {
                        type: 'image/webp',
                        lastModified: Date.now(),
                    });
                    var distance = Math.abs(candidate.size - targetMid);
                    if (!bestFile || distance < bestDistance) {
                        bestFile = candidate;
                        bestDistance = distance;
                    }
                    if (candidate.size >= targetMin && candidate.size <= targetMax) {
                        return candidate;
                    }
                }
            }

            if (!bestFile) return file;
            if (bestFile.size >= file.size * 0.98) return file;
            return bestFile;
        } catch (_err) {
            return file;
        }
    }

    function wireFormSubmit(root) {
        var formEl = root.querySelector('#car-admin-form');
        if (!formEl || formEl.dataset.cfSubmitBound === '1') return;
        formEl.dataset.cfSubmitBound = '1';

        formEl.addEventListener('submit', function (e) {
            e.preventDefault();
            e.stopPropagation();

            var imagesInput = root.querySelector('#admin-images-input');
            var submitBtn = formEl.querySelector('button[type="submit"]');
            var originalText = submitBtn ? submitBtn.textContent : '';

            function finishSave() {
                if (submitBtn) submitBtn.textContent = 'Saving...';
                return submitCarFormAjax(formEl, submitBtn, originalText || 'Save vehicle');
            }

            if (!imagesInput || !imagesInput.files || !imagesInput.files.length) {
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Saving...';
                }
                finishSave();
                return;
            }
            if (typeof DataTransfer === 'undefined') {
                if (submitBtn) submitBtn.disabled = true;
                finishSave();
                return;
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Compressing images...';
            }

            var selectedBeforeCompress = '';
            var selectedRadio = root.querySelector('input[name="primary_image_choice"]:checked');
            if (selectedRadio) selectedBeforeCompress = selectedRadio.value;

            var files = Array.prototype.slice.call(imagesInput.files);
            Promise.all(files.map(compressFile))
                .then(function (processedFiles) {
                    var dt = new DataTransfer();
                    processedFiles.forEach(function (f) {
                        if (f) dt.items.add(f);
                    });
                    imagesInput.files = dt.files;
                    renderNewImagePreview(root, selectedBeforeCompress);
                    return finishSave();
                })
                .catch(function () {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = originalText || 'Save vehicle';
                    }
                });
        });
    }

    function init() {
        destroy();
        bindCarFormCascade();
        bindVariantInput();

        var root = document.querySelector('[data-ap-car-form-root]');
        if (!root) return;

        bootstrapCascade(root);
        wireDropzone(root);
        wireImagePreview(root);
        wireFormSubmit(root);
    }

    document.addEventListener('ap:page:load', function (e) {
        if (e.detail && e.detail.pageKey === 'car_form') {
            init();
        }
    });

    if (window.AdminPanel) {
        window.AdminPanel.register('car_form', { init: init, destroy: destroy });
    } else {
        bindCarFormCascade();
        bindVariantInput();
        init();
    }
})();
