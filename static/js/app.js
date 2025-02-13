$(function () {
    const dropArea = document.getElementById('drop-area');
    // Предотвращаем стандартное поведение браузера при перетаскивании
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    // Изменяем стиль области при перетаскивании
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    function highlight(e) {
        dropArea.classList.add('highlight');
    }
    function unhighlight(e) {
        dropArea.classList.remove('highlight');
    }
    // Обработка перетаскивания файлов
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
            url: '/',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function () {
                location.reload();
            },
            error: function (xhr, status, error) {
                console.error('Ошибка загрузки файлов:', error);
            }
        });
    }
    function attachDraggableAndSortable() {
        $('#image-container').sortable({
            update: function () {
                let imageOrder = $(this).sortable('toArray');
                $.post('/reorder_images', {image_order: imageOrder});
            }
        });
    }
    $('#upload-form input[type="file"]').on('change', function () {
        let formData = new FormData();
        $.each(this.files, function (_, file) {
            formData.append('files', file);
        });
        $.ajax({
            url: '/',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function () {
                location.reload();
            },
            error: function (xhr, status, error) {
                console.error('Ошибка загрузки файлов:', error);
            }
        });
    });
    $(document).on('click', '.remove-btn', function () {
        let imageName = $(this).data('image');
        $.post('/remove_image', {image_name: imageName}, function () {
            location.reload();
        });
    });
    $('#generate-form').on('submit', function (e) {
        e.preventDefault();
        let formData = new FormData(this);
        $('#progress-container').show();
        $('#progress-bar').width('0%').text('0%');
        $.ajax({
            url: $(this).attr('action'),
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
                    } else {
                        console.log('evt.lengthComputable is false');
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
            }
        });
    });
    attachDraggableAndSortable();
});