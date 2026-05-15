(function () {
    'use strict';

    var cfgEl = document.getElementById('cf-config');
    if (!cfgEl) return;

    var cfg = {};
    try {
        cfg = JSON.parse(cfgEl.textContent || '{}');
    } catch (_e) {
        cfg = {};
    }

    var brandEl = document.getElementById('id_brand');
    var modelEl = document.getElementById('id_model');
    var transEl = document.getElementById('id_transmission');
    var fuelEl = document.getElementById('id_fuel_type');
    var variantEl = document.getElementById('id_variant');
    var variantSelect = document.getElementById('cf-variant-select');

    function apiTransmission() {
        if (!transEl || !transEl.value) return '';
        return transEl.value === 'AT' ? 'AUTOMATIC' : 'MANUAL';
    }

    function loadModels(brandId, selectedId) {
        if (!brandEl || !modelEl) return;
        if (!brandId) {
            modelEl.innerHTML = '<option value="">---------</option>';
            return;
        }
        fetch('/admin-panel/api/brands/' + brandId + '/models/', {
            credentials: 'same-origin',
            headers: { Accept: 'application/json' },
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                var keep = selectedId ? String(selectedId) : String(modelEl.value || '');
                modelEl.innerHTML = '';
                (data.models || []).forEach(function (m) {
                    var opt = document.createElement('option');
                    opt.value = m.id;
                    opt.textContent = m.name;
                    if (keep && String(m.id) === keep) opt.selected = true;
                    modelEl.appendChild(opt);
                });
                loadVariants();
            })
            .catch(function () {});
    }

    function setVariantSelectOptions(variants) {
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

    function applyVariantMeta(item) {
        if (!item) return;
        var fuel = item.fuel_type || (item.dataset && item.dataset.fuel);
        var trans = item.transmission || (item.dataset && item.dataset.trans);
        if (fuel && fuelEl) fuelEl.value = fuel;
        if (trans === 'Manual' && transEl) transEl.value = 'MT';
        if (trans === 'Automatic' && transEl) transEl.value = 'AT';
    }

    function loadVariants() {
        if (!variantSelect || !modelEl) return;
        var modelId = modelEl.value;
        if (!modelId) {
            setVariantSelectOptions([]);
            return;
        }
        var url = '/api/variants/?model_id=' + encodeURIComponent(modelId);
        var t = apiTransmission();
        if (t) url += '&transmission=' + encodeURIComponent(t);

        variantSelect.disabled = true;
        variantSelect.innerHTML = '<option value="">Loading variants…</option>';

        fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) {
                return r.json();
            })
            .then(function (rows) {
                setVariantSelectOptions(rows || []);
            })
            .catch(function () {
                setVariantSelectOptions([]);
            });
    }

    if (brandEl) {
        brandEl.addEventListener('change', function () {
            loadModels(this.value, null);
        });
    }
    if (modelEl) {
        modelEl.addEventListener('change', loadVariants);
    }
    if (transEl) {
        transEl.addEventListener('change', loadVariants);
    }
    if (variantSelect) {
        variantSelect.addEventListener('change', function () {
            var opt = variantSelect.options[variantSelect.selectedIndex];
            if (!opt || !opt.value) return;
            if (variantEl) variantEl.value = opt.value;
            applyVariantMeta(opt);
        });
    }
    if (variantEl) {
        variantEl.addEventListener('input', function () {
            if (!variantSelect) return;
            var v = this.value.trim();
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

    if (brandEl && brandEl.value) {
        loadModels(brandEl.value, cfg.modelId || modelEl.value);
    } else if (cfg.modelId && modelEl) {
        loadVariants();
    }

    /* Image compression (ported from car_form.html) */
    var formEl = document.getElementById('car-admin-form');
    var imagesInput = document.getElementById('admin-images-input');
    var previewWrap = document.getElementById('admin-new-image-preview-wrap');
    var previewGrid = document.getElementById('admin-new-image-preview-grid');
    var dropzone = document.getElementById('cf-dropzone');

    if (dropzone && imagesInput) {
        dropzone.addEventListener('click', function () {
            imagesInput.click();
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

    if (!formEl || !imagesInput) return;

    var previewObjectUrls = [];
    var compressionMeta = [];

    function formatSize(bytes) {
        if (!bytes || bytes < 0) return '0 KB';
        if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
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

    function clearPreview() {
        previewObjectUrls.forEach(function (url) {
            URL.revokeObjectURL(url);
        });
        previewObjectUrls = [];
        if (previewGrid) previewGrid.innerHTML = '';
        if (previewWrap) previewWrap.classList.add('hidden');
    }

    function renderNewImagePreview(preferredChoice) {
        if (!previewWrap || !previewGrid) return;
        clearPreview();
        var files = Array.prototype.slice.call(imagesInput.files || []);
        if (!files.length) return;
        previewWrap.classList.remove('hidden');

        var selectedForForm = document.querySelector('input[name="primary_image_choice"]:checked');
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

    imagesInput.addEventListener('change', function () {
        compressionMeta = [];
        renderNewImagePreview();
    });

    formEl.addEventListener('submit', function (e) {
        if (formEl.dataset.compressedOnce === '1') return;
        if (!imagesInput.files || !imagesInput.files.length) return;
        if (typeof DataTransfer === 'undefined') return;

        e.preventDefault();
        formEl.dataset.compressedOnce = '1';

        var submitBtn = formEl.querySelector('button[type="submit"]');
        var originalText = submitBtn ? submitBtn.textContent : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Compressing images...';
        }

        var selectedBeforeCompress = '';
        var selectedRadio = document.querySelector('input[name="primary_image_choice"]:checked');
        if (selectedRadio) selectedBeforeCompress = selectedRadio.value;

        var files = Array.prototype.slice.call(imagesInput.files);
        Promise.all(files.map(compressFile))
            .then(function (processedFiles) {
                var dt = new DataTransfer();
                processedFiles.forEach(function (f) {
                    if (f) dt.items.add(f);
                });
                imagesInput.files = dt.files;
                renderNewImagePreview(selectedBeforeCompress);
                if (submitBtn) submitBtn.textContent = 'Saving...';
                formEl.submit();
            })
            .catch(function () {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText || 'Save vehicle';
                }
                delete formEl.dataset.compressedOnce;
            });
    });
})();
