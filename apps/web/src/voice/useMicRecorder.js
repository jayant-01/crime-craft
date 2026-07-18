import { useCallback, useRef, useState } from "react";
// Minimal recorder hook around MediaRecorder. Returns a webm/opus Blob on stop;
// the backend Whisper path handles that container directly.
export function useMicRecorder() {
    const [state, setState] = useState({ recording: false, error: null });
    const recorderRef = useRef(null);
    const chunksRef = useRef([]);
    const resolveRef = useRef(null);
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
        }
        catch (e) {
            setState({ recording: false, error: e instanceof Error ? e.message : "mic error" });
        }
    }, []);
    const stop = useCallback(() => {
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
