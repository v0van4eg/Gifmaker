document.addEventListener("DOMContentLoaded", function () {
    const dropZone = document.getElementById("drop-zone");
    const imageContainer = document.getElementById("image-container");

    dropZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropZone.classList.add("highlight");
    });

    dropZone.addEventListener("dragleave", function () {
        dropZone.classList.remove("highlight");
    });

    dropZone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropZone.classList.remove("highlight");

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFiles(files);
        }
    });

    function handleFiles(files) {
        for (const file of files) {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = function (e) {
                createImageElement(e.target.result);
            };
        }
    }

    function createImageElement(src) {
        const wrapper = document.createElement("div");
        wrapper.classList.add("image-wrapper");

        const img = document.createElement("img");
        img.src = src;
        img.alt = "Uploaded Image";

        const removeBtn = document.createElement("button");
        removeBtn.classList.add("remove-btn");
        removeBtn.innerHTML = "&times;";
        removeBtn.addEventListener("click", function () {
            wrapper.remove();
        });

        wrapper.appendChild(img);
        wrapper.appendChild(removeBtn);
        imageContainer.appendChild(wrapper);
    }
});
