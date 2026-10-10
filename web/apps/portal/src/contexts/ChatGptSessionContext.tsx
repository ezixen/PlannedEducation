/**
 * Shared ChatGPT session context for teachers (ported from EasyLegalAid).
 * Manages OpenAI device-code sign-in, model/reasoning/verbosity preferences, and encrypted session history.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { apiClient } from '../api';
import { useAuth } from './AuthContext';

export interface ChatGptChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatGptModelOption {
  id: string;
  label: string;
  context_window?: number | null;
  reasoning_efforts: string[];
  default_reasoning_effort?: string | null;
}

export interface ChatGptOptionsResponse {
  models: ChatGptModelOption[];
  default_model: string;
  reasoning_efforts: string[];
  verbosity_levels: string[];
  default_reasoning_effort: string;
  default_verbosity: string;
  source: string;
}

export interface ChatGptUserPreferences {
  model: string;
  reasoningEffort: string;
  verbosity: string;
}

const PREFS_STORAGE_KEY = 'pe.chatgpt.preferences.v1';

export const DEFAULT_CHATGPT_PREFERENCES: ChatGptUserPreferences = {
  model: 'gpt-5.4-mini',
  reasoningEffort: 'medium',
  verbosity: 'medium',
};

function loadChatGptPreferences(): ChatGptUserPreferences {
  try {
    const raw = localStorage.getItem(PREFS_STORAGE_KEY);
    if (!raw) return { ...DEFAULT_CHATGPT_PREFERENCES };
    const parsed = JSON.parse(raw);
    return {
      model: typeof parsed.model === 'string' && parsed.model ? parsed.model : DEFAULT_CHATGPT_PREFERENCES.model,
      reasoningEffort:
        typeof parsed.reasoningEffort === 'string' && parsed.reasoningEffort
          ? parsed.reasoningEffort
          : DEFAULT_CHATGPT_PREFERENCES.reasoningEffort,
      verbosity:
        typeof parsed.verbosity === 'string' && parsed.verbosity
          ? parsed.verbosity
          : DEFAULT_CHATGPT_PREFERENCES.verbosity,
    };
  } catch {
    return { ...DEFAULT_CHATGPT_PREFERENCES };
  }
}

function saveChatGptPreferences(prefs: ChatGptUserPreferences): void {
  try {
    localStorage.setItem(PREFS_STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Ignore storage quota errors
  }
}

export interface ChatGptSessionContextValue {
  connected: boolean;
  accountId: string | null;
  history: ChatGptChatMessage[];
  loading: boolean;
  error: string | null;
  setError: (value: string | null) => void;
  options: ChatGptOptionsResponse | null;
  prefs: ChatGptUserPreferences;
  updatePrefs: (patch: Partial<ChatGptUserPreferences>) => void;
  selectedModel: ChatGptModelOption | null;
  reasoningChoices: string[];
  verbosityChoices: string[];
  loginId: string | null;
  userCode: string | null;
  verificationUri: string | null;
  verificationUriComplete: string | null;
  showDeviceLogin: boolean;
  codeCopied: boolean;
  loadOptions: (refresh?: boolean) => Promise<void>;
  refreshSession: () => Promise<void>;
  startDeviceLogin: () => Promise<void>;
  openDevicePage: () => void;
  copyUserCode: () => Promise<void>;
  onClearHistory: () => Promise<void>;
  onLogout: () => Promise<void>;
  sendMessage: (message: string, instructions?: string) => Promise<boolean>;
}

const ChatGptSessionContext = createContext<ChatGptSessionContextValue | null>(null);

export function useChatGptSession(): ChatGptSessionContextValue {
  const value = useContext(ChatGptSessionContext);
  if (!value) {
    throw new Error('useChatGptSession requires ChatGptSessionProvider');
  }
  return value;
}

export function ChatGptSessionProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const isTeacher = Boolean(user && user.role === 'teacher');

  const [connected, setConnected] = useState(false);
  const [accountId, setAccountId] = useState<string | null>(null);
  const [loginId, setLoginId] = useState<string | null>(null);
  const [userCode, setUserCode] = useState<string | null>(null);
  const [verificationUri, setVerificationUri] = useState<string | null>(null);
  const [verificationUriComplete, setVerificationUriComplete] = useState<string | null>(null);
  const [history, setHistory] = useState<ChatGptChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<ChatGptOptionsResponse | null>(null);
  const [prefs, setPrefs] = useState<ChatGptUserPreferences>(() => loadChatGptPreferences());
  const [showDeviceLogin, setShowDeviceLogin] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);

  const pollTimer = useRef<number | null>(null);
  const pollInFlight = useRef(false);
  const activeLoginIdRef = useRef<string | null>(null);

  const selectedModel =
    options?.models.find((m) => m.id === prefs.model) ?? options?.models[0] ?? null;
  const reasoningChoices =
    selectedModel?.reasoning_efforts && selectedModel.reasoning_efforts.length > 0
      ? selectedModel.reasoning_efforts
      : options?.reasoning_efforts ?? ['none', 'low', 'medium', 'high'];
  const verbosityChoices = options?.verbosity_levels ?? ['low', 'medium', 'high'];

  const applyOptions = useCallback((snapshot: ChatGptOptionsResponse) => {
    setOptions(snapshot);
    setPrefs((current) => {
      const stored = { ...DEFAULT_CHATGPT_PREFERENCES, ...current };
      const autoReview = snapshot.models.find((m) =>
        /auto[- ]?review/i.test(`${m.id} ${m.label}`),
      );
      const modelExists = snapshot.models.some((m) => m.id === stored.model);
      const next: ChatGptUserPreferences = {
        model: autoReview?.id || (modelExists ? stored.model : snapshot.default_model),
        reasoningEffort: stored.reasoningEffort || snapshot.default_reasoning_effort,
        verbosity: stored.verbosity || snapshot.default_verbosity,
      };
      const selected = snapshot.models.find((m) => m.id === next.model);
      if (
        selected?.default_reasoning_effort &&
        !selected.reasoning_efforts?.includes(next.reasoningEffort)
      ) {
        next.reasoningEffort = selected.default_reasoning_effort;
      }
      saveChatGptPreferences(next);
      return next;
    });
  }, []);

  const loadOptions = useCallback(
    async (refresh = false) => {
      if (!isTeacher) return;
      try {
        const res = await apiClient.get<ChatGptOptionsResponse>('/chatgpt/options', {
          params: refresh ? { refresh: true } : undefined,
        });
        applyOptions(res.data);
      } catch {
        // Keep prior options if refresh fails
      }
    },
    [applyOptions, isTeacher],
  );

  const updatePrefs = useCallback((patch: Partial<ChatGptUserPreferences>) => {
    setPrefs((current) => {
      const next = { ...current, ...patch };
      saveChatGptPreferences(next);
      return next;
    });
  }, []);

  const refreshSession = useCallback(async () => {
    if (!isTeacher) {
      setConnected(false);
      setAccountId(null);
      setHistory([]);
      return;
    }
    try {
      const res = await apiClient.get<{ connected: boolean; account_id?: string | null }>(
        '/chatgpt/session',
      );
      setConnected(res.data.connected);
      setAccountId(res.data.account_id ?? null);
      if (res.data.connected) {
        const histRes = await apiClient.get<{ messages: ChatGptChatMessage[] }>('/chatgpt/history');
        setHistory(histRes.data.messages || []);
      }
    } catch {
      setConnected(false);
      setAccountId(null);
    }
  }, [isTeacher]);

  useEffect(() => {
    void refreshSession();
    void loadOptions(false);
  }, [refreshSession, loadOptions]);

  useEffect(() => {
    return () => {
      if (pollTimer.current) {
        window.clearInterval(pollTimer.current);
      }
    };
  }, []);

  const openDevicePage = useCallback(() => {
    const target = verificationUriComplete || verificationUri;
    if (!target) return;
    window.open(target, '_blank', 'noopener,noreferrer');
  }, [verificationUri, verificationUriComplete]);

  const copyUserCode = useCallback(async () => {
    if (!userCode) return;
    try {
      await navigator.clipboard.writeText(userCode);
      setCodeCopied(true);
      window.setTimeout(() => setCodeCopied(false), 2000);
    } catch {
      setCodeCopied(false);
    }
  }, [userCode]);

  const startDeviceLogin = useCallback(async () => {
    if (pollTimer.current) {
      window.clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    pollInFlight.current = false;
    activeLoginIdRef.current = null;
    setError(null);
    setCodeCopied(false);
    setUserCode(null);
    setVerificationUri(null);
    setVerificationUriComplete(null);
    setLoginId(null);
    setShowDeviceLogin(true);
    setLoading(true);
    try {
      const res = await apiClient.post<{
        login_id: string;
        user_code: string;
        verification_uri: string;
        verification_uri_complete?: string | null;
        interval_seconds: number;
      }>('/chatgpt/login/start');
      const started = res.data;
      activeLoginIdRef.current = started.login_id;
      setLoginId(started.login_id);
      setUserCode(started.user_code);
      setVerificationUri(started.verification_uri);
      setVerificationUriComplete(started.verification_uri_complete ?? null);
      const intervalMs = Math.max(2500, Math.round((started.interval_seconds || 5) * 1000));
      const currentLoginId = started.login_id;

      pollTimer.current = window.setInterval(async () => {
        if (pollInFlight.current || activeLoginIdRef.current !== currentLoginId) {
          return;
        }
        pollInFlight.current = true;
        try {
          const pollRes = await apiClient.post<{ status: string; detail?: string | null }>(
            '/chatgpt/login/poll',
            { login_id: currentLoginId },
          );
          const result = pollRes.data;
          if (activeLoginIdRef.current !== currentLoginId) return;
          if (result.status === 'complete') {
            if (pollTimer.current) {
              window.clearInterval(pollTimer.current);
              pollTimer.current = null;
            }
            activeLoginIdRef.current = null;
            setLoginId(null);
            setUserCode(null);
            setShowDeviceLogin(false);
            await refreshSession();
            await loadOptions(true);
          } else if (result.status === 'failed') {
            if (pollTimer.current) {
              window.clearInterval(pollTimer.current);
              pollTimer.current = null;
            }
            activeLoginIdRef.current = null;
            setLoginId(null);
            setError(result.detail || 'ChatGPT sign-in failed.');
          }
        } catch (err: any) {
          if (pollTimer.current) {
            window.clearInterval(pollTimer.current);
            pollTimer.current = null;
          }
          activeLoginIdRef.current = null;
          setLoginId(null);
          setError(err.response?.data?.detail || err.message || 'ChatGPT sign-in failed.');
        } finally {
          pollInFlight.current = false;
        }
      }, intervalMs);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Could not start ChatGPT sign-in.');
    } finally {
      setLoading(false);
    }
  }, [loadOptions, refreshSession]);

  const onClearHistory = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      await apiClient.delete('/chatgpt/history');
      setHistory([]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Could not clear history.');
    } finally {
      setLoading(false);
    }
  }, []);

  const onLogout = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      await apiClient.post('/chatgpt/logout');
      setConnected(false);
      setAccountId(null);
      setHistory([]);
      setUserCode(null);
      setLoginId(null);
      setShowDeviceLogin(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Could not disconnect ChatGPT.');
    } finally {
      setLoading(false);
    }
  }, []);

  const sendMessage = useCallback(
    async (rawMessage: string, instructions?: string): Promise<boolean> => {
      const message = rawMessage.trim();
      if (!message) return false;
      const priorHistory = history;
      const nextHistory: ChatGptChatMessage[] = [...priorHistory, { role: 'user', content: message }];
      setHistory(nextHistory);
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.post<{ reply: string }>('/chatgpt/chat', {
          message,
          history: priorHistory,
          instructions: instructions || undefined,
          model: prefs.model,
          reasoning_effort: prefs.reasoningEffort,
          verbosity: prefs.verbosity,
        });
        const updated: ChatGptChatMessage[] = [
          ...nextHistory,
          { role: 'assistant', content: res.data.reply },
        ];
        setHistory(updated);
        return true;
      } catch (err: any) {
        setHistory(priorHistory);
        setError(err.response?.data?.detail || err.message || 'ChatGPT could not answer.');
        return false;
      } finally {
        setLoading(false);
      }
    },
    [history, prefs.model, prefs.reasoningEffort, prefs.verbosity],
  );

  const value = useMemo<ChatGptSessionContextValue>(
    () => ({
      connected,
      accountId,
      history,
      loading,
      error,
      setError,
      options,
      prefs,
      updatePrefs,
      selectedModel,
      reasoningChoices,
      verbosityChoices,
      loginId,
      userCode,
      verificationUri,
      verificationUriComplete,
      showDeviceLogin,
      codeCopied,
      loadOptions,
      refreshSession,
      startDeviceLogin,
      openDevicePage,
      copyUserCode,
      onClearHistory,
      onLogout,
      sendMessage,
    }),
    [
      connected,
      accountId,
      history,
      loading,
      error,
      options,
      prefs,
      updatePrefs,
      selectedModel,
      reasoningChoices,
      verbosityChoices,
      loginId,
      userCode,
      verificationUri,
      verificationUriComplete,
      showDeviceLogin,
      codeCopied,
      loadOptions,
      refreshSession,
      startDeviceLogin,
      openDevicePage,
      copyUserCode,
      onClearHistory,
      onLogout,
      sendMessage,
    ],
  );

  return <ChatGptSessionContext.Provider value={value}>{children}</ChatGptSessionContext.Provider>;
}
