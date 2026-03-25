// --- CONFIGURATION ---
// Base URL for the API Gateway
const API_BASE_URL = "YOUR BASE URL";
// ---------------------

// State
let currentTool = null;
let selectedFiles = [];

// DOM Elements
const views = {
  tools: document.getElementById("tools-view"),
  active: document.getElementById("active-tool-view"),
  result: document.getElementById("result-view"),
};

const elements = {
  activeTitle: document.getElementById("active-tool-title"),
  backBtn: document.getElementById("back-btn"),
  dropZone: document.getElementById("drop-zone"),
  fileInput: document.getElementById("file-input"),
  fileList: document.getElementById("file-list"),
  fileNoun: document.getElementById("file-noun"),
  optionsArea: document.getElementById("options-area"),
  actionFooter: document.getElementById("action-footer"),
  processBtn: document.getElementById("process-btn"),
  closeBtn: document.getElementById("close-btn"),
  downloadLinks: document.getElementById("download-links"),
  resultMessage: document.getElementById("result-message"),
  toast: document.getElementById("toast"),
  toastMsg: document.getElementById("toast-msg"),
};

const optionGroups = {
  "password-protect": document.getElementById("opt-password"),
  remove: document.getElementById("opt-remove"),
  split: document.getElementById("opt-split"),
};

// Tool Definitions
const toolsInfo = {
  compress: {
    title: "Compress PDF",
    multiple: false,
    endpoint: "/compress-pdf",
  },
  merge: { title: "Merge PDFs", multiple: true, endpoint: "/merge-pdf" },
  "password-protect": {
    title: "Password Protect PDF",
    multiple: false,
    endpoint: "/password-protect-pdf",
  },
  remove: {
    title: "Remove Pages",
    multiple: false,
    endpoint: "/remove-pages-from-pdf",
  },
  split: { title: "Split PDF", multiple: false, endpoint: "/split-pdf" },
};

// --- Initialization & Event Listeners ---

document.querySelectorAll(".tool-card").forEach((card) => {
  card.addEventListener("click", () => {
    const action = card.dataset.action;
    openTool(action);
  });
});

elements.backBtn.addEventListener("click", () => switchView("tools"));
elements.closeBtn.addEventListener("click", () => switchView("tools"));

// Drag & Drop
elements.dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  elements.dropZone.classList.add("drag-over");
});
elements.dropZone.addEventListener("dragleave", () =>
  elements.dropZone.classList.remove("drag-over"),
);
elements.dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  elements.dropZone.classList.remove("drag-over");
  if (e.dataTransfer.files.length) {
    handleFiles(e.dataTransfer.files);
  }
});

// File Input
elements.fileInput.addEventListener("change", (e) => {
  if (e.target.files.length) {
    handleFiles(e.target.files);
  }
  // reset so same file can be chosen again
  e.target.value = "";
});

// Process
elements.processBtn.addEventListener("click", processFiles);

// --- Core Helper Functions ---

function switchView(viewName) {
  Object.values(views).forEach((v) => v.classList.remove("active-view"));
  views[viewName].classList.add("active-view");

  if (viewName === "tools") {
    currentTool = null;
    selectedFiles = [];
    updateFileUI();
    hideAllOptions();
    elements.processBtn.classList.remove("loading");
    elements.processBtn.disabled = false;
  }
}

function openTool(action) {
  currentTool = action;
  const info = toolsInfo[action];

  elements.activeTitle.textContent = info.title;
  elements.fileInput.multiple = info.multiple;
  elements.fileNoun.textContent = info.multiple ? "PDF files" : "a PDF file";

  selectedFiles = [];
  updateFileUI();

  hideAllOptions();
  if (optionGroups[action]) {
    elements.optionsArea.style.display = "block";
    optionGroups[action].style.display = action === "remove" ? "grid" : "flex";
  } else {
    elements.optionsArea.style.display = "none";
  }

  switchView("active");
}

function hideAllOptions() {
  Object.values(optionGroups).forEach((el) => {
    if (el) el.style.display = "none";
  });
  // Clear inputs
  document
    .querySelectorAll(".options-area input")
    .forEach((inp) => (inp.value = ""));
}

function handleFiles(files) {
  const info = toolsInfo[currentTool];
  const newFiles = Array.from(files).filter(
    (f) => f.type === "application/pdf",
  );

  if (newFiles.length === 0) {
    showToast("Please select valid PDF files.");
    return;
  }

  if (!info.multiple) {
    selectedFiles = [newFiles[0]];
  } else {
    selectedFiles = [...selectedFiles, ...newFiles];
  }

  updateFileUI();
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  updateFileUI();
}

