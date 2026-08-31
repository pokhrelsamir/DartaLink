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

/* =========================================
   August 25 - Approval Dashboard
========================================= */

document.addEventListener("DOMContentLoaded", () => {

    const approvalSearch =
        document.getElementById("approvalSearch");

    const approvalFilter =
        document.getElementById("approvalFilter");

    const documentItems =
        document.querySelectorAll(".document-item");

    const approveButton =
        document.getElementById("approveButton");

    const rejectButton =
        document.getElementById("rejectButton");


    /* -------------------------
       Document Selection
    ------------------------- */

    documentItems.forEach(item => {

        item.addEventListener("click", () => {

            documentItems.forEach(documentItem => {
                documentItem.classList.remove("selected");
            });

            item.classList.add("selected");

        });

    });


    /* -------------------------
       Search Queue
    ------------------------- */

    function filterDocuments() {

        const searchValue =
            approvalSearch
                ? approvalSearch.value.toLowerCase().trim()
                : "";

        const priorityValue =
            approvalFilter
                ? approvalFilter.value
                : "all";


        documentItems.forEach(item => {

            const text =
                item.textContent.toLowerCase();

            const priority =
                item.dataset.priority;


            const matchesSearch =
                text.includes(searchValue);

            const matchesPriority =
                priorityValue === "all" ||
                priority === priorityValue;


            if (matchesSearch && matchesPriority) {

                item.style.display = "grid";

            } else {

                item.style.display = "none";

            }

        });

    }


    if (approvalSearch) {

        approvalSearch.addEventListener(
            "input",
            filterDocuments
        );

    }


    if (approvalFilter) {

        approvalFilter.addEventListener(
            "change",
            filterDocuments
        );

    }


    /* -------------------------
       Approval Wireframe
    ------------------------- */

    if (approveButton) {

        approveButton.addEventListener("click", () => {

            const branch =
                document.getElementById("targetBranch");

            if (!branch || !branch.value) {

                alert(
                    "Please select a receiving branch before approval."
                );

                return;

            }

            alert(
                "Wireframe action: document approved and routed to " +
                branch.options[branch.selectedIndex].text
            );

        });

    }


    /* -------------------------
       Return Document
    ------------------------- */

    if (rejectButton) {

        rejectButton.addEventListener("click", () => {

            const instruction =
                document.getElementById("approvalInstruction");

            if (instruction) {

                instruction.focus();

            }

            alert(
                "Wireframe action: document returned for correction."
            );

        });

    }

});

/* =========================================
   August 27 - Authentication & Portal
========================================= */


document.addEventListener("DOMContentLoaded", () => {

    const loginForm =
        document.getElementById("loginForm");

    const loginMessage =
        document.getElementById("loginMessage");

    const logoutButton =
        document.getElementById("logoutButton");


    /* -------------------------
       Login UI
    ------------------------- */

    if (loginForm) {

        loginForm.addEventListener("submit", (event) => {

            /*
             * August 27:
             * UI prototype only.
             *
             * Real Django authentication will be
             * connected during backend development.
             */

            event.preventDefault();


            const username =
                document.getElementById("username").value.trim();

            const password =
                document.getElementById("password").value.trim();


            if (!username || !password) {

                if (loginMessage) {

                    loginMessage.textContent =
                        "Please enter your employee ID and password.";

                }

                return;

            }


            /*
             * Temporary prototype navigation.
             */

            window.location.href = "/portal/";

        });

    }


    /* -------------------------
       Logout UI
    ------------------------- */

    if (logoutButton) {

        logoutButton.addEventListener("click", () => {

            window.location.href = "/login/";

        });

    }

});



/* =========================================================
   DARTALINK CAMERA CAPTURE
   August 31, 2026
   ========================================================= */

const cameraVideo = document.getElementById("cameraVideo");
const cameraCanvas = document.getElementById("cameraCanvas");
const cameraPlaceholder = document.getElementById("cameraPlaceholder");

