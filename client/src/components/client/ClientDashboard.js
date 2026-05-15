import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { conversationAPI, ticketsAPI } from '../../services/api';
import {
  PaperAirplaneIcon,
  ChatBubbleLeftRightIcon,
  ArrowRightOnRectangleIcon,
  PlusIcon,
  XMarkIcon,
  CheckCircleIcon,
  XCircleIcon,
  TicketIcon,
  PhoneIcon,
} from '@heroicons/react/24/outline';
import VoiceCallOverlay from './VoiceCallOverlay';

const ClientDashboard = () => {
  const [openConversations, setOpenConversations] = useState([]); // [{conversation_id, turns, preview}]
  const [tickets, setTickets] = useState([]); // closed tickets
  const [activeId, setActiveId] = useState(null); // conversation_id (open) OR `ticket-<id>`
  const [activeTurns, setActiveTurns] = useState([]);
  const [activeIsTicket, setActiveIsTicket] = useState(false);
  const [activeTicketStatus, setActiveTicketStatus] = useState(null);

  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingList, setLoadingList] = useState(false);
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeSuggestedByAI, setCloseSuggestedByAI] = useState(false);
  const [callOpen, setCallOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    refreshAll();
  }, [user, navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeTurns, sending]);

  const refreshAll = async () => {
    setLoadingList(true);
    try {
      const [open, closed] = await Promise.all([
        conversationAPI.listOpen(),
        ticketsAPI.listMine(),
      ]);
      setOpenConversations(open || []);
      setTickets(closed || []);

      if (open && open.length > 0 && !activeId) {
        selectOpen(open[0]);
      }
    } catch (e) {
      console.error('Failed to load conversations:', e);
    } finally {
      setLoadingList(false);
    }
  };

  const selectOpen = (conv) => {
    setActiveId(conv.conversation_id);
    setActiveIsTicket(false);
    setActiveTicketStatus(null);
    setActiveTurns(conv.turns || []);
  };

  const selectTicket = async (ticket) => {
    setActiveId(`ticket-${ticket.ticket_id}`);
    setActiveIsTicket(true);
    setActiveTicketStatus(ticket.status);
    try {
      const full = await ticketsAPI.getMine(ticket.ticket_id);
      setActiveTurns((full?.payload?.turns) || []);
    } catch (e) {
      console.error('Failed to load ticket:', e);
      setActiveTurns([]);
    }
  };

  const handleNewConversation = async () => {
    try {
      const conv = await conversationAPI.create();
      const newConv = { conversation_id: conv.conversation_id, turns: [], preview: '' };
      setOpenConversations(prev => [newConv, ...prev]);
      selectOpen(newConv);
    } catch (e) {
      console.error('Failed to create conversation:', e);
    }
  };

  const updateOpenConv = (convId, updater) => {
    setOpenConversations(prev =>
      prev.map(c => (c.conversation_id === convId ? { ...c, ...updater(c) } : c))
    );
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || activeIsTicket || !activeId) return;

    const text = newMessage;
    const convId = activeId;
    const userTurn = { role: 'user', content: text, ts: Date.now() / 1000 };

    setActiveTurns(prev => [...prev, userTurn]);
    updateOpenConv(convId, c => ({ turns: [...(c.turns || []), userTurn], preview: c.preview || text }));
    setNewMessage('');
    setSending(true);

    try {
      const res = await conversationAPI.sendMessage(convId, text);
      const aiTurn = { role: 'assistant', content: res.answer, ts: Date.now() / 1000 };

      setActiveTurns(prev => [...prev, aiTurn]);
      updateOpenConv(convId, c => ({ turns: [...(c.turns || []), aiTurn] }));

      if (res.conversation_finished) {
        setCloseSuggestedByAI(true);
        setShowCloseModal(true);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      const errTurn = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        ts: Date.now() / 1000,
      };
      setActiveTurns(prev => [...prev, errTurn]);
    } finally {
      setSending(false);
    }
  };

  const handleEndConversation = () => {
    setCloseSuggestedByAI(false);
    setShowCloseModal(true);
  };

  // ---- Voice call ----

  const ensureActiveConversation = async () => {
    if (activeId && !activeIsTicket) return activeId;
    const conv = await conversationAPI.create();
    const newConv = { conversation_id: conv.conversation_id, turns: [], preview: '' };
    setOpenConversations((prev) => [newConv, ...prev]);
    selectOpen(newConv);
    return conv.conversation_id;
  };

  const handleStartCall = async () => {
    try {
      await ensureActiveConversation();
      setCallOpen(true);
    } catch (e) {
      console.error('Failed to start voice call:', e);
    }
  };

  // Used by VoiceCallOverlay to forward each transcribed utterance through
  // the same backend pipeline as the chat input. Mirrors `handleSendMessage`
  // but returns the raw { answer, conversation_finished } payload.
  const voiceSendMessage = async (text) => {
    if (!activeId || activeIsTicket) {
      throw new Error('No active conversation for voice call.');
    }
    const userTurn = { role: 'user', content: text, ts: Date.now() / 1000 };
    setActiveTurns((prev) => [...prev, userTurn]);
    updateOpenConv(activeId, (c) => ({
      turns: [...(c.turns || []), userTurn],
      preview: c.preview || text,
    }));

    const res = await conversationAPI.sendMessage(activeId, text);
    const aiTurn = { role: 'assistant', content: res.answer, ts: Date.now() / 1000 };
    setActiveTurns((prev) => [...prev, aiTurn]);
    updateOpenConv(activeId, (c) => ({ turns: [...(c.turns || []), aiTurn] }));
    return res; // { answer, conversation_finished }
  };

  const handleCallClosed = ({ suggestedByAgent }) => {
    setCallOpen(false);
    setCloseSuggestedByAI(Boolean(suggestedByAgent));
    setShowCloseModal(true);
  };

  const handleCloseConfirm = async (success) => {
    if (!activeId || activeIsTicket) {
      setShowCloseModal(false);
      return;
    }
    try {
      await conversationAPI.close(activeId, success);
      setShowCloseModal(false);
      setActiveId(null);
      setActiveTurns([]);
      await refreshAll();
    } catch (e) {
      console.error('Failed to close conversation:', e);
      setShowCloseModal(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    try {
      const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-secondary-50">
      <div className="container mx-auto px-4 py-6 h-screen flex flex-col">
        {/* Header */}
        <div className="glass-effect rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <ChatBubbleLeftRightIcon className="h-8 w-8 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-secondary-800">FastCall</h1>
                <p className="text-secondary-600">Welcome, {user?.name}</p>
              </div>
            </div>
            <button onClick={handleLogout} className="btn-secondary flex items-center space-x-2">
              <ArrowRightOnRectangleIcon className="h-5 w-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>

        {/* Main */}
        <div className="flex-1 glass-effect rounded-xl p-6 flex space-x-6 min-h-0">
          {/* Sidebar */}
          <div className="w-1/3 flex flex-col border-r border-secondary-200 pr-4 min-h-0">
            <button
              onClick={handleNewConversation}
              className="btn-primary mb-4 flex items-center justify-center space-x-2"
            >
              <PlusIcon className="h-5 w-5" />
              <span>Create new conversation</span>
            </button>

            <div className="flex-1 overflow-y-auto space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-secondary-700 uppercase tracking-wide mb-2">
                  Active conversations
                </h3>
                {loadingList ? (
                  <div className="text-sm text-secondary-500">Loading...</div>
                ) : openConversations.length === 0 ? (
                  <div className="text-sm text-secondary-500">No active conversations.</div>
                ) : (
                  <div className="space-y-2">
                    {openConversations.map(c => (
                      <button
                        key={c.conversation_id}
                        onClick={() => selectOpen(c)}
                        className={`w-full text-left p-3 rounded-lg border transition ${
                          activeId === c.conversation_id
                            ? 'bg-primary-100 border-primary-300'
                            : 'bg-white border-secondary-200 hover:bg-secondary-50'
                        }`}
                      >
                        <div className="text-sm font-medium text-secondary-800 truncate">
                          {c.preview || 'New conversation'}
                        </div>
                        <div className="text-xs text-secondary-500">
                          {(c.turns || []).length} messages
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <h3 className="text-sm font-semibold text-secondary-700 uppercase tracking-wide mb-2 flex items-center">
                  <TicketIcon className="h-4 w-4 mr-1" /> Past tickets
                </h3>
                {tickets.length === 0 ? (
                  <div className="text-sm text-secondary-500">No tickets yet.</div>
                ) : (
                  <div className="space-y-2">
                    {tickets.map(t => (
                      <button
                        key={t.ticket_id}
                        onClick={() => selectTicket(t)}
                        className={`w-full text-left p-3 rounded-lg border transition ${
                          activeId === `ticket-${t.ticket_id}`
                            ? 'bg-primary-100 border-primary-300'
                            : 'bg-white border-secondary-200 hover:bg-secondary-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="text-sm font-medium text-secondary-800 truncate flex-1">
                            #{t.ticket_id} {t.preview || '(no preview)'}
                          </div>
                          {t.status === 'success' ? (
                            <CheckCircleIcon className="h-5 w-5 text-green-600 ml-2 flex-shrink-0" />
                          ) : (
                            <XCircleIcon className="h-5 w-5 text-red-600 ml-2 flex-shrink-0" />
                          )}
                        </div>
                        <div className="text-xs text-secondary-500">
                          {t.closed_at ? new Date(t.closed_at).toLocaleString() : ''}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Chat panel */}
          <div className="flex-1 flex flex-col min-h-0">
            {!activeId ? (
              <div className="flex-1 flex items-center justify-center text-center text-secondary-500">
                <div>
                  <ChatBubbleLeftRightIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
                  <p className="text-lg">Select or create a conversation to begin.</p>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-semibold text-secondary-800">
                      {activeIsTicket
                        ? `Ticket ${activeId.replace('ticket-', '#')} (${activeTicketStatus})`
                        : 'Active conversation'}
                    </h3>
                  </div>
                  {!activeIsTicket && (
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={handleStartCall}
                        className="btn-primary flex items-center space-x-2"
                        title="Call the operator"
                      >
                        <PhoneIcon className="h-5 w-5" />
                        <span>Call</span>
                      </button>
                      <button
                        onClick={handleEndConversation}
                        className="btn-secondary flex items-center space-x-2"
                      >
                        <XMarkIcon className="h-5 w-5" />
                        <span>End conversation</span>
                      </button>
                    </div>
                  )}
                </div>

                <div className="flex-1 overflow-y-auto mb-4 space-y-4">
                  {activeTurns.length === 0 ? (
                    <div className="text-center text-secondary-500 mt-8">
                      <p className="text-lg">Start chatting</p>
                      <p className="text-sm">Ask me anything about our services!</p>
                    </div>
                  ) : (
                    activeTurns.map((m, idx) => (
                      <div
                        key={idx}
                        className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
                      >
                        <div className={`max-w-xs lg:max-w-md`}>
                          <div className={m.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
                            <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                            {m.ts && (
                              <p className={`text-xs mt-1 ${m.role === 'user' ? 'text-primary-100' : 'text-secondary-500'}`}>
                                {formatTime(m.ts)}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                  {sending && (
                    <div className="flex justify-start animate-slide-up">
                      <div className="chat-bubble-ai">
                        <div className="flex items-center space-x-2">
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce"></div>
                            <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                            <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                          </div>
                          <span className="text-xs text-secondary-500">AI is thinking...</span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {!activeIsTicket && (
                  <form onSubmit={handleSendMessage} className="flex space-x-4">
                    <input
                      type="text"
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Type your message..."
                      className="flex-1 input-field"
                      disabled={sending}
                    />
                    <button
                      type="submit"
                      disabled={sending || !newMessage.trim()}
                      className="btn-primary px-6 py-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                    >
                      <PaperAirplaneIcon className="h-5 w-5" />
                      <span>Send</span>
                    </button>
                  </form>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Voice call overlay */}
      {callOpen && (
        <VoiceCallOverlay
          sendMessage={voiceSendMessage}
          onClose={handleCallClosed}
        />
      )}

      {/* Close confirmation modal */}
      {showCloseModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold text-secondary-800 mb-2">
              {closeSuggestedByAI ? 'It looks like we are done.' : 'End conversation'}
            </h2>
            <p className="text-secondary-600 mb-6">
              Was the conversation completed successfully?
            </p>
            <div className="flex space-x-3 justify-end">
              <button
                onClick={() => setShowCloseModal(false)}
                className="px-4 py-2 rounded-md border border-secondary-300 text-secondary-700 hover:bg-secondary-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleCloseConfirm(false)}
                className="px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 flex items-center space-x-2"
              >
                <XCircleIcon className="h-5 w-5" />
                <span>No</span>
              </button>
              <button
                onClick={() => handleCloseConfirm(true)}
                className="px-4 py-2 rounded-md bg-green-600 text-white hover:bg-green-700 flex items-center space-x-2"
              >
                <CheckCircleIcon className="h-5 w-5" />
                <span>Yes</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClientDashboard;
