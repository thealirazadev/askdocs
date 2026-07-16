(() => {
  "use strict";

  const uploadForm = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const documentsList = document.getElementById("documents-list");
  const documentsEmpty = document.getElementById("documents-empty");

  const askForm = document.getElementById("ask-form");
  const questionInput = document.getElementById("question-input");

  const answerCard = document.getElementById("answer-card");
  const answerText = document.getElementById("answer-text");
  const citationsEl = document.getElementById("citations");

  async function apiRequest(path, options = {}) {
    const response = await fetch(path, options);
    if (response.status === 204) {
      return null;
    }
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(body?.error?.message || `Request failed with status ${response.status}.`);
    }
    return body;
  }

  function renderDocuments(documents) {
    documentsList.innerHTML = "";
    documentsEmpty.hidden = documents.length > 0;
    for (const doc of documents) {
      const li = document.createElement("li");
      li.textContent = `${doc.filename} (${doc.num_chunks} chunks)`;

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.textContent = "Delete";
      deleteButton.addEventListener("click", () => onDelete(doc.id));

      li.appendChild(deleteButton);
      documentsList.appendChild(li);
    }
  }

  async function loadDocuments() {
    const body = await apiRequest("/documents");
    renderDocuments(body.documents);
  }

  async function onDelete(documentId) {
    await apiRequest(`/documents/${documentId}`, { method: "DELETE" });
    await loadDocuments();
  }

  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    await apiRequest("/documents", { method: "POST", body: formData });
    uploadForm.reset();
    await loadDocuments();
  });

  function showAnswer({ answer, citations }) {
    answerCard.hidden = false;
    answerText.textContent = answer;
    citationsEl.innerHTML = "";
    for (const citation of citations || []) {
      const chip = document.createElement("span");
      chip.textContent = `${citation.filename} #${citation.chunk_index}`;
      citationsEl.appendChild(chip);
    }
  }

  askForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = questionInput.value.trim();
    if (!question) {
      return;
    }
    const body = await apiRequest("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    showAnswer(body);
  });

  loadDocuments();
})();
