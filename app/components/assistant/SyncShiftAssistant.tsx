'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  SparklesIcon,
  XMarkIcon,
  PaperAirplaneIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  ClockIcon,
  MapPinIcon,
  CalendarIcon,
  ArrowRightIcon,
  InformationCircleIcon,
  ChatBubbleLeftRightIcon,
  PlusIcon,
  TrashIcon,
  ShieldCheckIcon,
  BuildingLibraryIcon,
  AcademicCapIcon,
} from '@heroicons/react/24/outline';
import {
  api,
  ActionPreview,
  AssistantChatResponse,
  AssistantConfirmResponse,
  AssistantConversationItem,
} from '@/lib/api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  action?: ActionPreview | null;
  choices?: Record<string, any>[] | null;
  confirmed?: boolean;
  isConfirming?: boolean;
  confirmError?: string | null;
  confirmSuccess?: string | null;
}

const STUDENT_SUGGESTIONS = [
  'What classes do I have today?',
  'When can I work this week?',
  'Do I have any conflicts?',
  'How many work hours do I have left?',
  'Preview my weekly plan',
  'Move my Friday shift to 4 PM',
];

const ADMIN_SUGGESTIONS = [
  'Which rooms are available on Monday between 10:00 and 12:00?',
  'Show university timetable versions',
  'Who is affected by moving CS101?',
  'Create a new draft version for timetable',
];

export function openSyncShiftAssistant() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('open-syncshift-assistant'));
  }
}

