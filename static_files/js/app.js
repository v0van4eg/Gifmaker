$(function () {
    const dropArea = document.getElementById('drop-area');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        let dt = e.dataTransfer;
        let files = dt.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        uploadFiles(files);
    }

    function uploadFiles(files) {
        let formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        $.ajax({
            url: '/api/upload',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function () {
                location.reload();
            },
            error: function (xhr, status, error) {
                console.error('Ошибка загрузки файлов:', error);
                alert('Ошибка загрузки файлов: ' + error);
            }
        });
    }

    function attachDraggableAndSortable() {
        $('#image-container').sortable({
            update: function () {
                let imageOrder = $(this).sortable('toArray');
                $.post('/api/reorder_images', {image_order: imageOrder});
            }
        });
    }

    $('#upload-form input[type="file"]').on('change', function () {
        let formData = new FormData();
        $.each(this.files, function (_, file) {
            formData.append('files', file);
        });
        $.ajax({
            url: '/api/upload',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function () {
                location.reload();
            },
            error: function (xhr, status, error) {
                console.error('Ошибка загрузки файлов:', error);
                alert('Ошибка загрузки файлов: ' + error);
            }
        });
    });

    $(document).on('click', '.remove-btn', function () {
        let imageName = $(this).data('image');
        let imageWrapper = $(this).closest('.image-wrapper');

        $.post('/api/remove_image', {image_name: imageName}, function () {
            imageWrapper.remove();
        }).fail(function (xhr, status, error) {
            console.error('Ошибка удаления изображения:', error);
            alert('Ошибка удаления изображения: ' + error);
        });
    });

    $('#generate-form').on('submit', function (e) {
        e.preventDefault();
        let formData = new FormData(this);
        $('#progress-container').show();
        $('#progress-bar').width('0%').text('0%');

        $.ajax({
            url: '/api/generate_gif',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            xhr: function () {
                let xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener('progress', function (evt) {
                    if (evt.lengthComputable) {
                        let percentComplete = evt.loaded / evt.total * 100;
                        $('#progress-bar').width(percentComplete + '%').text(percentComplete.toFixed(2) + '%');
                    }
                }, false);
                return xhr;
            },
            success: function () {
                $('#progress-container').hide();
                location.reload();
            },
            error: function (xhr, status, error) {
                console.error('Ошибка генерации GIF:', error);
                $('#progress-container').hide();
                alert('Ошибка генерации GIF: ' + error);
            }
        });
    });

    $('#reverse-order-btn').on('click', function () {
        let images = $('#image-container .image-wrapper').toArray().reverse();
        $('#image-container').html(images);

        let imageOrder = images.map(img => img.id);
        $.post('/api/reorder_images', {image_order: imageOrder});
    });

    attachDraggableAndSortable();
});
