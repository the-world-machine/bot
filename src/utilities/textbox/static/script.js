const textarea = document.getElementById("textbox-text");
const previewImage = document.getElementById("preview-image");
const errorBox = document.getElementById("error-box");
const timerDisplay = document.getElementById("timer-display");
const tbbFileInput = document.getElementById("tbb-file-input");
const downloadTbbButton = document.getElementById("download-tbb-button");

let lastOptions = {};
let isFetching = false;

function getOptions() {
  return textarea.innerText;
}

async function updatePreview(force = false) {
  if (isFetching) return;

  const currentOptions = getOptions();

  if (!force && currentOptions === lastOptions) {
    return;
  }
  isFetching = true;
  timerDisplay.innerText = "Loading...";
  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: currentOptions,
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.warn(
        `Server responded with status ${response.status}:`,
        errorData.error
      );
      throw new Error(
        errorData.error || `HTTP error! status: ${response.status}`
      );
    }

    const data = await response.json();
    previewImage.src = data.image_data;

    const timeMs = data.generation_time_ms;
    timerDisplay.innerText = `Took ${timeMs.toFixed(2)}ms`;
    timerDisplay.style.opacity = "1";
    errorBox.style.display = "none";
    errorBox.textContent = "";
  } catch (error) {
    console.error("Failed to update preview:", error);
    previewImage.src = "";
    errorBox.style.display = "block";
    errorBox.textContent = "Error: " + error.message;
  } finally {
    isFetching = false;
    lastOptions = currentOptions;
  }
}

const previewContainer = document.getElementById("preview-container");
function scrollToPreviewTop() {
  previewContainer.scrollIntoView();
}

window.addEventListener("resize", scrollToPreviewTop);

document.addEventListener("DOMContentLoaded", () => {
  textarea.contentEditable = true;
  updatePreview(true);
  scrollToPreviewTop();
});
setInterval(() => {
  updatePreview(false);
  scrollToPreviewTop();
}, 300);

tbbFileInput.addEventListener("change", function (event) {
  const file = event.target.files[0];
  if (!file) {
    return;
  }

  const reader = new FileReader();

  reader.onload = function (e) {
    textarea.innerText = e.target.result;
    updatePreview(true);
  };

  reader.onerror = function (e) {
    console.error("File could not be read! Code " + e.target.error.code);
    errorBox.style.display = "block";
    errorBox.textContent = "Error reading file.";
  };

  reader.readAsText(file);
});

downloadTbbButton.addEventListener("click", () => {
  const textContent = textarea.innerText;
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
