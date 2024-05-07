$(function() {

    function attachDraggableAndSortable() {
        $('img').draggable();
        $('#image-container').sortable({
            update: function(event, ui) {
                var imageOrder = $(this).sortable('toArray');
                console.log(imageOrder); // Вывод списка файлов в консоль
                $.post('/reorder_images', {image_order: imageOrder});
            }
        });
    }

    $('#upload-form input[type="file"]').on('change', function() {
        var files = this.files;
        var container = $('#image-container');
        container.empty();

        for (var i = 0; i < files.length; i++) {
            var file = files[i];
            if (file.type.match('image.*')) {
                (function(file) {
                    var reader = new FileReader();
                    reader.onload = function(e) {
                        var img = $('<img>').attr('src', URL.createObjectURL(file)).attr('alt', file.name).attr('id', file.name);
                        container.append(img);
                    }
                    reader.readAsDataURL(file);
                })(file);
            }
        }

        attachDraggableAndSortable(); // Перепривязываем события после добавления изображений
    });

    // Первоначальная привязка событий draggable и sortable при загрузке страницы
    attachDraggableAndSortable();

    $('#upload-form').on('submit', function(event) {
        event.preventDefault();
        var formData = new FormData(this);
        $.ajax({
            url: '/',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(data) {
                location.reload();
            },
            error: function(error) {
                console.error(error);
            }
        });
    });
});
