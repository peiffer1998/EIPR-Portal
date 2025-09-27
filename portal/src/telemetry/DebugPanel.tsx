import { useEffect, useState } from "react";

import { getBuffer, toggleDebugPanel } from "./telemetry";

export default function DebugPanel(): JSX.Element {
  const [events, setEvents] = useState(getBuffer());

  useEffect(() => {
    const id = window.setInterval(() => setEvents(getBuffer()), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div
      id="eipr-debug"
      className="no-print"
      style={{
        display: "none",
        position: "fixed",
        inset: "10% 5% auto 5%",
        background: "#fff",
        border: "1px solid #dce1e7",
        borderRadius: 12,
        boxShadow: "0 12px 40px rgba(15,23,42,0.18)",
        zIndex: 9998,
      }}
    >
      <div
        style={{
          padding: 8,
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <strong>Debug Panel</strong>
        <button type="button" onClick={() => toggleDebugPanel()}>
          Close
        </button>
      </div>
      <div
        style={{
          padding: 8,
          maxHeight: "60vh",
          overflow: "auto",
          fontFamily: "ui-monospace,monospace",
          fontSize: 12,
        }}
      >
        {events.map((event, index) => (
          <pre
            key={index}
            style={{
              margin: "6px 0",
              padding: 6,
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
            }}
          >
            {JSON.stringify(event, null, 2)}
          </pre>
        ))}
        {!events.length && <div style={{ color: "#64748b" }}>No events</div>}
      </div>
    </div>
  );
}
