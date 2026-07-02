import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, "");

const client = axios.create({ baseURL: API_BASE_URL });

export const apiConfig = { baseUrl: API_BASE_URL, origin: API_ORIGIN };

export async function connectSource(payload, slot = 0) {
  const response = await client.post(`/source/connect/?slot=${slot}`, payload);
  return response.data;
}

export async function connectDemo(demoIndex = 0, slot = 0) {
  const response = await client.post(`/source/connect-demo/?slot=${slot}`, { demo_index: demoIndex });
  return response.data;
}

export async function startInference(payload, slot = 0) {
  const response = await client.post(`/inference/start/?slot=${slot}`, payload);
  return response.data;
}

export async function pauseInference(slot = 0) {
  const response = await client.post(`/inference/pause/?slot=${slot}`);
  return response.data;
}

export async function resumeInference(slot = 0) {
  const response = await client.post(`/inference/resume/?slot=${slot}`);
  return response.data;
}

export async function stopInference(slot = 0) {
  const response = await client.post(`/inference/stop/?slot=${slot}`);
  return response.data;
}

export async function getResults(page = 1, pageSize = 10, slot = 0) {
  const response = await client.get("/inference/results/", {
    params: { page, page_size: pageSize, slot },
  });
  return response.data;
}

export async function saveZone(payload) {
  const response = await client.post("/zones/save/", payload);
  return response.data;
}

export async function getZones(sourceId) {
  const response = await client.get("/zones/", { params: { source_id: sourceId } });
  return response.data;
}

export async function clearZones(sourceId, zoneType) {
  const params = { source_id: sourceId };
  if (zoneType) params.zone_type = zoneType;
  const response = await client.delete("/zones/", { params });
  return response.data;
}

export async function saveSnapshot(slot = 0) {
  const response = await client.post(`/snapshot/?slot=${slot}`);
  return response.data;
}

export async function getSettings() {
  const response = await client.get("/settings/");
  return response.data;
}

export function getFrameUrl(cacheBuster, slot = 0, sourceId = null) {
  const url = new URL("/api/inference/frame/", API_ORIGIN);
  if (cacheBuster) url.searchParams.set("t", String(cacheBuster));
  url.searchParams.set("slot", String(slot));
  if (sourceId != null) url.searchParams.set("source_id", String(sourceId));
  return url.toString();
}

export function getStreamUrl(cacheBuster, slot = 0, sourceId = null) {
  const url = new URL("/api/inference/stream/", API_ORIGIN);
  if (cacheBuster) url.searchParams.set("t", String(cacheBuster));
  url.searchParams.set("slot", String(slot));
  if (sourceId != null) url.searchParams.set("source_id", String(sourceId));
  return url.toString();
}
