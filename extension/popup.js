"use strict";

const DEFAULT_API = "http://127.0.0.1:8000";
const apiInput = document.querySelector("#api-base");
const health = document.querySelector("#health");
const message = document.querySelector("#message");
const results = document.querySelector("#results");
const checkButton = document.querySelector("#check-api");
const analyzeButton = document.querySelector("#analyze-tab");
const fileInput = document.querySelector("#image-file");

function apiBase() {
  const value = (apiInput.value || DEFAULT_API).trim().replace(/\/+$/, "");
  return value || DEFAULT_API;
}

function rememberApiBase() {
  const value = apiBase();
  if (globalThis.chrome && chrome.storage && chrome.storage.local) {
    chrome.storage.local.set({ apiBase: value });
  }
}

function setBusy(busy) {
  checkButton.disabled = busy;
  analyzeButton.disabled = busy;
  fileInput.disabled = busy;
}

function showError(error) {
  message.textContent = error && error.message ? error.message : "Analysis failed.";
  results.replaceChildren();
}

async function readJson(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (_error) {
    return { detail: text };
  }
}

async function checkApi() {
  rememberApiBase();
  health.textContent = "Checking API…";
  health.className = "health";
  const response = await fetch(`${apiBase()}/health`);
  const body = await readJson(response);
  if (!response.ok) {
    throw new Error(`API check failed (${response.status}).`);
  }
  health.textContent = `API running · ${body && body.service ? body.service : "geometa"} ${body && body.version ? body.version : ""}`.trim();
  health.className = "health health-ok";
}

async function analyzeBlob(blob, filename) {
  rememberApiBase();
  const form = new FormData();
  form.append("file", blob, filename);
  const response = await fetch(`${apiBase()}/v1/analyses`, {
    method: "POST",
    body: form,
  });
  const body = await readJson(response);
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : `API returned ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  message.textContent = "";
  renderAnalysis(results, body);
  return body;
}

async function analyzeVisibleTab() {
  if (!globalThis.chrome || !chrome.tabs || !chrome.tabs.captureVisibleTab) {
    throw new Error("Tab capture is only available in the Chrome extension popup.");
  }
  const dataUrl = await chrome.tabs.captureVisibleTab({ format: "png" });
  const response = await fetch(dataUrl);
  const blob = await response.blob();
  await analyzeBlob(blob, "tab.png");
}

checkButton.addEventListener("click", async () => {
  setBusy(true);
  try {
    await checkApi();
  } catch (error) {
    health.textContent = error.message || "API unreachable";
    health.className = "health health-down";
  } finally {
    setBusy(false);
  }
});

analyzeButton.addEventListener("click", async () => {
  setBusy(true);
  message.textContent = "Analyzing this tab…";
  try {
    await analyzeVisibleTab();
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
});

fileInput.addEventListener("change", async () => {
  const file = fileInput.files && fileInput.files[0];
  fileInput.value = "";
  if (!file) return;
  setBusy(true);
  message.textContent = "Analyzing image…";
  try {
    await analyzeBlob(file, file.name || "upload.png");
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
});

if (globalThis.chrome && chrome.storage && chrome.storage.local) {
  chrome.storage.local.get(["apiBase"], (stored) => {
    if (stored && stored.apiBase) apiInput.value = stored.apiBase;
  });
}
