$(function () {
    const dropArea = document.getElementById('drop-area');

    // Получаем session_id из localStorage или создаем новый
    let session_id = localStorage.getItem('session_id');
    if (!session_id) {
        $.getJSON('/get_session_id', function(data) {
            session_id = data.session_id;
            localStorage.setItem('session_id', session_id);
        });
    }

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
            url: '/upload',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            headers: { 'X-Session-ID': session_id },
            success: function(response) {
                if (response.success) {
                    // Обновляем список изображений
                    updateImageList();
                } else {
                    alert('Ошибка при загрузке файлов: ' + response.error);
                }
            },
            error: function(xhr, status, error) {
                alert('Произошла ошибка: ' + error);
            }
        });
    }

    function updateImageList() {
        $.getJSON('/get_images', function(data) {
            let imageContainer = $('#image-container');
            imageContainer.empty();
            let imageOrder = {};
            data.images.forEach((image, index) => {
                imageOrder[index + 1] = image;
                let imageWrapper = $('<div class="image-wrapper"></div>');
                let imgElement = $('<img>').attr('src', `/uploads/${image}`).addClass('draggable');
                let removeBtn = $('<button class="remove-btn" data-image-name="' + image + '">✖</button>');
                imageWrapper.append(removeBtn).append(imgElement);
                imageContainer.append(imageWrapper);
            });
            makeImagesDraggable();
            sessionStorage.setItem('imageOrder', JSON.stringify(imageOrder));
        });
    }

    function makeImagesDraggable() {
        $('#image-container').sortable({
            update: function () {
                let imageOrder = {};
                $('#image-container').children().each(function(index) {
                    let imageSrc = $(this).find('img').attr('src').split('/').pop();
                    imageOrder[index + 1] = imageSrc;
                });
                sessionStorage.setItem('imageOrder', JSON.stringify(imageOrder));

                $.ajax({
                    url: '/reorder_images',
                    type: 'POST',
                    headers: { 'X-Session-ID': session_id },
                    data: { image_order: JSON.stringify(imageOrder) },
                    contentType: 'application/x-www-form-urlencoded',
                    success: function(response) {
                        if (!response.success) {
                            console.error('Ошибка перестановки изображений:', response.error);
                            alert('Ошибка перестановки изображений: ' + response.error);
                        } else {
                            console.log('Перестановка успешна:', response);
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('Ошибка перестановки изображений:', xhr.responseText || error);
                        alert('Ошибка перестановки изображений: ' + (xhr.responseText || error));
                    }
                });
            }
        });
    }

    // Event listener for remove button
    $(document).on('click', '.remove-btn', function () {
        let imageName = $(this).data('image-name');
        let imageWrapper = $(this).closest('.image-wrapper');
        let removeButton = $(this); // Сохраняем ссылку на кнопку

        removeButton.prop('disabled', true); // Отключаем кнопку

        $.ajax({
            url: '/remove_image',
            type: 'POST',
            headers: { 'X-Session-ID': session_id },
            data: { image_name: imageName },
            success: function(response) {
                if (response.success) {
                    // Обновляем список изображений
                    imageWrapper.remove();
                    updateImageList();
                } else {
                    alert('Ошибка при удалении изображения: ' + response.message);
                }
            },
            error: function(xhr, status, error) {
                console.error('Ошибка удаления изображения:', error);
                alert('Ошибка удаления изображения: ' + error);
            },
            complete: function() {
                removeButton.prop('disabled', false); // Включаем кнопку снова
            }
        });
    });

    $('#upload-form input[type="file"]').on('change', function () {
        let formData = new FormData();
        $.each(this.files, function (_, file) {
            formData.append('files', file);
        });
        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            headers: { 'X-Session-ID': session_id },
            success: function () {
                updateImageList(); // Обновляем список изображений без перезагрузки страницы
            },
            error: function (xhr, status, error) {
                console.error('Ошибка загрузки файлов:', error);
                alert('Ошибка загрузки файлов: ' + error);
            }
        });
    });


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
                // Перенаправляем пользователя на главную страницу
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

    $('#reverse-order-btn').on('click', function () {
        let images = $('#image-container .image-wrapper').toArray().reverse();
        $('#image-container').html(images);

        let imageOrder = {};
        images.forEach((img, index) => {
            let imageSrc = $(img).find('img').attr('src').split('/').pop();
            imageOrder[index + 1] = imageSrc;
        });
        $.ajax({
            url: '/reorder_images',
            type: 'POST',
            headers: { 'X-Session-ID': session_id },
            data: { image_order: JSON.stringify(imageOrder) },
            contentType: 'application/x-www-form-urlencoded',
            success: function(response) {
                if (!response.success) {
                    console.error('Ошибка перестановки изображений:', response.error);
                    alert('Ошибка перестановки изображений: ' + response.error);
                } else {
                    console.log('Перестановка успешна:', response);
                }
            },
            error: function(xhr, status, error) {
                console.error('Ошибка перестановки изображений:', xhr.responseText || error);
                alert('Ошибка перестановки изображений: ' + (xhr.responseText || error));
            }
        });
    });

    // Определяем функцию attachDraggableAndSortable
    function attachDraggableAndSortable() {
        makeImagesDraggable();
    }

    // Вызываем функцию после загрузки страницы
    attachDraggableAndSortable();

    // Инициализируем список изображений при загрузке страницы
    updateImageList();
});
