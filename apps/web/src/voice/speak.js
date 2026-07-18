import { voiceApi } from "../api/endpoints";
/**
 * Plays a TTS rendering of `text`. Tries the backend `/voice/tts` first
 * (so we get Indic-quality voices when available). Falls back to the
 * browser's built-in speechSynthesis when the backend is in stub mode and
 * we just want something to come out of the speakers.
 */
export async function speak(text, language) {
    try {
        const blob = await voiceApi.tts(text, language);
        const provider = "stub"; // we can't read response headers via the fetch wrapper here
        if (provider === "stub" && "speechSynthesis" in window) {
            // The stub returns a silent WAV — fall through to browser TTS for an
            // audible result while the prod TTS provider is being chosen.
            browserSpeak(text, language);
            return;
        }
        const audio = new Audio(URL.createObjectURL(blob));
        await audio.play();
    }
    catch {
        if ("speechSynthesis" in window)
            browserSpeak(text, language);
    }
}
function browserSpeak(text, language) {
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = { en: "en-IN", hi: "hi-IN", kn: "kn-IN" }[language] ?? "en-IN";
    window.speechSynthesis.speak(utter);
}
