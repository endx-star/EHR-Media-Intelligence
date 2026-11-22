
const API_BASE_URL = "http://127.0.0.1:8000";

// DOM elements
const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#search-query");
const searchButton = document.querySelector("#search-button");

const resourceType = document.querySelector("#resource-type");
const dateFrom = document.querySelector("#date-from");
const dateTo = document.querySelector("#date-to");
const topK = document.querySelector("#top-k");

const resultsContainer = document.querySelector("#results-container");
const resultsDescription = document.querySelector("#results-description");
const searchTime = document.querySelector("#search-time");

const loadingState = document.querySelector("#loading-state");
const errorState = document.querySelector("#error-state");
const emptyState = document.querySelector("#empty-state");

const connectionIndicator = document.querySelector(
  "#connection-indicator"
);
const connectionText = document.querySelector("#connection-text");

const detailModal = document.querySelector("#detail-modal");
const modalTitle = document.querySelector("#modal-title");
const modalContent = document.querySelector("#modal-content");
const closeModalButton = document.querySelector("#close-modal");
let previouslyFocusedElement = null;

// Utility: safely escape text before inserting it into HTML
function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    };

    return entities[character];
  });
}


// Utility: format dates for display
function formatDate(value) {
  if (!value) return "Date unavailable";

  const parsed = new Date(`${value}T00:00:00`);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric"
  }).format(parsed);
}


// Backend connection check
async function checkBackendConnection() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    connectionIndicator.className =
      "h-2.5 w-2.5 rounded-full bg-emerald-500";

    connectionText.textContent =
      `Backend connected: ${data.status}`;

  } catch (error) {
    connectionIndicator.className =
      "h-2.5 w-2.5 rounded-full bg-red-500";

    connectionText.textContent = "Backend unavailable";

    console.error("Backend connection failed:", error);
  }
}


// Show and hide UI states
function showLoading() {
  loadingState.classList.remove("hidden");
  emptyState.classList.add("hidden");
  errorState.classList.add("hidden");
  resultsContainer.classList.add("hidden");

  searchButton.disabled = true;
  searchButton.textContent = "Searching...";
}


function hideLoading() {
  loadingState.classList.add("hidden");

  searchButton.disabled = false;
  searchButton.textContent = "Search records";
}


function showError(message) {
  errorState.textContent = message;
  errorState.classList.remove("hidden");

  resultsContainer.classList.add("hidden");
  emptyState.classList.add("hidden");
}


function showEmptyResults() {
  emptyState.classList.remove("hidden");
  emptyState.innerHTML = `
    <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
      <svg class="h-6 w-6 text-slate-500" fill="none"
        stroke="currentColor" viewBox="0 0 24 24">
        <circle cx="11" cy="11" r="7" stroke-width="2"/>
        <path d="m16 16 4 4" stroke-width="2"
          stroke-linecap="round"/>
      </svg>
    </div>

    <h4 class="mt-4 font-semibold text-slate-800">
      No matching records found
    </h4>

    <p class="mt-1 text-sm text-slate-500">
      Try changing your search query or removing some filters.
    </p>
  `;

  resultsContainer.classList.add("hidden");
}


// Build search request
function buildSearchPayload() {
  const payload = {
    query: searchInput.value.trim(),
    top_k: Number(topK.value)
  };

  if (resourceType.value) {
    payload.resource_type = resourceType.value;
  }

  if (dateFrom.value) {
    payload.date_from = dateFrom.value;
  }

  if (dateTo.value) {
    payload.date_to = dateTo.value;
  }

  return payload;
}


// Validate date range
function validateFilters() {
  if (
    dateFrom.value &&
    dateTo.value &&
    dateFrom.value > dateTo.value
  ) {
    showError("The start date cannot be later than the end date.");
    return false;
  }

  return true;
}


// Search API request
async function searchRecords(event) {
  event.preventDefault();

  errorState.classList.add("hidden");

  if (!validateFilters()) {
    return;
  }

  const payload = buildSearchPayload();

  if (payload.query.length < 3) {
    showError("Please enter at least 3 characters to search.");
    return;
  }

  showLoading();

  try {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : `Search failed with status ${response.status}.`
      );
    }

    renderSearchResults(data);

  } catch (error) {
    console.error("Search request failed:", error);

    showError(
      error.message ||
      "Unable to search clinical records. Please try again."
    );

    resultsDescription.textContent = "Search could not be completed.";
    searchTime.textContent = "";

  } finally {
    hideLoading();
  }
}


