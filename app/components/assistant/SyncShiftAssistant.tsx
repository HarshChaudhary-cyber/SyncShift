'use client';

import React, { useState, useRef, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';
import AssistantTimetableUpload from './AssistantTimetableUpload';
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
  ChatBubbleLeftRightIcon,
  PlusIcon,
  TrashIcon,
  ShieldCheckIcon,
  BuildingLibraryIcon,
  AcademicCapIcon,
  PaperClipIcon,
} from '@heroicons/react/24/outline';
import {
  api,
  ActionPreview,
  AlternativeSlot,
  ToolProgressStep,
  AssistantChatResponse,
  AssistantConfirmResponse,
  AssistantConversationItem,
} from '@/lib/api';
import { isProfessor } from '@/lib/academic';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  action?: ActionPreview | null;
  choices?: Record<string, any>[] | null;
  alternatives?: AlternativeSlot[] | null;
  tool_progress?: ToolProgressStep[] | null;
  confirmed?: boolean;
  isConfirming?: boolean;
  confirmError?: string | null;
  confirmSuccess?: string | null;
}

const STUDENT_SUGGESTIONS = [
  'What classes do I have today?',
  'Move my today work to tomorrow',
  'When can I work this week?',
  'Do I have any conflicts?',
  'How many work hours do I have left?',
  'Preview my weekly plan',
  'Find open study time slots',
];

const PROFESSOR_SUGGESTIONS = [
  'When are my teaching slots today?',
  'Show my scheduled office hours',
  'Check for conflicts with departmental meetings',
  'How many lecture hours are assigned this term?',
  'Find free slots for student consultations',
  'Summarize upcoming class lectures',
];

const ADMIN_SUGGESTIONS = [
  'Which rooms are available on Monday between 10:00 and 12:00?',
  'Show university timetable versions',
  'Who is affected by moving CS101?',
  'Create a new draft version for timetable',
  'Check for faculty teaching conflicts',
  'Inspect room capacity utilization',
];

export function openSyncShiftAssistant(prompt?: string) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('open-syncshift-assistant', { detail: { prompt } }));
  }
}

export default function SyncShiftAssistant() {
  const { user } = useAuthContext();
  return <ScopedAssistant key={user?.user_id ?? 'guest'} />;
}

