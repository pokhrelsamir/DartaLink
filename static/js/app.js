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

/* =========================================================
   DARTALINK MANUAL DARTA ENTRY
   September 1, 2026
   ========================================================= */

const dartaEntryForm =
    document.getElementById("dartaEntryForm");

const senderInput =
    document.getElementById("sender");

const subjectInput =
    document.getElementById("subject");

const referenceInput =
    document.getElementById("referenceNumber");

const dateInput =
    document.getElementById("letterDate");

const urgencyInput =
    document.getElementById("urgency");

const branchInput =
    document.getElementById("receivingBranch");


const previewSender =
    document.getElementById("previewSender");

const previewSubject =
    document.getElementById("previewSubject");

const previewReference =
    document.getElementById("previewReference");

const previewDate =
    document.getElementById("previewDate");

const previewUrgency =
    document.getElementById("previewUrgency");

const previewBranch =
    document.getElementById("previewBranch");


/* Update Preview */

function updateDartaPreview() {

    if (!dartaEntryForm) {
        return;
    }


    if (previewSender) {
        previewSender.textContent =
            senderInput.value.trim() || "—";
    }


    if (previewSubject) {
        previewSubject.textContent =
            subjectInput.value.trim() || "—";
    }


    if (previewReference) {
        previewReference.textContent =
            referenceInput.value.trim() || "—";
    }


    if (previewDate) {

        if (dateInput.value) {

            const date =
                new Date(
                    dateInput.value + "T00:00:00"
                );

            previewDate.textContent =
                date.toLocaleDateString(
                    "en-GB",
                    {
                        day: "2-digit",
                        month: "short",
                        year: "numeric"
                    }
                );

        } else {

            previewDate.textContent = "—";

        }
    }


    if (previewUrgency) {

        if (urgencyInput.value) {

            previewUrgency.textContent =
                urgencyInput.options[
                    urgencyInput.selectedIndex
                ].text;

        } else {

            previewUrgency.textContent = "—";

        }
    }


    if (previewBranch) {

        if (branchInput.value) {

            previewBranch.textContent =
                branchInput.options[
                    branchInput.selectedIndex
                ].text;

        } else {

            previewBranch.textContent = "—";

        }
    }
}


/* Live Preview Listeners */

[
    senderInput,
    subjectInput,
    referenceInput,
    dateInput,
    urgencyInput,
    branchInput
].forEach(function(element) {

    if (element) {

        element.addEventListener(
            "input",
            updateDartaPreview
        );

        element.addEventListener(
            "change",
            updateDartaPreview
        );
    }
});


/* Validation */

function validateDartaForm() {

    if (!dartaEntryForm) {
        return false;
    }


    const requiredFields = [
        senderInput,
        subjectInput,
        dateInput,
        urgencyInput,
        branchInput
    ];


    let valid = true;


    requiredFields.forEach(function(field) {

        if (!field) {
            return;
        }


        const wrapper =
            field.closest(".darta-field");


        if (!field.value.trim()) {

            valid = false;

            if (wrapper) {
                wrapper.classList.add(
                    "validation-error"
                );
            }

        } else {

            if (wrapper) {
                wrapper.classList.remove(
                    "validation-error"
                );
            }
        }
    });


    if (!valid) {

        alert(
            "Please complete all required Darta fields."
        );

    }


    return valid;
}


/* Form Submit */

if (dartaEntryForm) {

    dartaEntryForm.addEventListener(
        "submit",
        function(event) {

            event.preventDefault();


            if (!validateDartaForm()) {
                return;
            }


            alert(
                "Darta information is ready for review."
            );

        }
    );
}


/* Save Draft */

const saveDraftButton =
    document.getElementById(
        "saveDraftButton"
    );


if (saveDraftButton) {

    saveDraftButton.addEventListener(
        "click",
        function() {

            updateDartaPreview();

            alert(
                "Draft preview prepared. " +
                "Database saving will be connected in the backend phase."
            );

        }
    );
}


