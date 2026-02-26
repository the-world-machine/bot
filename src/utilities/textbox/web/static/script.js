const textarea = document.getElementById("textbox-text");
const previewImage = document.getElementById("preview-image");
const errorBox = document.getElementById("error-box");
const timerDisplay = document.getElementById("timer-display");
const tbbFileInput = document.getElementById("tbb-file-input");
const downloadTbbButton = document.getElementById("download-tbb-button");
const downloadMediaButton = document.getElementById("download-media-button");

let lastText;
let isFetching = false;

async function updatePreview(force = false) {
  if (isFetching) return;

  const currentText = textarea.value;

  if (!force && currentText === lastText) {
    return;
  }
  isFetching = true;
  timerDisplay.innerText = "Loading...";
  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: currentText,
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.warn(
        `Server responded with status ${response.status}:`,
        errorData.error,
      );
      throw new Error(
        errorData.error || `HTTP error! status: ${response.status}`,
      );
    }

    const data = await response.json();
    previewImage.src = data.output_blob;

    const timeMs = data.took;
    timerDisplay.innerText = `Took ${timeMs.toFixed(2)}ms`;
    timerDisplay.style.opacity = "1";
    errorBox.style.display = "none";
    errorBox.textContent = "";
  } catch (error) {
    console.error("Failed to update preview:", error);
    previewImage.src = "";
    errorBox.style.display = "block";
    errorBox.textContent = `Error: ${error.message}`;
  } finally {
    isFetching = false;
    lastText = currentText;
  }
}

const previewContainer = document.getElementById("preview-container");
function scrollToPreviewTop() {
  previewContainer.scrollIntoView();
}

window.addEventListener("resize", scrollToPreviewTop);

document.addEventListener("DOMContentLoaded", () => {
  updatePreview(true);
  scrollToPreviewTop();
  textarea.readOnly = false;
});
setInterval(() => {
  updatePreview(false);
  scrollToPreviewTop();
}, 300);

tbbFileInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) {
    return;
  }

  const reader = new FileReader();

  reader.onload = (e) => {
    textarea.value = e.target.result;
    updatePreview(true);
  };

  reader.onerror = (e) => {
    console.error(`File could not be read! Err: ${e.target.error}`);
    errorBox.style.display = "block";
    errorBox.textContent = "Error reading file.";
  };

  reader.readAsText(file);
});

downloadTbbButton.addEventListener("click", () => {
  const textContent = textarea.value;
  const timestamp = Math.floor(Date.now() / 1000);
  const filename = `TWM_web_textbox_${timestamp}.tbb`;

  const blob = new Blob([textContent], { type: "text/plain" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();

  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

downloadMediaButton.addEventListener("click", () => {
  const imageDataUrl = previewImage.src;
  if (!imageDataUrl) {
    errorBox.style.display = "block";
    errorBox.textContent = "No image to download. Generate one first.";
    return;
  }

  const timestamp = Math.floor(Date.now() / 1000);

  let filename = `TWM_textbox_web_${timestamp}`;
  let fileExtension = "";
  let blobType = "";

  // Determine file extension and blob type from the data URL
  if (imageDataUrl.startsWith("data:image/png")) {
    fileExtension = ".png";
    blobType = "image/png";
  } else if (
    imageDataUrl.startsWith("data:image/jpeg") ||
    imageDataUrl.startsWith("data:image/jpg")
  ) {
    fileExtension = ".jpg";
    blobType = "image/jpeg";
  } else if (imageDataUrl.startsWith("data:image/webp")) {
    fileExtension = ".webp";
    blobType = "image/webp";
  } else if (imageDataUrl.startsWith("data:image/gif")) {
    fileExtension = ".gif";
    blobType = "image/gif";
  } else {
    // Fallback for unknown types or if the src was cleared
    fileExtension = ".bin";
    blobType = "application/octet-stream"; // Generic binary type
  }
  filename += fileExtension;

  // Decode the base64 data URL
  const base64Data = imageDataUrl.split(",")[1];
  const byteCharacters = atob(base64Data);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  const blob = new Blob([byteArray], { type: blobType });

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;

  // This is the key part that helps signal download intent more strongly
  link.setAttribute("target", "_top"); // Tries to ensure it doesn't open in a parent frame if embedded

  document.body.appendChild(link);
  link.click();

  document.body.removeChild(link);
  URL.revokeObjectURL(url);
});
