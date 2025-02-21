$(function () {
    const dropArea = document.getElementById('drop-area');

    // Получаем session_id из сервера
    let session_id = null;

    // Функция для получения session_id
    function getSessionId() {
        return $.getJSON('/get_session_id').then(function (data) {
            session_id = data.session_id;
            return session_id;
        });
    }

    // Инициализация session_id при загрузке страницы
    getSessionId().then(() => {
        console.log('Session ID:', session_id);
    });

    // Обработчики событий для drag-and-drop
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

    // Загрузка файлов на сервер
    function uploadFiles(files) {
        let formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            headers: { 'X-Session-ID': session_id },
            success: function (response) {
                if (response.success) {
                    updateImageList();
                } else {
                    alert('Ошибка при загрузке файлов: ' + response.error);
                }
            },
            error: function (xhr, status, error) {
                alert('Произошла ошибка: ' + error);
            }
        });
    }

    // Обновление списка изображений
    function updateImageList() {
        $.getJSON('/get_images', function (data) {
            let imageContainer = $('#image-container');
            imageContainer.empty();
            if (data.images && Array.isArray(data.images)) {
                data.images.forEach((image, index) => {
                    let imageWrapper = $('<div class="image-wrapper"></div>');
                    let imgElement = $('<img>').attr('src', `/uploads/${image}`).addClass('draggable');
                    let removeBtn = $('<button class="remove-btn" data-image-name="' + image + '">✖</button>');
                    imageWrapper.append(removeBtn).append(imgElement);
                    imageContainer.append(imageWrapper);
                });
                makeImagesDraggable();
            } else {
                console.error('Ошибка: данные изображений не являются массивом');
            }
        });
    }

    // Сделать изображения перетаскиваемыми
    function makeImagesDraggable() {
        $('#image-container').sortable({
            update: function () {
                let imageOrder = {};
                $('#image-container').children().each(function (index) {
                    let imageSrc = $(this).find('img').attr('src').split('/').pop();
                    imageOrder[index + 1] = imageSrc;
                });

                $.ajax({
                    url: '/reorder_images',
                    type: 'POST',
                    headers: { 'X-Session-ID': session_id },
                    data: { image_order: JSON.stringify(imageOrder) },
                    contentType: 'application/x-www-form-urlencoded',
                    success: function (response) {
                        if (!response.success) {
                            console.error('Ошибка перестановки изображений:', response.error);
                            alert('Ошибка перестановки изображений: ' + response.error);
                        } else {
                            console.log('Перестановка успешна:', response);
                        }
                    },
                    error: function (xhr, status, error) {
                        console.error('Ошибка перестановки изображений:', xhr.responseText || error);
                        alert('Ошибка перестановки изображений: ' + (xhr.responseText || error));
                    }
                });
            }
        });
    }

    $('#new-session-btn').on('click', function () {
        $.getJSON('/new_session', function (data) {
            if (data.session_id) {
                session_id = data.session_id;
                localStorage.setItem('session_id', session_id);
                updateImageList();  // Обновляем список изображений
            } else {
                alert('Ошибка при создании новой сессии');
            }
        });
    });

    // Удаление изображения
    $(document).on('click', '.remove-btn', function () {
        let imageName = $(this).data('image-name');
        let imageWrapper = $(this).closest('.image-wrapper');
        let removeButton = $(this);

        removeButton.prop('disabled', true);

        $.ajax({
            url: '/remove_image',
            type: 'POST',
            headers: { 'X-Session-ID': session_id },
            data: { image_name: imageName },
            success: function (response) {
                if (response.success) {
                    imageWrapper.remove();
                    updateImageList();
                } else {
                    alert('Ошибка при удалении изображения: ' + response.message);
                }
            },
            error: function (xhr, status, error) {
                console.error('Ошибка удаления изображения:', error);
                alert('Ошибка удаления изображения: ' + error);
            },
            complete: function () {
                removeButton.prop('disabled', false);
            }
        });
    });

    // Генерация GIF
    $('#generate-form').on('submit', function (e) {
        e.preventDefault();
        let formData = new FormData(this);
        $('#progress-container').show();
        $('#progress-bar').width('0%').text('0%');

        $.ajax({
            url: '/generate_gif',
            type: 'POST',
            headers: { 'X-Session-ID': session_id },
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
            success: function (response) {
                $('#progress-container').hide();
                if (response.success) {
                    window.location.href = '/';
                } else {
                    alert('Ошибка генерации GIF: ' + response.error);
                }
            },
            error: function (xhr, status, error) {
                console.error('Ошибка генерации GIF:', error);
                $('#progress-container').hide();
                alert('Ошибка генерации GIF: ' + error);
            }
        });
    });

    // Инициализация списка изображений при загрузке страницы
    updateImageList();
});