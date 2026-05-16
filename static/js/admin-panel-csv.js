(function () {
    'use strict';

    function initUploadForm() {
        var form = document.getElementById('csv-upload-form');
        if (!form) return;
        form.addEventListener(
            'submit',
            function (e) {
                var fileInput = form.querySelector('input[type="file"]');
                if (!fileInput || !fileInput.files || !fileInput.files.length) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (window.AdminPanelAjax) {
                        window.AdminPanelAjax.showMessage('Choose a CSV file to upload.', 'error');
                    }
                }
            },
            true
        );
    }

    function init() {
        initUploadForm();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    document.addEventListener('ap:page:load', function (e) {
        if (e.detail && e.detail.pageKey === 'csv') {
            init();
        }
    });
})();
