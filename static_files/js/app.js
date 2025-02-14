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
        dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
    });

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        let files = e.dataTransfer.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        uploadFiles(files);
    }

    function uploadFiles(files) {
        let formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }

        $.get('/get_session_id', function(response) {
            console.log('Ответ от сервера:', response);  // Лог для отладки
            if (!response || !response.session_id) {
                console.error('Ошибка: session_id отсутствует в ответе');
                return;
            }

            let session_id = response.session_id;
            if (typeof session_id !== 'string') {
                console.warn('session_id не строка, преобразуем:', session_id);
                session_id = JSON.stringify(session_id);
            }

            console.log('Используемый session_id:', session_id);
            formData.append('session_id', session_id);

            $.ajax({
                url: '/upload',
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
        }).fail(function() {
            console.error('Ошибка получения session_id');
        });
    }

    $('#upload-form input[type="file"]').on('change', function () {
        let files = this.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    });

    $('#generate-form').on('submit', function (e) {
        e.preventDefault();
        let formData = new FormData(this);
        $('#progress-container').show();
        $('#progress-bar').width('0%').text('0%');

        $.get('/get_session_id', function(response) {
            console.log('Ответ от сервера для GIF:', response);
            if (!response || !response.session_id) {
                console.error('Ошибка: session_id отсутствует в ответе');
                return;
            }

            let session_id = response.session_id;
            if (typeof session_id !== 'string') {
                console.warn('session_id не строка, преобразуем:', session_id);
                session_id = JSON.stringify(session_id);
            }

            console.log('session_id для генерации GIF:', session_id);
            formData.append('session_id', session_id);

            $.ajax({
                url: '/generate_gif',
                type: 'POST',
                data: formData,
                contentType: false,
                processData: false,
                xhr: function () {
                    let xhr = new window.XMLHttpRequest();
                    xhr.upload.addEventListener('progress', function (evt) {
                        if (evt.lengthComputable) {
                            let percentComplete = (evt.loaded / evt.total) * 100;
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
                }
            });
        }).fail(function() {
            console.error('Ошибка получения session_id');
        });
    });

    $(document).on('click', '.remove-btn', function () {
        let imageName = $(this).data('image');
        $.post('/remove_image', { image_name: imageName }, function () {
            location.reload();
        });
    });

    $('#reverse-order-btn').on('click', function () {
        let images = $('#image-container .image-wrapper').toArray().reverse();
        $('#image-container').html(images);
        let imageOrder = images.map(img => img.id);
        $.post('/reorder_images', { image_order: imageOrder });
    });
});