const startCameraButton = document.getElementById("startCameraButton");
const captureButton = document.getElementById("captureButton");
const stopCameraButton = document.getElementById("stopCameraButton");

const capturedSection = document.getElementById("capturedSection");
const capturedImage = document.getElementById("capturedImage");

const retakeButton = document.getElementById("retakeButton");
const continueButton = document.getElementById("continueButton");

const documentFile = document.getElementById("documentFile");
const fileName = document.getElementById("fileName");
const captureMethod = document.getElementById("captureMethod");

let cameraStream = null;


/* Start Camera */

async function startDocumentCamera() {

    if (!cameraVideo) {
        return;
    }

    try {

        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: {
                    ideal: "environment"
                }
            },
            audio: false
        });

        cameraVideo.srcObject = cameraStream;

        cameraVideo.style.display = "block";

        if (cameraPlaceholder) {
            cameraPlaceholder.style.display = "none";
        }

        if (captureButton) {
            captureButton.disabled = false;
        }

    } catch (error) {

        console.error("Camera access error:", error);

        alert(
            "Unable to access the camera. " +
            "Please allow camera permission or choose an image file instead."
        );
    }
}


/* Stop Camera */

function stopDocumentCamera() {

    if (cameraStream) {

        cameraStream.getTracks().forEach(function(track) {
            track.stop();
        });

        cameraStream = null;
    }

    if (cameraVideo) {
        cameraVideo.srcObject = null;
    }

    if (captureButton) {
        captureButton.disabled = true;
    }
}


/* Capture Image */

function captureDocumentImage() {

    if (!cameraVideo || !cameraCanvas) {
        return;
    }

    if (!cameraStream) {
        return;
    }

    const width = cameraVideo.videoWidth;
    const height = cameraVideo.videoHeight;

    if (!width || !height) {
        alert("Camera is not ready yet. Please try again.");
        return;
    }

    cameraCanvas.width = width;
    cameraCanvas.height = height;

    const context = cameraCanvas.getContext("2d");

    context.drawImage(
        cameraVideo,
        0,
        0,
        width,
        height
    );

    const imageData = cameraCanvas.toDataURL(
        "image/jpeg",
        0.92
    );

    showCapturedDocument(
        imageData,
        "Camera"
    );

    stopDocumentCamera();
}


/* Show Captured Document */

function showCapturedDocument(imageData, method) {

    if (!capturedImage || !capturedSection) {
        return;
    }

    capturedImage.src = imageData;

    capturedSection.classList.remove("hidden");

    if (captureMethod) {
        captureMethod.textContent = method;
    }

    capturedSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


/* File Upload */

if (documentFile) {

    documentFile.addEventListener("change", function(event) {

        const file = event.target.files[0];

        if (!file) {
            return;
        }

        if (!file.type.startsWith("image/")) {

            alert("Please select an image file.");

            documentFile.value = "";

            return;
        }

        fileName.textContent = file.name;

        const reader = new FileReader();

        reader.onload = function(loadEvent) {

            showCapturedDocument(
                loadEvent.target.result,
                "File Upload"
            );

        };

        reader.readAsDataURL(file);
    });
}


/* Camera Buttons */

if (startCameraButton) {

    startCameraButton.addEventListener(
        "click",
        startDocumentCamera
    );
}


if (captureButton) {

    captureButton.addEventListener(
        "click",
        captureDocumentImage
    );
}


if (stopCameraButton) {

    stopCameraButton.addEventListener(
        "click",
        stopDocumentCamera
    );
}


/* Retake */

if (retakeButton) {

    retakeButton.addEventListener(
        "click",
        function() {

            capturedSection.classList.add("hidden");

            startDocumentCamera();

        }
    );
}


/* Continue */

if (continueButton) {

    continueButton.addEventListener(
        "click",
        function() {

            window.location.href = "/darta-entry/";

        }
    );
}


/* Stop camera when leaving page */

window.addEventListener(
    "beforeunload",
    stopDocumentCamera
);