/* Cancel */

const cancelDartaButton =
    document.getElementById(
        "cancelDartaButton"
    );


if (cancelDartaButton) {

    cancelDartaButton.addEventListener(
        "click",
        function() {

            window.location.href = "/";

        }
    );
}


/* Initial Preview */

updateDartaPreview();

/* =========================================================
   DARTALINK - CHALANI / OUTWARD DISPATCH
   September 2, 2026
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const chalaniForm = document.getElementById("chalaniForm");

    if (!chalaniForm) {
        return;
    }

    const dispatchDate = document.getElementById("dispatchDate");
    const recipient = document.getElementById("recipient");
    const subject = document.getElementById("subject");
    const priority = document.getElementById("priority");

    const previewDate = document.getElementById("previewDate");
    const previewRecipient = document.getElementById("previewRecipient");
    const previewSubject = document.getElementById("previewSubject");
    const previewPriority = document.getElementById("previewPriority");

    const chalaniNumber = document.getElementById("chalaniNumber");
    const previewChalaniNumber = document.getElementById(
        "previewChalaniNumber"
    );

    const attachmentInput = document.getElementById(
        "documentAttachment"
    );

    const chooseAttachment = document.getElementById(
        "chooseAttachment"
    );

    const attachmentZone = document.getElementById(
        "attachmentZone"
    );

    const attachmentPreview = document.getElementById(
        "attachmentPreview"
    );

    const attachmentName = document.getElementById(
        "attachmentName"
    );

    const attachmentSize = document.getElementById(
        "attachmentSize"
    );

    const removeAttachment = document.getElementById(
        "removeAttachment"
    );

    const saveDraft = document.getElementById(
        "saveChalaniDraft"
    );

    const cancelButton = document.getElementById(
        "cancelChalani"
    );


    /* -----------------------------------------
       Auto-numbering prototype
       ----------------------------------------- */

    function generateChalaniNumber() {

        const randomNumber = Math.floor(
            1000 + Math.random() * 9000
        );

        const number = "CH-2083-" + randomNumber;

        chalaniNumber.textContent = number;
        previewChalaniNumber.textContent = number;
    }

    generateChalaniNumber();


    /* -----------------------------------------
       Default dispatch date
       ----------------------------------------- */

    if (dispatchDate) {

        const today = new Date();

        const year = today.getFullYear();
        const month = String(
            today.getMonth() + 1
        ).padStart(2, "0");

        const day = String(
            today.getDate()
        ).padStart(2, "0");

        dispatchDate.value =
            `${year}-${month}-${day}`;

        updateDatePreview();
    }


    /* -----------------------------------------
       Live preview
       ----------------------------------------- */

    function updateDatePreview() {

        if (!dispatchDate.value) {
            previewDate.textContent = "—";
            return;
        }

        const date = new Date(
            dispatchDate.value + "T00:00:00"
        );

        previewDate.textContent =
            date.toLocaleDateString(
                "en-GB",
                {
                    day: "2-digit",
                    month: "short",
                    year: "numeric"
                }
            );
    }


    function updateRecipientPreview() {

        const value =
            recipient.value.trim();

        previewRecipient.textContent =
            value || "—";
    }


    function updateSubjectPreview() {

        const value =
            subject.value.trim();

        previewSubject.textContent =
            value || "—";
    }


    function updatePriorityPreview() {

        const value =
            priority.value;

        previewPriority.textContent =
            value || "—";
    }


    dispatchDate.addEventListener(
        "change",
        updateDatePreview
    );

    recipient.addEventListener(
        "input",
        updateRecipientPreview
    );

    subject.addEventListener(
        "input",
        updateSubjectPreview
    );

    priority.addEventListener(
        "change",
        updatePriorityPreview
    );


    /* -----------------------------------------
       File attachment
       ----------------------------------------- */

    chooseAttachment.addEventListener(
        "click",
        function () {
            attachmentInput.click();
        }
    );


    attachmentInput.addEventListener(
        "change",
        function () {

            const file =
                attachmentInput.files[0];

            if (!file) {
                return;
            }

            processAttachment(file);
        }
    );


    function processAttachment(file) {

        const allowedTypes = [
            "application/pdf",
            "image/jpeg",
            "image/png"
        ];

        const maxSize =
            10 * 1024 * 1024;

        if (!allowedTypes.includes(file.type)) {

            alert(
                "Please select a PDF, JPG or PNG file."
            );

            attachmentInput.value = "";
            return;
        }


        if (file.size > maxSize) {

            alert(
                "The selected file is larger than 10 MB."
            );

            attachmentInput.value = "";
            return;
        }


        attachmentName.textContent =
            file.name;

        attachmentSize.textContent =
            formatFileSize(file.size);

        attachmentPreview.hidden = false;
        attachmentZone.style.display = "none";
    }


    function formatFileSize(bytes) {

        if (bytes === 0) {
            return "0 KB";
        }

        const kilobytes =
            bytes / 1024;

        if (kilobytes < 1024) {
            return (
                kilobytes.toFixed(1) +
                " KB"
            );
        }

        return (
            (kilobytes / 1024).toFixed(1) +
            " MB"
        );
    }


    removeAttachment.addEventListener(
        "click",
        function () {

            attachmentInput.value = "";

            attachmentPreview.hidden = true;
            attachmentZone.style.display = "";
        }
    );


    /* -----------------------------------------
       Drag and drop
       ----------------------------------------- */

    attachmentZone.addEventListener(
        "dragover",
        function (event) {

            event.preventDefault();

            attachmentZone.classList.add(
                "drag-active"
            );
        }
    );


    attachmentZone.addEventListener(
        "dragleave",
        function () {

            attachmentZone.classList.remove(
                "drag-active"
            );
        }
    );


    attachmentZone.addEventListener(
        "drop",
        function (event) {

            event.preventDefault();

            attachmentZone.classList.remove(
                "drag-active"
            );

            const file =
                event.dataTransfer.files[0];

            if (!file) {
                return;
            }

            processAttachment(file);
        }
    );


    /* -----------------------------------------
       Save draft
       ----------------------------------------- */

    saveDraft.addEventListener(
        "click",
        function () {

            const recipientValue =
                recipient.value.trim();

            if (!recipientValue) {

                alert(
                    "Enter at least the recipient before saving the draft."
                );

                recipient.focus();
                return;
            }

            alert(
                "Chalani draft saved locally for this UI prototype."
            );
        }
    );


    /* -----------------------------------------
       Cancel
       ----------------------------------------- */

    cancelButton.addEventListener(
        "click",
        function () {

            const confirmed =
                confirm(
                    "Discard the current Chalani entry?"
                );

            if (confirmed) {
                window.location.href =
                    "/portal/";
            }
        }
    );


    /* -----------------------------------------
       Register & Dispatch
       ----------------------------------------- */

    chalaniForm.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();

            if (!chalaniForm.checkValidity()) {

                chalaniForm.reportValidity();
                return;
            }

            const fileSelected =
                attachmentInput.files.length > 0;

            if (!fileSelected) {

                const proceed =
                    confirm(
                        "No document attachment has been selected. Continue with registration?"
                    );

                if (!proceed) {
                    return;
                }
            }

            alert(
                "Chalani " +
                chalaniNumber.textContent +
                " is ready for registration and dispatch."
            );
        }
    );


    /* -----------------------------------------
       Initial preview
       ----------------------------------------- */

    updateRecipientPreview();
    updateSubjectPreview();
    updatePriorityPreview();

});