function ScopedAssistant() {
  const { user, status } = useAuthContext();
  const pathname = usePathname();
  const [showUpload, setShowUpload] = useState(false);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStateText, setLoadingStateText] = useState<string>('Consulting schedule...');
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<AssistantConversationItem[]>([]);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [userRole, setUserRole] = useState<'student' | 'admin' | 'instructor'>('student');
  const [institutionId, setInstitutionId] = useState<number | null>(null);

  const lastFocusedElementRef = useRef<HTMLElement | null>(null);

  const isSuperAdmin = user?.institution_role === 'super_admin';
  const isAdmin = isSuperAdmin || userRole === 'admin';
  const isProf = isProfessor(user?.institution_role) || userRole === 'instructor';
  const effectiveRole: 'admin' | 'professor' | 'student' = isAdmin ? 'admin' : isProf ? 'professor' : 'student';

  const initialWelcomeText =
    effectiveRole === 'admin'
      ? "Welcome, Administrator! I'm your SyncShift assistant. Ask me about room availability, timetable versions, draft creation, or impact analyses. Every timetable modification requires your explicit review and confirmation."
      : effectiveRole === 'professor'
      ? "Welcome, Professor! I'm your SyncShift assistant. Ask me about your assigned lectures, free slots for office hours, preparation time, or conflict checks with university meetings."
      : "Hi! Ask me how to use SyncShift, inspect your schedule, or attach a timetable to import it. Say 'Move my today work to tomorrow' and I’ll move just today's work if it fits. Other changes may need a preview or more details.";

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

  // Listen for open-syncshift-assistant events, optionally carrying a suggested prompt
  useEffect(() => {
    const handleOpen = (e: Event) => {
      if (status === 'authenticated') {
        lastFocusedElementRef.current = document.activeElement as HTMLElement;
        setIsOpen(true);
        const customEvent = e as CustomEvent<{ prompt?: string }>;
        if (customEvent?.detail?.prompt) {
          setInputMessage(customEvent.detail.prompt);
          setTimeout(() => {
            inputRef.current?.focus();
          }, 50);
        }
      }
    };
    window.addEventListener('open-syncshift-assistant', handleOpen as EventListener);
    return () => window.removeEventListener('open-syncshift-assistant', handleOpen as EventListener);
  }, [status]);

  // Escape key handler for dialog accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  useEffect(() => {
    let active = true;
    if (status === 'authenticated') {
      api.getMyInstitutionStatus()
        .then((res) => {
          if (!active) return;
          setInstitutionId(res.membership?.institution_id ?? null);
          const r = res.membership?.role;
          if (r === 'admin' || r === 'super_admin') {
            setUserRole('admin');
          } else if (r === 'instructor' || r === 'faculty') {
            setUserRole('instructor');
          } else {
            setUserRole('student');
          }
        })
        .catch(() => {});
    }
    return () => {
      active = false;
    };
  }, [status, user?.user_id]);

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
    } else {
      if (lastFocusedElementRef.current && typeof lastFocusedElementRef.current.focus === 'function') {
        lastFocusedElementRef.current.focus();
      }
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
          effectiveRole === 'admin'
            ? 'Started a new administrator consultation. What would you like to inspect or plan?'
            : effectiveRole === 'professor'
            ? 'Started a new faculty consultation. What would you like to check today?'
            : 'Started a fresh conversation. What would you like to check in your schedule today?',
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
        setMessages(
          loaded.length > 0
            ? loaded
            : [
                {
                  id: 'empty',
                  sender: 'assistant',
                  text: 'Conversation resumed.',
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                },
              ]
        );
      }
    } catch {
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
        void loadConversations();
      }

      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        sender: 'assistant',
        text: response.message,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        action: response.action,
        choices: response.choices,
        alternatives: response.alternatives,
        tool_progress: response.tool_progress,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      if (response.schedule_changed) {
        window.dispatchEvent(new CustomEvent('syncshift:schedule-updated'));
      }
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
      prev.map((m) =>
        m.id === msgId ? { ...m, action: null, text: m.text + '\n\n*(Action cancelled by user)*' } : m
      )
    );
  };

  const handleSelectChoice = (choice: Record<string, any>) => {
    setInputMessage(`Move ${choice.title} on ${choice.day} to 4 PM`);
    inputRef.current?.focus();
  };

  const handleSelectSuggestion = (chip: string) => {
    setInputMessage(chip);
    inputRef.current?.focus();
  };

  // Render text with basic bold, bullet, and link formatting
  const renderFormattedText = (text: string) => {
    const lines = text.split('\n');
    return (
      <div className="space-y-1.5 text-xs sm:text-sm leading-relaxed">
        {lines.map((line, idx) => {
          if (!line.trim()) return <div key={idx} className="h-1" />;

          let parsedLine: React.ReactNode = line;
          if (line.includes('**')) {
            const parts = line.split('**');
            parsedLine = parts.map((part, pIdx) =>
              pIdx % 2 === 1 ? (
                <strong key={pIdx} className="font-semibold text-[var(--text-primary)]">
                  {part}
                </strong>
              ) : (
                part
              )
            );
          }

          if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
            return (
              <div key={idx} className="flex items-start gap-1.5 pl-1">
                <span className="text-indigo-600 dark:text-indigo-400 font-bold">•</span>
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

  const suggestions =
    effectiveRole === 'admin'
      ? ADMIN_SUGGESTIONS
      : effectiveRole === 'professor'
      ? PROFESSOR_SUGGESTIONS
      : STUDENT_SUGGESTIONS;

  const prefersReducedMotion =
    user?.reduced_motion ||
    (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  if (status !== 'authenticated') return null;

  return (
    <>
      {/* Live Region for Screen Readers */}
      <div aria-live="polite" className="sr-only">
        {isLoading ? loadingStateText : ''}
      </div>

      {/* Floating Assistant Panel Dialog */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            id="syncshift-assistant-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="syncshift-assistant-title"
            initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 20, scale: prefersReducedMotion ? 1 : 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: prefersReducedMotion ? 0 : 20, scale: prefersReducedMotion ? 1 : 0.95 }}
            transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.2 }}
            className="fixed bottom-4 sm:bottom-6 right-2 sm:right-6 z-50 w-[calc(100vw-1rem)] sm:w-[500px] max-h-[90vh] h-[660px] bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl shadow-2xl flex flex-col overflow-hidden text-[var(--text-primary)]"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3.5 border-b border-[var(--border-color)] bg-[var(--bg-secondary)]">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-xs">
                  {effectiveRole === 'admin' ? (
                    <BuildingLibraryIcon className="w-4 h-4" aria-hidden="true" />
                  ) : effectiveRole === 'professor' ? (
                    <AcademicCapIcon className="w-4 h-4" aria-hidden="true" />
                  ) : (
                    <SparklesIcon className="w-4 h-4" aria-hidden="true" />
                  )}
                </div>
                <div>
                  <h2
                    id="syncshift-assistant-title"
                    className="text-sm font-bold text-[var(--text-primary)] tracking-tight flex items-center gap-1.5"
                  >
                    SyncShift Assistant
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
                      {effectiveRole === 'admin' ? 'Admin' : effectiveRole === 'professor' ? 'Faculty' : 'Online'}
                    </span>
                  </h2>
                  <p className="text-[11px] text-[var(--text-muted)]">Timetables, schedule planning & guidance</p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {/* Past conversations button */}
                <button
                  type="button"
                  onClick={() => setShowHistory((prev) => !prev)}
                  className={`p-1.5 rounded-lg transition ${
                    showHistory
                      ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400'
                      : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
                  }`}
                  title="Past conversations"
                  aria-label="Past conversations"
                >
                  <ChatBubbleLeftRightIcon className="w-4 h-4" aria-hidden="true" />
                </button>

                {/* New Chat button */}
                <button
                  type="button"
                  onClick={handleStartNewChat}
                  className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] rounded-lg transition"
                  title="New conversation"
                  aria-label="New conversation"
                >
                  <PlusIcon className="w-4 h-4" aria-hidden="true" />
                </button>

                {/* Close button */}
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] rounded-lg transition"
                  title="Close Assistant"
                  aria-label="Close Assistant"
                >
                  <XMarkIcon className="w-5 h-5" aria-hidden="true" />
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
                  transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.15 }}
                  className="border-b border-[var(--border-color)] bg-[var(--bg-secondary)] overflow-hidden"
                >
                  <div className="p-3 max-h-48 overflow-y-auto space-y-1.5 custom-scrollbar">
                    <div className="flex items-center justify-between px-1 pb-1">
                      <span className="text-xs font-semibold text-[var(--text-secondary)]">Past Inquiries</span>
                      <button
                        type="button"
                        onClick={handleStartNewChat}
                        className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline font-medium flex items-center gap-1 cursor-pointer"
                      >
                        <PlusIcon className="w-3 h-3" aria-hidden="true" /> New
                      </button>
                    </div>

                    {conversations.length === 0 ? (
                      <p className="text-xs text-[var(--text-muted)] px-1 py-2 italic">No past conversations yet.</p>
                    ) : (
                      conversations.map((c) => (
                        <div
                          key={c.id}
                          onClick={() => handleSelectConversation(c.id)}
                          className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition ${
                            c.id === currentConversationId
                              ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                              : 'text-[var(--text-secondary)] hover:bg-[var(--bg-card)]'
                          }`}
                        >
                          <span className="truncate flex-1">{c.title || 'Conversation'}</span>
                          <button
                            type="button"
                            onClick={(e) => handleDeleteConversation(e, c.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 text-[var(--text-muted)] hover:text-rose-500 rounded transition"
                            title="Delete conversation"
                            aria-label={`Delete conversation ${c.title || ''}`}
                          >
                            <TrashIcon className="w-3.5 h-3.5" aria-hidden="true" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Chat Messages Feed */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-[var(--text-primary)] custom-scrollbar">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
                >
                  {/* Sender Bubble */}
                  <div
                    className={`max-w-[92%] rounded-2xl px-4 py-3 shadow-xs ${
                      msg.sender === 'user'
                        ? 'bg-indigo-600 text-white rounded-br-xs'
                        : 'bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-bl-xs'
                    }`}
                  >
                    {renderFormattedText(msg.text)}

                    {/* Ambiguous Choices */}
                    {msg.choices && msg.choices.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] space-y-2">
                        <p className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
                          Select which event to modify:
                        </p>
                        <div className="grid grid-cols-1 gap-1.5">
                          {msg.choices.map((choice, cIdx) => (
                            <button
                              key={cIdx}
                              type="button"
                              onClick={() => handleSelectChoice(choice)}
                              className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] hover:border-indigo-400 text-left text-xs transition cursor-pointer"
                            >
                              <span className="font-semibold text-[var(--text-primary)]">{choice.title}</span>
                              <span className="text-[var(--text-muted)]">
                                {choice.day} {choice.start_time}–{choice.end_time}
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Structured Action Preview Card */}
                    {msg.action && (
                      <div className="mt-3.5 p-3.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl space-y-3 shadow-xs">
                        <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
                          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                            <ClockIcon className="w-3.5 h-3.5" aria-hidden="true" /> Action Preview
                          </span>
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 font-medium">
                            Confirmation Required
                          </span>
                        </div>

                        {/* Title & Description */}
                        <div className="space-y-1 text-xs">
                          <p className="font-semibold text-[var(--text-primary)] text-sm">{msg.action.title}</p>
                          {msg.action.description && (
                            <p className="text-[var(--text-secondary)] text-xs">{msg.action.description}</p>
                          )}
                        </div>

                        {/* From -> To Preview if available */}
                        {msg.action.original && msg.action.target && (
                          <div className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs space-y-1">
                            <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                              <span>
                                {msg.action.original.day}{' '}
                                {msg.action.original.time ||
                                  `${msg.action.original.start_time}–${msg.action.original.end_time}`}
                              </span>
                              <ArrowRightIcon className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" aria-hidden="true" />
                              <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                                {msg.action.target.day}{' '}
                                {msg.action.target.time ||
                                  `${msg.action.target.start_time}–${msg.action.target.end_time}`}
                              </span>
                            </div>
                            {msg.action.original.location && (
                              <div className="flex items-center gap-1 text-[11px] text-[var(--text-muted)]">
                                <MapPinIcon className="w-3 h-3" aria-hidden="true" />
                                {msg.action.original.location}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Impact Analysis Badges (if timetable_change) */}
                        {msg.action.impact_summary && (
                          <div className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-2 text-xs">
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-[var(--text-secondary)] flex items-center gap-1">
                                <ShieldCheckIcon className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" aria-hidden="true" />
                                Impact Analysis:
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  msg.action.impact_summary.severity === 'LOW'
                                    ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                                    : msg.action.impact_summary.severity === 'MEDIUM'
                                    ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                                    : 'bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                                }`}
                              >
                                {msg.action.impact_summary.severity} SEVERITY
                              </span>
                            </div>

                            <div className="grid grid-cols-3 gap-1.5 text-[11px]">
                              <div className="p-1.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-center">
                                <div className="font-bold text-[var(--text-primary)]">
                                  {msg.action.impact_summary.students_affected_count ?? 0}
                                </div>
                                <div className="text-[10px] text-[var(--text-muted)]">Students</div>
                              </div>
                              <div className="p-1.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-center">
                                <div className="font-bold text-[var(--text-primary)]">
                                  {msg.action.impact_summary.new_conflicts_count ?? 0}
                                </div>
                                <div className="text-[10px] text-[var(--text-muted)]">New Conflicts</div>
                              </div>
                              <div className="p-1.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-center">
                                <div className="font-bold text-[var(--text-primary)]">
                                  {msg.action.impact_summary.work_shift_conflicts_count ?? 0}
                                </div>
                                <div className="text-[10px] text-[var(--text-muted)]">Shift Clashes</div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Safety & Constraint Checks */}
                        {msg.action.checks && msg.action.checks.length > 0 && (
                          <div className="space-y-1 pt-1">
                            <p className="text-[11px] font-medium text-[var(--text-muted)]">Safety & Rule Checks:</p>
                            {msg.action.checks.map((check, chkIdx) => (
                              <div key={chkIdx} className="flex items-center gap-1.5 text-xs">
                                {check.warning ? (
                                  <ExclamationTriangleIcon className="w-3.5 h-3.5 text-amber-500 shrink-0" aria-hidden="true" />
                                ) : check.passed ? (
                                  <CheckCircleIcon className="w-3.5 h-3.5 text-emerald-500 shrink-0" aria-hidden="true" />
                                ) : (
                                  <XMarkIcon className="w-3.5 h-3.5 text-rose-500 shrink-0" aria-hidden="true" />
                                )}
                                <span
                                  className={
                                    check.warning
                                      ? 'text-amber-700 dark:text-amber-300'
                                      : check.passed
                                      ? 'text-[var(--text-secondary)]'
                                      : 'text-rose-700 dark:text-rose-300'
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
                          <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-xs text-rose-700 dark:text-rose-300">
                            {msg.confirmError}
                          </div>
                        )}

                        {msg.confirmSuccess && (
                          <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-700 dark:text-emerald-300 font-medium flex items-center gap-1.5">
                            <CheckCircleIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                            {msg.confirmSuccess}
                          </div>
                        )}

                        {/* Actions buttons */}
                        {!msg.confirmed && (
                          <div className="flex items-center justify-end gap-2 pt-1.5">
                            <button
                              type="button"
                              onClick={() => handleCancelAction(msg.id)}
                              disabled={msg.isConfirming}
                              className="px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition disabled:opacity-50 cursor-pointer"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={() => handleConfirmAction(msg.id, msg.action!)}
                              disabled={msg.isConfirming}
                              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs transition flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                            >
                              {msg.isConfirming ? (
                                <>
                                  <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
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

                  {/* Tool Progress Badges */}
                  {msg.tool_progress && msg.tool_progress.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {msg.tool_progress.map((step, tIdx) => (
                        <span
                          key={tIdx}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-muted)]"
                        >
                          {step.status === 'success' ? (
                            <CheckCircleIcon className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                          ) : step.status === 'error' ? (
                            <XMarkIcon className="w-2.5 h-2.5 text-rose-600 dark:text-rose-400" aria-hidden="true" />
                          ) : (
                            <ArrowPathIcon className="w-2.5 h-2.5 animate-spin text-indigo-600 dark:text-indigo-400" aria-hidden="true" />
                          )}
                          {step.label || step.tool}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Conflict-Free Alternatives Panel */}
                  {msg.alternatives && msg.alternatives.length > 0 && (
                    <div className="mt-2 p-3 rounded-xl bg-[var(--bg-card)] border border-amber-300 dark:border-amber-700/60 space-y-2">
                      <p className="text-[11px] font-semibold text-amber-800 dark:text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                        <CalendarIcon className="w-3.5 h-3.5" aria-hidden="true" />
                        Conflict-Free Alternatives
                      </p>
                      <div className="space-y-1.5">
                        {msg.alternatives.map((alt) => (
                          <button
                            key={alt.option_number}
                            type="button"
                            onClick={() =>
                              handleSendMessage(
                                `Apply Option ${alt.option_number}: ${alt.day_name} ${alt.start_time}–${alt.end_time}`
                              )
                            }
                            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-400 text-left transition group cursor-pointer"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] font-bold text-indigo-600 dark:text-indigo-400 group-hover:underline">
                                {alt.option_label}
                              </span>
                              <span className="text-xs text-[var(--text-primary)] font-semibold">
                                {alt.day_name}
                              </span>
                              <span className="text-xs text-[var(--text-secondary)]">
                                {alt.start_time}–{alt.end_time}
                              </span>
                            </div>
                            <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
                              <ClockIcon className="w-3 h-3" aria-hidden="true" />
                              {alt.duration_minutes}m
                              <ArrowRightIcon className="w-3 h-3 text-indigo-600 dark:text-indigo-400 ml-1" aria-hidden="true" />
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <span className="text-[10px] text-[var(--text-muted)] mt-1 px-1">{msg.timestamp}</span>
                </div>
              ))}

              {/* Loading indicator */}
              {isLoading && (
                <div className="flex items-start gap-2 text-[var(--text-secondary)] text-xs">
                  <div className="p-2.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-center gap-2 shadow-2xs">
                    <ArrowPathIcon className="w-3.5 h-3.5 animate-spin text-indigo-600 dark:text-indigo-400" aria-hidden="true" />
                    <span>{loadingStateText}</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Quick Starter Suggestion Chips - clicking populates the prompt for review */}
            <div className="px-3 py-2 bg-[var(--bg-secondary)] border-t border-[var(--border-color)] overflow-x-auto flex items-center gap-1.5 no-scrollbar">
              {suggestions.map((chip, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectSuggestion(chip)}
                  disabled={isLoading}
                  title="Click to place prompt in input"
                  className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-[var(--bg-card)] hover:bg-indigo-50 dark:hover:bg-indigo-950/40 border border-[var(--border-color)] hover:border-indigo-400 text-[var(--text-secondary)] hover:text-indigo-600 dark:hover:text-indigo-300 whitespace-nowrap transition disabled:opacity-50 cursor-pointer shadow-2xs"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Timetable upload drawer */}
            {showUpload && (
              <AssistantTimetableUpload
                onClose={() => setShowUpload(false)}
                onDone={(text) => {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: `import-${Date.now()}`,
                      sender: 'assistant',
                      text,
                      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    },
                  ]);
                  setShowUpload(false);
                }}
              />
            )}

            {/* Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="p-3 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] flex items-center gap-2"
            >
              <button
                type="button"
                aria-label="Attach timetable"
                title="Attach timetable"
                disabled={isLoading}
                onClick={() => setShowUpload(!showUpload)}
                className="p-2 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 rounded-xl hover:bg-[var(--bg-card)] transition cursor-pointer"
              >
                <PaperClipIcon className="w-5 h-5" aria-hidden="true" />
              </button>
              <input
                ref={inputRef}
                id="syncshift-assistant-input"
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  effectiveRole === 'admin'
                    ? 'Ask about room vacancies, timetable drafts, or impact...'
                    : effectiveRole === 'professor'
                    ? 'Ask about teaching slots, office hours, or preparations...'
                    : 'Ask about your schedule, shifts, or study sessions...'
                }
                disabled={isLoading}
                className="flex-1 px-3.5 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] focus:border-indigo-500 rounded-xl text-xs sm:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-indigo-500 transition shadow-2xs"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || isLoading}
                className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-[var(--bg-card)] text-white disabled:text-[var(--text-muted)] transition shadow-sm disabled:shadow-none cursor-pointer"
                aria-label="Send message"
              >
                <PaperAirplaneIcon className="w-4 h-4" aria-hidden="true" />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