export default function SyncShiftAssistant() {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStateText, setLoadingStateText] = useState<string>('Consulting schedule...');
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<AssistantConversationItem[]>([]);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [userRole, setUserRole] = useState<'student' | 'admin'>('student');
  const [institutionId, setInstitutionId] = useState<number | null>(null);

  const initialWelcomeText =
    userRole === 'admin'
      ? "👋 Welcome, Administrator! I'm your **SyncShift Assistant**. Ask me about room availability, timetable versions, draft creation, or impact analyses. Every timetable modification requires your explicit review and confirmation."
      : "👋 Hi! I'm your **SyncShift Assistant**. Ask me anything about your timetable, enrolled courses, work hours, conflicts, or study blocks. All schedule changes require your explicit confirmation.";

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: initialWelcomeText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Listen for open event & check role
  useEffect(() => {
    const handleOpen = () => setIsOpen(true);
    window.addEventListener('open-syncshift-assistant', handleOpen);

    // Fetch user status to set role
    api
      .getMyInstitutionStatus()
      .then((res) => {
        if (res?.has_institution && res.membership) {
          setInstitutionId(res.membership.institution_id);
          if (res.membership.role === 'admin' || res.membership.role === 'super_admin') {
            setUserRole('admin');
          }
        }
      })
      .catch(() => {});

    return () => window.removeEventListener('open-syncshift-assistant', handleOpen);
  }, []);

  // Load user's conversations
  const loadConversations = async () => {
    try {
      const convs = await api.getAssistantConversations(institutionId);
      if (Array.isArray(convs)) {
        setConversations(convs);
      }
    } catch {
      // Ignore unauthenticated or offline errors
    }
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
      inputRef.current?.focus();
      loadConversations();
    }
  }, [isOpen]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleStartNewChat = () => {
    setCurrentConversationId(null);
    setShowHistory(false);
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        sender: 'assistant',
        text:
          userRole === 'admin'
            ? "Started a new administrator consultation. What would you like to inspect or plan?"
            : "Started a fresh conversation. What would you like to check in your schedule today?",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  const handleSelectConversation = async (convId: number) => {
    try {
      setIsLoading(true);
      setLoadingStateText('Loading conversation history...');
      const detail = await api.getAssistantConversationDetail(convId);
      setCurrentConversationId(convId);
      setShowHistory(false);

      if (detail && Array.isArray(detail.messages)) {
        const loaded: ChatMessage[] = detail.messages.map((m) => ({
          id: `msg-${m.id}`,
          sender: m.role === 'user' ? 'user' : 'assistant',
          text: m.content,
          timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          action: m.action_preview,
        }));
        setMessages(loaded.length > 0 ? loaded : [
          {
            id: 'empty',
            sender: 'assistant',
            text: 'Conversation resumed.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: 'assistant',
          text: 'Unable to load conversation history. You can continue chatting below.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, convId: number) => {
    e.stopPropagation();
    try {
      await api.deleteAssistantConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (currentConversationId === convId) {
        handleStartNewChat();
      }
    } catch {
      // deletion error
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || isLoading) return;

    const userMsgId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsLoading(true);

    if (query.toLowerCase().includes('move') || query.toLowerCase().includes('reschedule')) {
      setLoadingStateText('Checking schedule constraints & room conflicts...');
    } else if (query.toLowerCase().includes('work') || query.toLowerCase().includes('plan')) {
      setLoadingStateText('Running smart schedule evaluator...');
    } else if (query.toLowerCase().includes('room') || query.toLowerCase().includes('version')) {
      setLoadingStateText('Checking institutional records...');
    } else {
      setLoadingStateText('Analyzing request...');
    }

    try {
      const response: AssistantChatResponse = await api.chatAssistant(
        query,
        currentConversationId,
        institutionId
      );

      if (response.conversation_id && response.conversation_id !== currentConversationId) {
        setCurrentConversationId(response.conversation_id);
        loadConversations();
      }

      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        sender: 'assistant',
        text: response.message,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        action: response.action,
        choices: response.choices,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: err?.message || 'SyncShift Assistant is temporarily unavailable. Please try again.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmAction = async (msgId: string, action: ActionPreview) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, isConfirming: true, confirmError: null } : m))
    );

    try {
      const result: AssistantConfirmResponse = await api.confirmAssistantAction(action);
      if (result.success) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId
              ? {
                  ...m,
                  isConfirming: false,
                  confirmed: true,
                  confirmSuccess: result.message,
                }
              : m
          )
        );
        // Trigger global calendar reload event
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('syncshift:schedule-updated'));
        }
      } else {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId
              ? {
                  ...m,
                  isConfirming: false,
                  confirmError: result.message || 'Action could not be completed.',
                }
              : m
          )
        );
      }
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? {
                ...m,
                isConfirming: false,
                confirmError: err?.message || 'Failed to execute confirmed change.',
              }
            : m
        )
      );
    }
  };

  const handleCancelAction = (msgId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, action: null, text: m.text + '\n\n*(Action cancelled by user)*' } : m))
    );
  };

  const handleSelectChoice = (choice: Record<string, any>) => {
    handleSendMessage(`Move ${choice.title} on ${choice.day} to 4 PM`);
  };

  // Render text with basic bold, bullet, and link formatting
  const renderFormattedText = (text: string) => {
    const lines = text.split('\n');
    return (
      <div className="space-y-1.5 text-sm leading-relaxed">
        {lines.map((line, idx) => {
          if (!line.trim()) return <div key={idx} className="h-1" />;

          let parsedLine: React.ReactNode = line;
          // Simple bold parser
          if (line.includes('**')) {
            const parts = line.split('**');
            parsedLine = parts.map((part, pIdx) =>
              pIdx % 2 === 1 ? <strong key={pIdx} className="font-semibold text-white">{part}</strong> : part
            );
          }

          if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
            return (
              <div key={idx} className="flex items-start gap-1.5 pl-1">
                <span className="text-indigo-400 font-bold">•</span>
                <span className="flex-1">
                  {typeof parsedLine === 'string' ? parsedLine.replace(/^[•-]\s*/, '') : parsedLine}
                </span>
              </div>
            );
          }

          return <p key={idx}>{parsedLine}</p>;
        })}
      </div>
    );
  };

  const suggestions = userRole === 'admin' ? ADMIN_SUGGESTIONS : STUDENT_SUGGESTIONS;

  return (
    <>
      {/* Floating Action Trigger Button */}
      <motion.button
        id="syncshift-assistant-trigger"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`fixed bottom-6 right-6 z-40 flex items-center gap-2.5 px-4 py-3 rounded-full font-medium shadow-xl transition-all duration-300 ${
          isOpen
            ? 'bg-slate-800 text-slate-200 border border-slate-700 shadow-slate-900/50'
            : 'bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-105 active:scale-95'
        }`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Open SyncShift Assistant"
      >
        <SparklesIcon className="w-5 h-5 text-indigo-200 animate-pulse" />
        <span className="text-sm font-semibold tracking-wide hidden sm:inline">
          {isOpen ? 'Close Assistant' : 'Ask SyncShift'}
        </span>
      </motion.button>

      {/* Floating / Drawer Assistant Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            id="syncshift-assistant-panel"
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-20 right-4 sm:right-6 z-50 w-[calc(100vw-2rem)] sm:w-[480px] max-h-[85vh] h-[680px] bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-800 bg-slate-950/70">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-inner">
                  {userRole === 'admin' ? (
                    <BuildingLibraryIcon className="w-4 h-4 text-white" />
                  ) : (
                    <SparklesIcon className="w-4 h-4 text-white" />
                  )}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-1.5">
                    SyncShift Assistant
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block" />
                    {userRole === 'admin' && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
                        ADMIN
                      </span>
                    )}
                  </h3>
                  <p className="text-[11px] text-slate-400">Deterministic Coordinator • Zero Hallucination</p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {/* Conversation History Toggle */}
                <button
                  onClick={() => setShowHistory((prev) => !prev)}
                  className={`p-1.5 rounded-lg transition ${
                    showHistory
                      ? 'bg-indigo-600/30 text-indigo-300'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                  title="Past conversations"
                  aria-label="Past conversations"
                >
                  <ChatBubbleLeftRightIcon className="w-4 h-4" />
                </button>

                {/* New Chat */}
                <button
                  onClick={handleStartNewChat}
                  className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
                  title="New conversation"
                  aria-label="New conversation"
                >
                  <PlusIcon className="w-4 h-4" />
                </button>

                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
                  title="Close Assistant"
                  aria-label="Close Assistant"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Conversation History Drawer */}
            <AnimatePresence>
              {showHistory && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-b border-slate-800 bg-slate-950/90 overflow-hidden"
                >
                  <div className="p-3 max-h-48 overflow-y-auto space-y-1.5 custom-scrollbar">
                    <div className="flex items-center justify-between px-1 pb-1">
                      <span className="text-xs font-semibold text-slate-400">Conversations</span>
                      <button
                        onClick={handleStartNewChat}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                      >
                        <PlusIcon className="w-3 h-3" /> New
                      </button>
                    </div>

                    {conversations.length === 0 ? (
                      <p className="text-xs text-slate-500 px-1 py-2 italic">No past conversations yet.</p>
                    ) : (
                      conversations.map((c) => (
                        <div
                          key={c.id}
                          onClick={() => handleSelectConversation(c.id)}
                          className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition ${
                            c.id === currentConversationId
                              ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40'
                              : 'text-slate-300 hover:bg-slate-800/80'
                          }`}
                        >
                          <span className="truncate flex-1">{c.title || 'Conversation'}</span>
                          <button
                            onClick={(e) => handleDeleteConversation(e, c.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 rounded transition"
                            title="Delete conversation"
                          >
                            <TrashIcon className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Chat Messages Feed */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-slate-200 custom-scrollbar">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
                >
                  {/* Sender Bubble */}
                  <div
                    className={`max-w-[90%] rounded-2xl px-4 py-3 shadow-md ${
                      msg.sender === 'user'
                        ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-br-none'
                        : 'bg-slate-800/90 border border-slate-700/60 text-slate-200 rounded-bl-none'
                    }`}
                  >
                    {renderFormattedText(msg.text)}

                    {/* Ambiguous Choices */}
                    {msg.choices && msg.choices.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-700/80 space-y-2">
                        <p className="text-xs font-medium text-indigo-300">Select which shift to move:</p>
                        <div className="grid grid-cols-1 gap-1.5">
                          {msg.choices.map((choice, cIdx) => (
                            <button
                              key={cIdx}
                              onClick={() => handleSelectChoice(choice)}
                              className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-slate-900/60 hover:bg-indigo-600/30 border border-slate-700 hover:border-indigo-500/50 text-left text-xs transition"
                            >
                              <span className="font-semibold text-white">{choice.title}</span>
                              <span className="text-slate-400">
                                {choice.day} {choice.start_time}–{choice.end_time}
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Structured Action Preview Card */}
                    {msg.action && (
                      <div className="mt-3.5 p-3.5 bg-slate-950/80 border border-slate-700/90 rounded-xl space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                          <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                            <ClockIcon className="w-3.5 h-3.5" /> Action Preview
                          </span>
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-900/50 text-indigo-300 border border-indigo-700/40">
                            Explicit Confirmation Required
                          </span>
                        </div>

                        {/* Title & Description */}
                        <div className="space-y-1 text-xs">
                          <p className="font-semibold text-white text-sm">{msg.action.title}</p>
                          {msg.action.description && (
                            <p className="text-slate-400 text-xs">{msg.action.description}</p>
                          )}
                        </div>

                        {/* From -> To Preview if available */}
                        {msg.action.original && msg.action.target && (
                          <div className="p-2 rounded-lg bg-slate-900/70 border border-slate-800 text-xs space-y-1">
                            <div className="flex items-center gap-2 text-slate-300">
                              <span className="text-slate-400">
                                {msg.action.original.day} {msg.action.original.time || `${msg.action.original.start_time}–${msg.action.original.end_time}`}
                              </span>
                              <ArrowRightIcon className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                              <span className="font-semibold text-emerald-400">
                                {msg.action.target.day} {msg.action.target.time || `${msg.action.target.start_time}–${msg.action.target.end_time}`}
                              </span>
                            </div>
                            {msg.action.original.location && (
                              <div className="flex items-center gap-1 text-[11px] text-slate-400">
                                <MapPinIcon className="w-3 h-3 text-slate-500" />
                                {msg.action.original.location}
                              </div>
                            )}
                          </div>
                        )}

                        {/* N6 Impact Analysis Badges (if timetable_change) */}
                        {msg.action.impact_summary && (
                          <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2 text-xs">
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-slate-300 flex items-center gap-1">
                                <ShieldCheckIcon className="w-3.5 h-3.5 text-indigo-400" />
                                N6 Impact Analysis:
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  msg.action.impact_summary.severity === 'LOW'
                                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                    : msg.action.impact_summary.severity === 'MEDIUM'
                                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                    : 'bg-red-500/20 text-red-300 border border-red-500/30'
                                }`}
                              >
                                {msg.action.impact_summary.severity} SEVERITY
                              </span>
                            </div>

                            <div className="grid grid-cols-3 gap-1.5 text-[11px]">
                              <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 text-center">
                                <div className="font-bold text-white">
                                  {msg.action.impact_summary.students_affected_count ?? 0}
                                </div>
                                <div className="text-[10px] text-slate-400">Students</div>
                              </div>
                              <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 text-center">
                                <div className="font-bold text-white">
                                  {msg.action.impact_summary.new_conflicts_count ?? 0}
                                </div>
                                <div className="text-[10px] text-slate-400">New Conflicts</div>
                              </div>
                              <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 text-center">
                                <div className="font-bold text-white">
                                  {msg.action.impact_summary.work_shift_conflicts_count ?? 0}
                                </div>
                                <div className="text-[10px] text-slate-400">Shift Clashes</div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Safety & Constraint Checks */}
                        {msg.action.checks && msg.action.checks.length > 0 && (
                          <div className="space-y-1 pt-1">
                            <p className="text-[11px] font-medium text-slate-400">Deterministic Safety Checks:</p>
                            {msg.action.checks.map((check, chkIdx) => (
                              <div key={chkIdx} className="flex items-center gap-1.5 text-xs">
                                {check.warning ? (
                                  <ExclamationTriangleIcon className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                                ) : check.passed ? (
                                  <CheckCircleIcon className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                                ) : (
                                  <XMarkIcon className="w-3.5 h-3.5 text-red-400 shrink-0" />
                                )}
                                <span
                                  className={
                                    check.warning
                                      ? 'text-amber-300'
                                      : check.passed
                                      ? 'text-slate-300'
                                      : 'text-red-300'
                                  }
                                >
                                  {check.label}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Status Messages */}
                        {msg.confirmError && (
                          <div className="p-2 rounded-lg bg-red-950/60 border border-red-800 text-xs text-red-300">
                            {msg.confirmError}
                          </div>
                        )}

                        {msg.confirmSuccess && (
                          <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800 text-xs text-emerald-300 font-medium flex items-center gap-1.5">
                            <CheckCircleIcon className="w-4 h-4 text-emerald-400" />
                            {msg.confirmSuccess}
                          </div>
                        )}

                        {/* Actions buttons */}
                        {!msg.confirmed && (
                          <div className="flex items-center justify-end gap-2 pt-1.5">
                            <button
                              onClick={() => handleCancelAction(msg.id)}
                              disabled={msg.isConfirming}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleConfirmAction(msg.id, msg.action!)}
                              disabled={msg.isConfirming}
                              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-700/20 transition flex items-center gap-1.5 disabled:opacity-50"
                            >
                              {msg.isConfirming ? (
                                <>
                                  <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" />
                                  Applying...
                                </>
                              ) : (
                                'Confirm & Apply'
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
                </div>
              ))}

              {/* Loading indicator */}
              {isLoading && (
                <div className="flex items-start gap-2 text-slate-400 text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center gap-2 shadow-sm">
                    <ArrowPathIcon className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                    <span>{loadingStateText}</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Quick Starter Suggestion Chips */}
            <div className="px-3 py-2 bg-slate-950/50 border-t border-slate-800/60 overflow-x-auto flex items-center gap-1.5 no-scrollbar">
              {suggestions.map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(chip)}
                  disabled={isLoading}
                  className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-slate-800/70 hover:bg-indigo-600/30 border border-slate-700 hover:border-indigo-500/40 text-slate-300 hover:text-white whitespace-nowrap transition disabled:opacity-50"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="p-3 border-t border-slate-800 bg-slate-950/80 flex items-center gap-2"
            >
              <input
                ref={inputRef}
                id="syncshift-assistant-input"
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  userRole === 'admin'
                    ? 'Ask about room vacancies, timetable drafts, or impact...'
                    : 'Ask about your schedule, shifts, or study sessions...'
                }
                disabled={isLoading}
                className="flex-1 px-3.5 py-2.5 bg-slate-900 border border-slate-700/80 focus:border-indigo-500 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || isLoading}
                className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white transition shadow-md shadow-indigo-600/20 disabled:shadow-none"
                aria-label="Send message"
              >
                <PaperAirplaneIcon className="w-4 h-4" />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
