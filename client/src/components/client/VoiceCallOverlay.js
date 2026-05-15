import React, { useEffect, useRef } from 'react';
import {
  MicrophoneIcon,
  PhoneXMarkIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
} from '@heroicons/react/24/solid';
import { useVoiceCall } from '../../hooks/useVoiceCall';

/**
 * Full-screen "call in progress" overlay.
 *
 * Props:
 *   - conversationId: string             active conversation to send messages to
 *   - sendMessage:    (text) => {answer, conversation_finished}
 *   - onClose:        ({ suggestedByAgent }) => void   called when the user hangs up
 *                                                     (the parent then opens the success/failure modal)
 */
const VoiceCallOverlay = ({ sendMessage, onClose }) => {
  const {
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
  } = useVoiceCall({ sendMessage });

  const transcriptEndRef = useRef(null);

  // Auto-start the call when the overlay mounts. `start()` is idempotent
  // (guards on `activeRef.current` internally), which lets it correctly
  // re-arm the loop after React 18 StrictMode's setup→cleanup→setup cycle
  // in development.
  useEffect(() => {
    if (supported) {
      start();
    }
  }, [supported, start]);

  // Auto-close once the agent says we're done (state machine emits `ended`
  // with finishedByAgent = true after the closing line has finished speaking).
  useEffect(() => {
    if (status === 'ended' && finishedByAgent) {
      onClose({ suggestedByAgent: true });
    }
  }, [status, finishedByAgent, onClose]);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, interimText]);

  const handleHangUp = () => {
    hangUp();
    onClose({ suggestedByAgent: false });
  };

  const statusLabel = {
    idle: 'Connecting…',
    listening: 'Listening…',
    thinking: 'Thinking…',
    speaking: 'Speaking…',
    ended: 'Call ended',
  }[status] || status;

  return (
    <div className="fixed inset-0 z-50 bg-gradient-to-br from-secondary-900 via-secondary-800 to-primary-900 text-white flex flex-col">
      {/* Top bar */}
      <div className="px-6 py-4 flex items-center justify-between border-b border-white/10">
        <div>
          <div className="text-sm uppercase tracking-wider text-white/60">Voice call</div>
          <div className="text-lg font-semibold">FastCall operator</div>
        </div>
        <div className="flex items-center space-x-2 text-sm">
          <span className={`inline-block w-2 h-2 rounded-full ${
            status === 'listening' ? 'bg-emerald-400 animate-pulse' :
            status === 'speaking' ? 'bg-sky-400 animate-pulse' :
            status === 'thinking' ? 'bg-amber-400 animate-pulse' :
            'bg-white/40'
          }`} />
          <span>{statusLabel}</span>
        </div>
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col items-center justify-center px-6">
        {!supported ? (
          <div className="max-w-md text-center bg-red-500/20 border border-red-300/40 rounded-xl p-6">
            <h3 className="text-xl font-semibold mb-2">Voice calls not supported</h3>
            <p className="text-white/80">
              Your browser does not support the Web Speech API. Please use a recent
              version of Chrome or Edge to use voice calls.
            </p>
          </div>
        ) : error ? (
          <div className="max-w-md text-center bg-red-500/20 border border-red-300/40 rounded-xl p-6">
            <h3 className="text-xl font-semibold mb-2">Call error</h3>
            <p className="text-white/80">{error}</p>
          </div>
        ) : (
          <>
            {/* Animated mic indicator */}
            <div className="relative mb-8">
              <div className={`absolute inset-0 rounded-full ${
                status === 'listening' ? 'bg-emerald-400/40 animate-ping' :
                status === 'speaking' ? 'bg-sky-400/40 animate-ping' : ''
              }`} />
              <div className={`relative w-32 h-32 rounded-full flex items-center justify-center
                ${status === 'listening' ? 'bg-emerald-500' :
                  status === 'speaking' ? 'bg-sky-500' :
                  status === 'thinking' ? 'bg-amber-500' :
                  'bg-white/20'}
              `}>
                <MicrophoneIcon className="h-14 w-14 text-white" />
              </div>
            </div>

            {/* Live transcript */}
            <div className="w-full max-w-2xl bg-black/30 rounded-xl p-4 max-h-80 overflow-y-auto mb-6 backdrop-blur-sm">
              {transcript.length === 0 && !interimText ? (
                <div className="text-center text-white/50 py-4">
                  Start speaking — the transcript will appear here.
                </div>
              ) : (
                <div className="space-y-2">
                  {transcript.map((t, i) => (
                    <div
                      key={i}
                      className={`flex ${t.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-md px-3 py-2 rounded-lg text-sm ${
                        t.role === 'user'
                          ? 'bg-primary-500/80 text-white'
                          : 'bg-white/15 text-white'
                      }`}>
                        {t.content}
                      </div>
                    </div>
                  ))}
                  {interimText && (
                    <div className="flex justify-end">
                      <div className="max-w-md px-3 py-2 rounded-lg text-sm bg-primary-500/40 text-white/80 italic">
                        {interimText}
                      </div>
                    </div>
                  )}
                  <div ref={transcriptEndRef} />
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Controls */}
      <div className="px-6 py-6 flex items-center justify-center space-x-6 border-t border-white/10">
        <button
          onClick={() => setMuted((m) => !m)}
          title={muted ? 'Unmute operator voice' : 'Mute operator voice'}
          className="w-14 h-14 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition"
        >
          {muted ? (
            <SpeakerXMarkIcon className="h-7 w-7 text-white" />
          ) : (
            <SpeakerWaveIcon className="h-7 w-7 text-white" />
          )}
        </button>

        <button
          onClick={handleHangUp}
          title="End call"
          className="w-20 h-20 rounded-full bg-red-600 hover:bg-red-700 flex items-center justify-center transition shadow-lg"
        >
          <PhoneXMarkIcon className="h-10 w-10 text-white" />
        </button>
      </div>
    </div>
  );
};

export default VoiceCallOverlay;
