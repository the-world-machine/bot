const textarea = document.getElementById("textbox-text");
const filetypeSelect = document.getElementById("filetype-select");
const animatedCheckbox = document.getElementById("animated-checkbox");
const qualitySlider = document.getElementById("quality-slider");
const qualityValue = document.getElementById("quality-value");
const previewImage = document.getElementById("preview-image");
const errorBox = document.getElementById("error-box");
const refreshButton = document.getElementById("refresh-button");
const timerDisplay = document.getElementById("timer-display");

let lastOptions = {};
let isFetching = false;

function getOptions() {
  return {
    text: textarea.value,
    filetype: filetypeSelect.value,
    animated: animatedCheckbox.checked,
    quality: parseInt(qualitySlider.value, 10) || 100,
  };
}

async function updatePreview(force = false) {
  if (isFetching) return;

  const currentOptions = getOptions();

  if (
    !force &&
    JSON.stringify(currentOptions) === JSON.stringify(lastOptions)
  ) {
    return;
  }

  isFetching = true;
  lastOptions = currentOptions;

  timerDisplay.style.opacity = "0";

  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentOptions),
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
    timerDisplay.textContent = `Took ${timeMs.toFixed(2)}ms`;
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
  }
}
qualitySlider.addEventListener("input", () => {
  qualityValue.textContent = qualitySlider.value;
});

refreshButton.addEventListener("click", () => {
  updatePreview(true);
});

setInterval(() => updatePreview(false), 300);

document.addEventListener("DOMContentLoaded", () => updatePreview(true));
