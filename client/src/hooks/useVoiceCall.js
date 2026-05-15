import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * useVoiceCall
 * ------------
 * Hands-free, browser-native voice loop between the user and the agent
 * operator. STT comes from the Web Speech API (`SpeechRecognition`), TTS
 * from `speechSynthesis`. No backend changes required — the hook is given
 * a `sendMessage(text)` callback that returns `{ answer, conversation_finished }`
 * and orchestrates the whole listening / thinking / speaking loop.
 *
 * State machine:
 *   idle      -> call not started
 *   listening -> microphone open, capturing user speech
 *   thinking  -> waiting for backend reply
 *   speaking  -> playing the operator's answer
 *   ended     -> the user hung up or the backend asked to close
 *
 * The hook also surfaces a live transcript of the conversation so the UI
 * can render it as an accessibility aid.
 */
export function useVoiceCall({ sendMessage, lang = 'en-US' }) {
  const SpeechRecognition =
    typeof window !== 'undefined'
      ? window.SpeechRecognition || window.webkitSpeechRecognition
      : null;

  const supported = Boolean(SpeechRecognition) && typeof window !== 'undefined' && 'speechSynthesis' in window;

  const [status, setStatus] = useState('idle'); // idle | listening | thinking | speaking | ended
  const [interimText, setInterimText] = useState('');
  const [transcript, setTranscript] = useState([]); // [{role, content}]
  const [error, setError] = useState(null);
  const [muted, setMuted] = useState(false);
  const [finishedByAgent, setFinishedByAgent] = useState(false);

  const recognitionRef = useRef(null);
  const utteranceRef = useRef(null);
  const activeRef = useRef(false); // call is alive
  const lastFinalRef = useRef('');
  const sendMessageRef = useRef(sendMessage);

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  // ---------- TTS ----------

  const speak = useCallback(
    (text) =>
      new Promise((resolve) => {
        if (!text || typeof window === 'undefined' || !window.speechSynthesis) {
          resolve();
          return;
        }
        try {
          window.speechSynthesis.cancel();
          const utter = new window.SpeechSynthesisUtterance(text);
          utter.lang = lang;
          utter.rate = 1.0;
          utter.pitch = 1.0;

          // Pick an English voice if available — improves quality dramatically
          // on Chrome/Edge where good neural voices exist.
          const voices = window.speechSynthesis.getVoices();
          const preferred =
            voices.find((v) => /en[-_]US/i.test(v.lang) && /natural|neural|aria|jenny|guy/i.test(v.name)) ||
            voices.find((v) => /en[-_]US/i.test(v.lang)) ||
            voices.find((v) => v.lang && v.lang.startsWith('en'));
          if (preferred) utter.voice = preferred;

          utter.onend = () => resolve();
          utter.onerror = () => resolve();
          utteranceRef.current = utter;
          window.speechSynthesis.speak(utter);
        } catch (e) {
          resolve();
        }
      }),
    [lang]
  );

  // ---------- STT ----------

  const stopRecognition = useCallback(() => {
    const r = recognitionRef.current;
    if (!r) return;
    try {
      r.onresult = null;
      r.onerror = null;
      r.onend = null;
      r.stop();
    } catch (_) {
      /* noop */
    }
    recognitionRef.current = null;
  }, []);

  const listenOnce = useCallback(
    () =>
      new Promise((resolve, reject) => {
        if (!SpeechRecognition) {
          reject(new Error('Speech recognition not supported in this browser.'));
          return;
        }
        // Guard against any leftover recognition instance from a previous turn.
        if (recognitionRef.current) {
          try { recognitionRef.current.abort(); } catch (_) {}
          recognitionRef.current = null;
        }

        const rec = new SpeechRecognition();
        rec.lang = lang;
        rec.interimResults = true;
        rec.continuous = false;
        rec.maxAlternatives = 1;
        recognitionRef.current = rec;

        let finalText = '';
        let lastInterim = '';
        let settled = false;
        const settle = (value) => {
          if (settled) return;
          settled = true;
          recognitionRef.current = null;
          resolve(value);
        };

        rec.onstart = () => {
          // eslint-disable-next-line no-console
          console.log('[voice] recognition started');
        };

        rec.onaudiostart = () => {
          // eslint-disable-next-line no-console
          console.log('[voice] audio capture started');
        };

        rec.onspeechstart = () => {
          // eslint-disable-next-line no-console
          console.log('[voice] speech detected');
        };

        rec.onresult = (ev) => {
          let interim = '';
          for (let i = ev.resultIndex; i < ev.results.length; i++) {
            const res = ev.results[i];
            if (res.isFinal) {
              finalText += res[0].transcript;
            } else {
              interim += res[0].transcript;
            }
          }
          if (interim) lastInterim = interim;
          setInterimText((finalText + ' ' + interim).trim());
        };

        rec.onerror = (ev) => {
          // eslint-disable-next-line no-console
          console.warn('[voice] recognition error:', ev.error, ev);
          if (ev.error === 'aborted' || ev.error === 'no-speech') {
            settle((finalText || lastInterim).trim());
            return;
          }
          if (ev.error === 'not-allowed' || ev.error === 'service-not-allowed') {
            settled = true;
            recognitionRef.current = null;
            reject(new Error('Microphone access was denied. Please allow it in the address bar.'));
            return;
          }
          // For network / audio-capture errors, still settle so the loop can retry.
          settle((finalText || lastInterim).trim());
        };

        rec.onend = () => {
          // eslint-disable-next-line no-console
          console.log('[voice] recognition ended; final="', finalText, '" interim="', lastInterim, '"');
          // Fall back to the last interim transcript if no final result was emitted
          // (Chrome occasionally drops the final event on very short utterances).
          settle((finalText || lastInterim).trim());
        };

        try {
          rec.start();
        } catch (e) {
          // eslint-disable-next-line no-console
          console.error('[voice] recognition.start() threw:', e);
          reject(e);
        }
      }),
    [SpeechRecognition, lang]
  );

  // ---------- main loop ----------

  const loop = useCallback(async () => {
    while (activeRef.current) {
      // 1) LISTEN ---------------------------------------------------------
      setStatus('listening');
      setInterimText('');
      let userText = '';
      try {
        userText = await listenOnce();
      } catch (e) {
        if (!activeRef.current) return;
        setError(e.message || 'Speech recognition failed.');
        activeRef.current = false;
        setStatus('ended');
        return;
      }

      if (!activeRef.current) return;
      userText = (userText || '').trim();
      if (!userText) {
        // Empty utterance (silence / no speech) → just listen again.
        continue;
      }
      lastFinalRef.current = userText;
      setInterimText('');
      setTranscript((prev) => [...prev, { role: 'user', content: userText }]);

      // 2) THINK ---------------------------------------------------------
      setStatus('thinking');
      let answer = '';
      let finishedFlag = false;
      try {
        const res = await sendMessageRef.current(userText);
        answer = (res && res.answer) || '';
        finishedFlag = Boolean(res && res.conversation_finished);
      } catch (e) {
        answer = 'Sorry, I encountered an error. Please try again.';
      }

      if (!activeRef.current) return;
      setTranscript((prev) => [...prev, { role: 'assistant', content: answer }]);

      // 3) SPEAK ---------------------------------------------------------
      setStatus('speaking');
      if (!muted) {
        await speak(answer);
      }
      if (!activeRef.current) return;

      if (finishedFlag) {
        setFinishedByAgent(true);
        activeRef.current = false;
        setStatus('ended');
        return;
      }
    }
  }, [listenOnce, muted, speak]);

  // ---------- public controls ----------

  const start = useCallback(() => {
    if (!supported) {
      setError('Voice calls require a Chromium-based browser (Chrome, Edge) with microphone access.');
      return;
    }
    if (activeRef.current) return;
    setError(null);
    setTranscript([]);
    setInterimText('');
    setFinishedByAgent(false);
    activeRef.current = true;
    // Warm up the voices list (Chrome populates it asynchronously).
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.getVoices();
    }
    loop();
  }, [loop, supported]);

  const hangUp = useCallback(() => {
    activeRef.current = false;
    stopRecognition();
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setStatus('ended');
  }, [stopRecognition]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      activeRef.current = false;
      stopRecognition();
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [stopRecognition]);

  return {
    supported,
    status,
    interimText,
    transcript,
    error,
    finishedByAgent,
    muted,
    setMuted,
    start,
    hangUp,
  };
}
