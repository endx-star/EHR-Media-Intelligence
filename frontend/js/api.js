const API_BASE_URL = "http://127.0.0.1:8000";

const healthButton = document.querySelector("#health-check");
const healthStatus = document.querySelector("#health-status");

healthButton.addEventListener("click", async () => {
  healthButton.disabled = true;
  healthStatus.textContent = "Checking backend…";
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    healthStatus.textContent = `Connected: ${data.status}`;
    healthStatus.className = "mt-3 text-sm text-emerald-700";
  } catch (error) {
    healthStatus.textContent = `Could not connect: ${error.message}`;
    healthStatus.className = "mt-3 text-sm text-red-700";
  } finally {
    healthButton.disabled = false;
  }
});
