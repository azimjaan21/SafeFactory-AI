import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, "");

const client = axios.create({
  baseURL: API_BASE_URL,
});

export const apiConfig = {
  baseUrl: API_BASE_URL,
  origin: API_ORIGIN,
};

export async function connectSource(payload) {
  const response = await client.post("/source/connect/", payload);
  return response.data;
}

export async function startInference(payload) {
  const response = await client.post("/inference/start/", payload);
  return response.data;
}

export async function pauseInference() {
  const response = await client.post("/inference/pause/");
  return response.data;
}

export async function resumeInference() {
  const response = await client.post("/inference/resume/");
  return response.data;
}

export async function stopInference() {
  const response = await client.post("/inference/stop/");
  return response.data;
}

export async function getResults(page = 1, pageSize = 10) {
  const response = await client.get("/inference/results/", {
    params: {
      page,
      page_size: pageSize,
    },
  });
  return response.data;
}

export async function saveZone(payload) {
  const response = await client.post("/zones/save/", payload);
  return response.data;
}

export async function getZones(sourceId) {
  const response = await client.get("/zones/", {
    params: { source_id: sourceId },
  });
  return response.data;
}

export async function saveSnapshot() {
  const response = await client.post("/snapshot/");
  return response.data;
}

export async function getSettings() {
  const response = await client.get("/settings/");
  return response.data;
}

export function getFrameUrl(cacheBuster) {
  const url = new URL("/api/inference/frame/", API_ORIGIN);
  if (cacheBuster) {
    url.searchParams.set("t", String(cacheBuster));
  }
  return url.toString();
}

export function getStreamUrl(cacheBuster) {
  const url = new URL("/api/inference/stream/", API_ORIGIN);
  if (cacheBuster) {
    url.searchParams.set("t", String(cacheBuster));
  }
  return url.toString();
}
