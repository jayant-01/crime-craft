import { useCallback, useRef, useState } from "react";

interface State {
  recording: boolean;
  error: string | null;
}

// Minimal recorder hook around MediaRecorder. Returns a webm/opus Blob on stop;
// the backend Whisper path handles that container directly.
export function useMicRecorder() {
  const [state, setState] = useState<State>({ recording: false, error: null });
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const resolveRef = useRef<((b: Blob) => void) | null>(null);

  const start = useCallback(async () => {
    setState({ recording: false, error: null });
    if (!navigator.mediaDevices?.getUserMedia) {
      setState({ recording: false, error: "microphone not supported" });
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
        resolveRef.current?.(blob);
        resolveRef.current = null;
        setState({ recording: false, error: null });
      };
      rec.start();
      recorderRef.current = rec;
      setState({ recording: true, error: null });
    } catch (e) {
      setState({ recording: false, error: e instanceof Error ? e.message : "mic error" });
    }
  }, []);

  const stop = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      const rec = recorderRef.current;
      if (!rec) {
        resolve(new Blob());
        return;
      }
      resolveRef.current = resolve;
      rec.stop();
    });
  }, []);

  return { ...state, start, stop };
}