// Render search results
function renderSearchResults(data) {
  const results = data.results || [];

  resultsDescription.textContent =
    `${data.total_results} matching record(s) found`;

  searchTime.textContent =
    `Search completed in ${Number(data.search_time_ms).toFixed(2)} ms`;

  if (results.length === 0) {
    showEmptyResults();
    return;
  }

  emptyState.classList.add("hidden");
  errorState.classList.add("hidden");
  resultsContainer.classList.remove("hidden");

  resultsContainer.innerHTML = results.map((record, index) => {
   const rawScore = Number(record.relevance_score);
   const score = Number.isFinite(rawScore)
       ? Math.round(Math.max(0, Math.min(1, rawScore)) * 100)
       : null;

    return `
      <article class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-200 hover:shadow-md">

        <div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">

          <div class="min-w-0 flex-1">

            <div class="flex flex-wrap items-center gap-2">

              <span class="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                ${escapeHTML(record.resource_type)}
              </span>

              <span class="text-xs text-slate-400">
                Result #${index + 1}
              </span>

            </div>

            <h4 class="mt-3 text-lg font-bold text-slate-900">
              ${escapeHTML(record.title)}
            </h4>

            <p class="mt-1 text-sm text-slate-600">
              ${escapeHTML(record.patient_name || "Unknown patient")}
              · MRN: ${escapeHTML(record.mrn || "Unavailable")}
            </p>

          </div>


          <div class="shrink-0 rounded-lg bg-emerald-50 px-3 py-2 text-center">

            <p class="text-xl font-bold text-emerald-700">
              ${score === null ? "N/A" : `${score}%`}
            </p>

            <p class="text-xs text-emerald-700">
              Relevance
            </p>

          </div>

        </div>


        <div class="mt-4 rounded-lg bg-slate-50 p-4">

          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Clinical content
          </p>

          <p class="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
            ${escapeHTML(record.snippet)}
          </p>

        </div>


        <div class="mt-4 flex flex-col justify-between gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-center">

          <div class="flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-500">

            <span>
              Record date: ${escapeHTML(formatDate(record.record_date))}
            </span>

            <span>
              Record ID: ${escapeHTML(record.resource_id)}
            </span>

          </div>

          <button
            type="button"
            class="view-details rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-blue-600 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-result-index="${index}"
          >
            View details
          </button>

        </div>

      </article>
    `;
  }).join("");

  // Attach detail buttons
  resultsContainer.querySelectorAll(".view-details").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.resultIndex);
      openRecordDetails(results[index]);
    });
  });
}


// Open record detail modal
function openRecordDetails(record) {
  previouslyFocusedElement = document.activeElement;
  modalTitle.textContent = record.title || "Clinical record";

  modalContent.innerHTML = `
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">

      ${detailField("Patient name", record.patient_name || "Unavailable")}
      ${detailField("MRN", record.mrn || "Unavailable")}
      ${detailField("Patient ID", record.patient_id)}
      ${detailField("Resource type", record.resource_type)}
      ${detailField("Resource ID", record.resource_id)}
      ${detailField("Record date", formatDate(record.record_date))}
      ${detailField(
        "Relevance score",
        `${Math.round(record.relevance_score * 100)}%`
      )}

    </div>

    <div>
      <h4 class="mb-2 text-sm font-semibold text-slate-700">
        Clinical record content
      </h4>

      <div class="whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm leading-relaxed text-slate-700">
        ${escapeHTML(record.snippet)}
      </div>
    </div>

    <p class="text-xs leading-relaxed text-slate-500">
      This view displays the search result snippet returned by the
      semantic search API. It does not retrieve the complete original
      FHIR resource.
    </p>
  `;

  detailModal.classList.remove("hidden");
  detailModal.classList.add("flex");

  closeModalButton.focus();
}


// Build a detail field
function detailField(label, value) {
  return `
    <div class="rounded-lg border border-slate-200 p-3">
      <p class="text-xs font-medium text-slate-500">
        ${escapeHTML(label)}
      </p>

      <p class="mt-1 break-words text-sm font-semibold text-slate-800">
        ${escapeHTML(value)}
      </p>
    </div>
  `;
}


// Close modal
function closeModal() {
  detailModal.classList.add("hidden");
  detailModal.classList.remove("flex");

  if (previouslyFocusedElement) {
    previouslyFocusedElement.focus();
    previouslyFocusedElement = null;
  }
}


closeModalButton.addEventListener("click", closeModal);

detailModal.addEventListener("click", (event) => {
  if (event.target === detailModal) {
    closeModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (detailModal.classList.contains("hidden")) {
    return;
  }

  if (event.key === "Escape") {
    closeModal();
    return;
  }

  // Keep keyboard focus inside the open modal.
  if (event.key === "Tab") {
    const focusableElements = detailModal.querySelectorAll(
      'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (!firstElement || !lastElement) {
      return;
    }

    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  }
});

// Clear filters
document.querySelector("#clear-filters").addEventListener("click", () => {
  resourceType.value = "";
  dateFrom.value = "";
  dateTo.value = "";
  topK.value = "5";

  errorState.classList.add("hidden");

  if (searchInput.value.trim().length >= 3) {
    searchForm.requestSubmit();
  }
});


// Event listeners
searchForm.addEventListener("submit", searchRecords);


// Initialize frontend
checkBackendConnection();
