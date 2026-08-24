document.addEventListener("DOMContentLoaded", () => {

    const openCameraButton = document.getElementById("openCameraButton");
    const captureButton = document.getElementById("captureButton");

    const cameraPreview = document.getElementById("cameraPreview");
    const cameraPlaceholder = document.getElementById("cameraPlaceholder");

    const captureCanvas = document.getElementById("captureCanvas");
    const photoPreview = document.getElementById("photoPreview");

    const documentPhoto = document.getElementById("documentPhoto");
    const captureStatus = document.getElementById("captureStatus");

    const reviewButton = document.getElementById("reviewButton");
    const reviewCard = document.getElementById("reviewCard");

    let cameraStream = null;


    /* -------------------------
       Open Camera
    ------------------------- */

    if (openCameraButton) {

        openCameraButton.addEventListener("click", async () => {

            try {

                cameraStream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: "environment"
                    },
                    audio: false
                });

                cameraPreview.srcObject = cameraStream;

                cameraPlaceholder.classList.add("hidden");
                cameraPreview.classList.remove("hidden");
                captureButton.classList.remove("hidden");

                captureStatus.textContent = "Camera ready";

            } catch (error) {

                console.error("Camera error:", error);

                captureStatus.textContent =
                    "Camera access unavailable. Upload a document photo instead.";

            }

        });

    }


    /* -------------------------
       Capture Photo
    ------------------------- */

    if (captureButton) {

        captureButton.addEventListener("click", () => {

            if (!cameraStream) {
                return;
            }

            captureCanvas.width = cameraPreview.videoWidth;
            captureCanvas.height = cameraPreview.videoHeight;

            const context = captureCanvas.getContext("2d");

            context.drawImage(
                cameraPreview,
                0,
                0,
                captureCanvas.width,
                captureCanvas.height
            );

            const imageData =
                captureCanvas.toDataURL("image/jpeg", 0.9);

            photoPreview.src = imageData;

            cameraPreview.classList.add("hidden");
            photoPreview.classList.remove("hidden");

            captureButton.classList.add("hidden");

            captureStatus.textContent =
                "Document photo captured";

            stopCamera();

        });

    }


    /* -------------------------
       Upload Document Photo
    ------------------------- */

    if (documentPhoto) {

        documentPhoto.addEventListener("change", (event) => {

            const file = event.target.files[0];

            if (!file) {
                return;
            }

            const reader = new FileReader();

            reader.onload = (loadEvent) => {

                photoPreview.src = loadEvent.target.result;

                cameraPlaceholder.classList.add("hidden");
                cameraPreview.classList.add("hidden");
                photoPreview.classList.remove("hidden");

                captureButton.classList.add("hidden");

                captureStatus.textContent =
                    `Photo selected: ${file.name}`;

                stopCamera();

            };

            reader.readAsDataURL(file);

        });

    }


    /* -------------------------
       Review Entry
    ------------------------- */

    if (reviewButton) {

        reviewButton.addEventListener("click", () => {

            const sender =
                document.getElementById("sender").value.trim();

            const subject =
                document.getElementById("subject").value.trim();

            const reference =
                document.getElementById("referenceNumber").value.trim();

            const priority =
                document.getElementById("urgency").value;

            const branch =
                document.getElementById("receivingBranch");

            const branchText =
                branch.options[branch.selectedIndex]?.text || "—";

            const hasDocument =
                !photoPreview.classList.contains("hidden");

            document.getElementById("reviewSender").textContent =
                sender || "—";

            document.getElementById("reviewSubject").textContent =
                subject || "—";

            document.getElementById("reviewReference").textContent =
                reference || "—";

            document.getElementById("reviewPriority").textContent =
                priority || "—";

            document.getElementById("reviewBranch").textContent =
                branch.value ? branchText : "—";

            document.getElementById("reviewDocument").textContent =
                hasDocument ? "Attached" : "Not attached";

            reviewCard.classList.remove("hidden");

            reviewCard.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        });

    }


    /* -------------------------
       Stop Camera
    ------------------------- */

    function stopCamera() {

        if (!cameraStream) {
            return;
        }

        cameraStream.getTracks().forEach(track => {
            track.stop();
        });

        cameraStream = null;
    }

});