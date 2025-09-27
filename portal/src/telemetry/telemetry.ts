import api from "../lib/api";

type EventBase = {
  ts: number;
  type: string;
  requestId?: string;
  message?: string;
  meta?: unknown;
};

const BUFFER: EventBase[] = [];
const MAX_EVENTS = 200;

export function emit(event: EventBase) {
  try {
    BUFFER.push(event);
    if (BUFFER.length > MAX_EVENTS) BUFFER.shift();
  } catch (error) {
    console.warn("emit telemetry failed", error);
  }
}

export function getBuffer(): EventBase[] {
  return BUFFER.slice().reverse();
}

export async function flush(): Promise<void> {
  if (!BUFFER.length) return;
  const payload = { events: BUFFER.slice(-50) };
  try {
    await api
      .post("/telemetry", payload)
      .catch(async () => api.post("/api/v1/telemetry", payload));
  } catch (error) {
    console.warn("flush telemetry failed", error);
  }
}

let debugOpen = false;
export function toggleDebugPanel(): void {
  debugOpen = !debugOpen;
  const el = document.getElementById("eipr-debug");
  if (!el) return;
  el.style.display = debugOpen ? "block" : "none";
}