function updateFileUI() {
  elements.fileList.innerHTML = "";

  selectedFiles.forEach((f, i) => {
    const item = document.createElement("div");
    item.className = "file-item";

    const sizeMB = (f.size / (1024 * 1024)).toFixed(2);

    item.innerHTML = `
            <div class="file-info">
                <i class="fa-solid fa-file-pdf"></i>
                <span class="file-name" title="${f.name}">${f.name}</span>
                <span class="file-size">(${sizeMB} MB)</span>
            </div>
            <button class="file-remove" onclick="removeFile(${i})" title="Remove file"><i class="fa-solid fa-xmark"></i></button>
        `;
    elements.fileList.appendChild(item);
  });

  if (selectedFiles.length > 0) {
    elements.actionFooter.style.display = "block";
    // if merge, requires > 1
    if (currentTool === "merge" && selectedFiles.length < 2) {
      elements.processBtn.disabled = true;
    } else {
      elements.processBtn.disabled = false;
    }
  } else {
    elements.actionFooter.style.display = "none";
  }
}

function showToast(msg) {
  elements.toastMsg.textContent = msg;
  elements.toast.classList.add("show");
  setTimeout(() => {
    elements.toast.classList.remove("show");
  }, 4000);
}

// --- API Interactions ---

async function getPresignedUrls(filenames) {
  const res = await fetch(`${API_BASE_URL}/generate-presigned-urls`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filenames }),
  });
  if (!res.ok) throw new Error("Failed to get presigned URLs");
  return await res.json();
}

async function uploadFileToS3(url, file) {
  const res = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/pdf" },
    body: file,
  });
  if (!res.ok) throw new Error(`Failed to upload ${file.name}`);
}

async function callOperation(endpoint, payload) {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data || "Operation failed");
  }
  return data;
}

// --- Main Processing Logic ---

async function processFiles() {
  // Validate extra inputs
  let extraPayload = {};
  if (currentTool === "password-protect") {
    const pass = document.getElementById("password-input").value;
    if (!pass) return showToast("Password is required.");
    extraPayload = { password: pass };
  } else if (currentTool === "remove") {
    const from = parseInt(document.getElementById("from-page").value);
    const to = parseInt(document.getElementById("to-page").value);
    if (!from || !to || from < 1 || to < from)
      return showToast("Invalid page range.");
    extraPayload = { from_page: from, to_page: to };
  } else if (currentTool === "split") {
    const splitAfter = parseInt(document.getElementById("split-after").value);
    if (!splitAfter || splitAfter < 1) return showToast("Invalid split page.");
    extraPayload = { split_after_page_number: splitAfter };
  }

  elements.processBtn.classList.add("loading");
  elements.processBtn.disabled = true;

  try {
    // 1. Get Presigned URLs
    const filenames = selectedFiles.map((f) => f.name);
    const urlsData = await getPresignedUrls(filenames);

    // 2. Upload Files to S3
    const keys = [];
    for (const file of selectedFiles) {
      const data = urlsData[file.name];
      await uploadFileToS3(data.upload_url, file);
      keys.push(data.key);
    }

    // 3. Prepare Operation Payload
    let payload = { ...extraPayload };
    if (currentTool === "merge") {
      payload.keys = keys;
    } else {
      payload.key = keys[0];
    }

    // 4. Call Operation API
    const endpoint = toolsInfo[currentTool].endpoint;
    const result = await callOperation(endpoint, payload);

    // 5. Show Success View
    showResult(result);
  } catch (error) {
    console.error(error);
    showToast(error.message || "An unexpected error occurred.");
  } finally {
    elements.processBtn.classList.remove("loading");
    elements.processBtn.disabled = false;
  }
}

function showResult(result) {
  elements.downloadLinks.innerHTML = "";

  if (result.part1 && result.part2) {
    // Split result
    elements.resultMessage.textContent =
      "Your document has been split into two parts.";
    createDownloadBtn("Download Part 1", result.part1.url);
    createDownloadBtn("Download Part 2", result.part2.url);
  } else {
    // Standard result
    let msg = "Your file is ready to download.";
    if (result.compressed_size_bytes) {
      const saved = (
        (1 - result.compressed_size_bytes / result.original_size_bytes) *
        100
      ).toFixed(1);
      msg = `Great! File size was reduced by ${saved}%.`;
    }
    elements.resultMessage.textContent = msg;
    createDownloadBtn("Download PDF", result.url);
  }

  switchView("result");
}

function createDownloadBtn(text, url) {
  const a = document.createElement("a");
  a.href = url;
  a.className = "download-link";
  a.target = "_blank";
  a.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> ${text}`;
  elements.downloadLinks.appendChild(a);
}
