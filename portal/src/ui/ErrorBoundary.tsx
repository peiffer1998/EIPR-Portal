import React from "react";

import { emit } from "../telemetry/telemetry";
import { toast } from "./Toast";

type Props = {
  children: React.ReactNode;
};

type State = {
  error?: unknown;
};

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = {};

  static getDerivedStateFromError(error: unknown): State {
    return { error };
  }

  componentDidCatch(error: unknown, info: unknown): void {
    try {
      const anyError = error as any;
      const requestId =
        anyError?.requestId || anyError?.response?.headers?.["x-request-id"];
      emit({
        ts: Date.now(),
        type: "ui.error",
        requestId,
        message: String(anyError?.message ?? error ?? "UI error"),
        meta: { stack: String(anyError?.stack ?? ""), info },
      });
      toast(
        `Unexpected error${requestId ? ` • Request-ID ${requestId}` : ""}`,
        "error",
        8000,
      );
    } catch (err) {
      console.warn("ErrorBoundary telemetry failed", err);
    }
  }

  render(): React.ReactNode {
    if (!this.state.error) return this.props.children;

    const error = this.state.error as any;
    const requestId =
      error?.requestId || error?.response?.headers?.["x-request-id"];

    const copyDiagnostics = async () => {
      try {
        const payload = JSON.stringify(
          {
            message: String(error?.message ?? error ?? "UI error"),
            requestId,
            stack: String(error?.stack ?? ""),
          },
          null,
          2,
        );
        await navigator.clipboard.writeText(payload);
        toast("Diagnostics copied", "success");
      } catch (err) {
        console.warn("Copy diagnostics failed", err);
      }
    };

    const retry = () => {
      this.setState({ error: undefined });
      window.location.reload();
    };

    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-xl grid gap-2">
          <div className="text-lg font-semibold">Something went wrong</div>
          {requestId ? (
            <div className="text-sm text-slate-600">
              Request-ID: <code>{requestId}</code>
            </div>
          ) : null}
          <div className="flex gap-2 justify-end mt-2">
            <button type="button" className="px-3 py-2 rounded border" onClick={copyDiagnostics}>
              Copy diagnostics
            </button>
            <button
              type="button"
              className="px-3 py-2 rounded bg-slate-900 text-white"
              onClick={retry}
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }
}
