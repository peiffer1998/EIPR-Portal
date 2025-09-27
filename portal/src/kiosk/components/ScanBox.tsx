import { useCallback, useEffect, useRef, useState } from 'react';

type ScanBoxProps = {
  label?: string;
  onSubmit: (id: string) => void;
};

type JsQRResult = {
  data: string;
};

const loadJsQR = async () => {
  if ((window as any).jsQR) return;
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/jsqr';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Unable to load jsQR'));
    document.body.appendChild(script);
  });
};

export default function ScanBox({ label = 'Scan or type ID', onSubmit }: ScanBoxProps) {
  const [manualId, setManualId] = useState('');
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [error, setError] = useState('');
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number>();

  const cleanup = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    const stream = videoRef.current?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((track) => track.stop());
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const tick = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) {
      rafRef.current = requestAnimationFrame(tick);
      return;
    }

    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext('2d');
    if (!context) {
      rafRef.current = requestAnimationFrame(tick);
      return;
    }

    context.drawImage(video, 0, 0, width, height);

    try {
      const imageData = context.getImageData(0, 0, width, height);
      const result = ((window as any).jsQR?.(imageData.data, width, height) ?? null) as JsQRResult | null;
      if (result?.data) {
        onSubmit(String(result.data));
        cleanup();
        setCameraEnabled(false);
        return;
      }
    } catch {
      // Ignore decoding errors; continue scanning.
    }

    rafRef.current = requestAnimationFrame(tick);
  }, [cleanup, onSubmit]);

  const startCamera = useCallback(async () => {
    if (cameraEnabled) return;

    try {
      setError('');
      const stream = await navigator.mediaDevices?.getUserMedia?.({ video: { facingMode: 'environment' } });
      if (!stream) throw new Error('Camera unavailable');
      const video = videoRef.current;
      if (!video) throw new Error('Video element missing');

      video.srcObject = stream;
      await video.play();

      await loadJsQR();
      setCameraEnabled(true);
      rafRef.current = requestAnimationFrame(tick);
    } catch (cameraError) {
      setError((cameraError as Error).message ?? 'Camera unavailable');
      cleanup();
      setCameraEnabled(false);
    }
  }, [cameraEnabled, cleanup, tick]);

  const submitManual = useCallback(() => {
    if (!manualId.trim()) return;
    onSubmit(manualId.trim());
    setManualId('');
  }, [manualId, onSubmit]);

  return (
    <div className="grid gap-2">
      <label className="text-lg font-semibold" htmlFor="scan-box-input">
        {label}
      </label>
      <div className="flex flex-wrap gap-2">
        <input
          id="scan-box-input"
          className="text-2xl border rounded px-3 py-2 w-full max-w-xl"
          placeholder="Type ID"
          value={manualId}
          onChange={(event) => setManualId(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') submitManual();
          }}
        />
        <button type="button" className="px-3 py-2 rounded bg-slate-900 text-white" onClick={submitManual}>
          Go
        </button>
        <button
          type="button"
          className="px-3 py-2 rounded border"
          onClick={startCamera}
          disabled={cameraEnabled}
        >
          Use Camera
        </button>
      </div>
      {cameraEnabled ? (
        <div className="grid">
          <video ref={videoRef} playsInline muted className="rounded border max-h-[40vh]" />
          <canvas ref={canvasRef} className="hidden" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-red-600">{error}</div> : null}
    </div>
  );
}
