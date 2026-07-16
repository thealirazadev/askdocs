(() => {
  "use strict";

  const API_KEY_STORAGE = "askdocs_api_key";

  const uploadForm = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const uploadButton = document.getElementById("upload-button");
  const uploadStatus = document.getElementById("upload-status");
  const uploadError = document.getElementById("upload-error");
  const documentsList = document.getElementById("documents-list");
  const documentsEmpty = document.getElementById("documents-empty");
  const documentsCard = document.getElementById("documents-card");

  const askForm = document.getElementById("ask-form");
  const questionInput = document.getElementById("question-input");
  const askButton = document.getElementById("ask-button");
  const askValidation = document.getElementById("ask-validation");

  const answerCard = document.getElementById("answer-card");
  const answerText = document.getElementById("answer-text");
  const answerError = document.getElementById("answer-error");
  const citationsWrap = document.getElementById("citations-wrap");
  const citationsEl = document.getElementById("citations");
  const citationSnippet = document.getElementById("citation-snippet");

  const apiKeyDialog = document.getElementById("api-key-dialog");
  const apiKeyForm = document.getElementById("api-key-form");
  const apiKeyInput = document.getElementById("api-key-input");

  function getApiKey() {
    return localStorage.getItem(API_KEY_STORAGE) || "";
  }

  function setApiKey(key) {
    localStorage.setItem(API_KEY_STORAGE, key);
  }

  function authHeaders() {
    const key = getApiKey();
    return key ? { "X-API-Key": key } : {};
  }

  function promptForApiKey() {
    return new Promise((resolve) => {
      if (typeof apiKeyDialog.showModal === "function") {
        apiKeyDialog.showModal();
      }
      apiKeyForm.onsubmit = (event) => {
        event.preventDefault();
        setApiKey(apiKeyInput.value.trim());
        apiKeyDialog.close();
        resolve();
      };
    });
  }

  async function apiRequest(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { ...(options.headers || {}), ...authHeaders() },
    });
    if (response.status === 401) {
      await promptForApiKey();
      const retry = await fetch(path, {
        ...options,
        headers: { ...(options.headers || {}), ...authHeaders() },
      });
      return handleResponse(retry);
    }
    return handleResponse(response);
  }

  async function handleResponse(response) {
    if (response.status === 204) {
      return null;
    }
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const message = body?.error?.message || `Request failed with status ${response.status}.`;
      const error = new Error(message);
      error.code = body?.error?.code;
      throw error;
    }
    return body;
  }

  function renderDocuments(documents) {
    documentsList.innerHTML = "";
    documentsEmpty.hidden = documents.length > 0;
    for (const doc of documents) {
      const li = document.createElement("li");

      const info = document.createElement("span");
      info.textContent = doc.filename + " ";
      const meta = document.createElement("span");
      meta.className = "doc-meta";
      meta.textContent = `${doc.num_chunks} chunks`;
      info.appendChild(meta);

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "delete-button";
      deleteButton.textContent = "Delete";
      deleteButton.addEventListener("click", () => onDelete(doc.id, deleteButton));

      li.appendChild(info);
      li.appendChild(deleteButton);
      documentsList.appendChild(li);
    }
  }

  async function loadDocuments() {
    try {
      const body = await apiRequest("/documents");
      renderDocuments(body.documents);
    } catch (error) {
      uploadError.textContent = error.message;
    }
  }

  async function onDelete(documentId, button) {
    if (!confirm("Delete this document?")) {
      return;
    }
    button.disabled = true;
    button.textContent = "Deleting...";
    try {
      await apiRequest(`/documents/${documentId}`, { method: "DELETE" });
      await loadDocuments();
    } catch (error) {
      uploadError.textContent = error.message;
      button.disabled = false;
      button.textContent = "Delete";
    }
  }

  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    uploadError.textContent = "";
    uploadStatus.textContent = "";

    const file = fileInput.files[0];
    if (!file) {
      return;
    }

    uploadButton.disabled = true;
    uploadButton.textContent = "Uploading...";
    fileInput.disabled = true;
    documentsCard.setAttribute("aria-busy", "true");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const body = await apiRequest("/documents", { method: "POST", body: formData });
      uploadStatus.textContent = `Indexed ${body.filename} - ${body.num_chunks} chunks`;
      uploadForm.reset();
      await loadDocuments();
    } catch (error) {
      uploadError.textContent = error.message;
    } finally {
      uploadButton.disabled = false;
      uploadButton.textContent = "Upload";
      fileInput.disabled = false;
      documentsCard.removeAttribute("aria-busy");
    }
  });

  function showAnswer({ answer, citations, error }) {
    answerCard.hidden = false;
    answerError.textContent = error || "";
    answerText.textContent = error ? "" : answer;
    citationsEl.innerHTML = "";
    citationSnippet.hidden = true;

    if (error || !citations || citations.length === 0) {
      citationsWrap.hidden = true;
      return;
    }

    citationsWrap.hidden = false;
    for (const citation of citations) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = `${citation.filename} #${citation.chunk_index}`;
      chip.addEventListener("click", () => {
        citationSnippet.textContent = citation.snippet;
        citationSnippet.hidden = false;
      });
      citationsEl.appendChild(chip);
    }
  }

  askForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    askValidation.textContent = "";

    const question = questionInput.value.trim();
    if (!question) {
      askValidation.textContent = "Enter a question.";
      return;
    }

    askButton.disabled = true;
    askButton.textContent = "Thinking...";
    questionInput.disabled = true;
    answerCard.setAttribute("aria-busy", "true");

    try {
      const body = await apiRequest("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      showAnswer(body);
    } catch (error) {
      showAnswer({ error: error.message });
    } finally {
      askButton.disabled = false;
      askButton.textContent = "Ask";
      questionInput.disabled = false;
      answerCard.removeAttribute("aria-busy");
    }
  });

  loadDocuments();
})();