/* =========================================================
   DARTALINK - FRONTEND VALIDATION & IMAGE PREVIEW
   September 3, 2026
   ========================================================= */


/* =========================================================
   DARTA - IMAGE PREVIEW & METADATA VALIDATION
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const dartaForm = document.getElementById("dartaEntryForm");

    if (!dartaForm) {
        return;
    }

    /* -----------------------------------------
       Optional document image input
       ----------------------------------------- */

    const dartaDocumentInput =
        document.getElementById("documentPhoto");

    const dartaImagePreview =
        document.getElementById("photoPreview");

    const dartaCaptureStatus =
        document.getElementById("captureStatus");


    if (dartaDocumentInput) {

        dartaDocumentInput.addEventListener("change", function () {

            const file = this.files[0];

            if (!file) {
                return;
            }

            /* Validate image type */

            if (!file.type.startsWith("image/")) {

                alert(
                    "Please select a valid image file."
                );

                this.value = "";
                return;
            }


            /* Validate file size */

            const maxSize =
                10 * 1024 * 1024;

            if (file.size > maxSize) {

                alert(
                    "The selected image must be smaller than 10 MB."
                );

                this.value = "";
                return;
            }


            /* Preview image */

            if (dartaImagePreview) {

                const reader =
                    new FileReader();

                reader.onload = function (event) {

                    dartaImagePreview.src =
                        event.target.result;

                    dartaImagePreview.classList.remove(
                        "hidden"
                    );

                };

                reader.readAsDataURL(file);
            }


            if (dartaCaptureStatus) {

                dartaCaptureStatus.textContent =
                    `Photo selected: ${file.name}`;

            }

        });

    }


    /* -----------------------------------------
       Darta metadata validation
       ----------------------------------------- */

    function validateDartaMetadata() {

        const sender =
            document.getElementById("sender");

        const subject =
            document.getElementById("subject");

        const reference =
            document.getElementById("referenceNumber");

        const letterDate =
            document.getElementById("letterDate");

        const urgency =
            document.getElementById("urgency");

        const branch =
            document.getElementById("receivingBranch");


        const fields = [
            {
                element: sender,
                message: "Please enter the sender name."
            },
            {
                element: subject,
                message: "Please enter the document subject."
            },
            {
                element: letterDate,
                message: "Please select the letter date."
            },
            {
                element: urgency,
                message: "Please select the urgency level."
            },
            {
                element: branch,
                message: "Please select the receiving branch."
            }
        ];


        for (const field of fields) {

            if (
                !field.element ||
                !field.element.value.trim()
            ) {

                alert(field.message);

                if (field.element) {
                    field.element.focus();
                }

                return false;
            }

        }


        /* Sender length */

        if (sender.value.trim().length < 2) {

            alert(
                "Sender name must contain at least 2 characters."
            );

            sender.focus();
            return false;
        }


        /* Subject length */

        if (subject.value.trim().length < 3) {

            alert(
                "Subject must contain at least 3 characters."
            );

            subject.focus();
            return false;
        }


        /* Reference number validation */

        if (reference && reference.value.trim()) {

            const referencePattern =
                /^[A-Za-z0-9\/._-]+$/;

            if (!referencePattern.test(
                reference.value.trim()
            )) {

                alert(
                    "Reference number contains invalid characters."
                );

                reference.focus();
                return false;
            }

        }


        return true;
    }


    /* -----------------------------------------
       Darta form submission
       ----------------------------------------- */

    dartaForm.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();


            if (!validateDartaMetadata()) {
                return;
            }


            updateDartaPreview();


            alert(
                "Darta information has passed frontend validation and is ready for the next workflow step."
            );

        }
    );

});


/* =========================================================
   CHALANI - IMAGE PREVIEW & METADATA VALIDATION
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const chalaniForm =
        document.getElementById("chalaniForm");

    if (!chalaniForm) {
        return;
    }


    const attachmentInput =
        document.getElementById("documentAttachment");

    const attachmentPreview =
        document.getElementById("attachmentPreview");

    const attachmentName =
        document.getElementById("attachmentName");

    const attachmentSize =
        document.getElementById("attachmentSize");

    const attachmentZone =
        document.getElementById("attachmentZone");


    /* -----------------------------------------
       Image preview for attachments
       ----------------------------------------- */

    function previewChalaniAttachment(file) {

        if (!file) {
            return;
        }


        /* Only preview images */

        if (!file.type.startsWith("image/")) {
            return;
        }


        const reader =
            new FileReader();


        reader.onload =
            function (event) {

                if (!attachmentPreview) {
                    return;
                }


                /*
                 * If the existing attachment preview
                 * contains an image element, use it.
                 */

                const previewImage =
                    attachmentPreview.querySelector(
                        "img"
                    );


                if (previewImage) {

                    previewImage.src =
                        event.target.result;

                    previewImage.style.display =
                        "block";

                }

            };


        reader.readAsDataURL(file);
    }


    /* -----------------------------------------
       Attachment validation
       ----------------------------------------- */

    function validateChalaniAttachment() {

        if (!attachmentInput) {
            return true;
        }


        const file =
            attachmentInput.files[0];


        if (!file) {
            return true;
        }


        const allowedTypes = [
            "application/pdf",
            "image/jpeg",
            "image/png"
        ];


        const maxSize =
            10 * 1024 * 1024;


        if (!allowedTypes.includes(file.type)) {

            alert(
                "Only PDF, JPG and PNG files are allowed."
            );

            attachmentInput.value = "";

            if (attachmentPreview) {
                attachmentPreview.hidden = true;
            }

            if (attachmentZone) {
                attachmentZone.style.display = "";
            }

            return false;
        }


        if (file.size > maxSize) {

            alert(
                "The attachment must be smaller than 10 MB."
            );

            attachmentInput.value = "";

            if (attachmentPreview) {
                attachmentPreview.hidden = true;
            }

            if (attachmentZone) {
                attachmentZone.style.display = "";
            }

            return false;
        }


        return true;
    }


    /* -----------------------------------------
       File selection
       ----------------------------------------- */

    if (attachmentInput) {

        attachmentInput.addEventListener(
            "change",
            function () {

                const file =
                    this.files[0];


                if (!file) {
                    return;
                }


                if (!validateChalaniAttachment()) {
                    return;
                }


                /* Show image preview */

                previewChalaniAttachment(file);


                if (attachmentName) {

                    attachmentName.textContent =
                        file.name;

                }


                if (attachmentSize) {

                    attachmentSize.textContent =
                        formatFileSize(
                            file.size
                        );

                }

            }
        );

    }


    /* -----------------------------------------
       Chalani metadata validation
       ----------------------------------------- */

    function validateChalaniMetadata() {

        const recipient =
            document.getElementById("recipient");

        const subject =
            document.getElementById("subject");

        const dispatchDate =
            document.getElementById("dispatchDate");

        const priority =
            document.getElementById("priority");


        const fields = [
            {
                element: recipient,
                message:
                    "Please enter the recipient."
            },
            {
                element: subject,
                message:
                    "Please enter the document subject."
            },
            {
                element: dispatchDate,
                message:
                    "Please select the dispatch date."
            },
            {
                element: priority,
                message:
                    "Please select the priority."
            }
        ];


        for (const field of fields) {

            if (
                !field.element ||
                !field.element.value.trim()
            ) {

                alert(field.message);

                if (field.element) {
                    field.element.focus();
                }

                return false;
            }

        }


        if (recipient.value.trim().length < 2) {

            alert(
                "Recipient name must contain at least 2 characters."
            );

            recipient.focus();
            return false;
        }


        if (subject.value.trim().length < 3) {

            alert(
                "Subject must contain at least 3 characters."
            );

            subject.focus();
            return false;
        }


        return true;
    }


    /* -----------------------------------------
       Replace submit validation
       ----------------------------------------- */

    chalaniForm.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();


            if (!validateChalaniMetadata()) {
                return;
            }


            if (!validateChalaniAttachment()) {
                return;
            }


            alert(
                "Chalani information and attachment have passed frontend validation and are ready for registration."
            );

        }
    );

});