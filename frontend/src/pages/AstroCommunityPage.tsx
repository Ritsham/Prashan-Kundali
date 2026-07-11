import React from 'react';
import {
  AtSign,
  Bell,
  Bookmark,
  ChevronDown,
  Hash,
  Image,
  MessageSquare,
  Moon,
  MoreHorizontal,
  Plus,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Smile,
  Sun,
  Trash2,
  X,
  Zap,
} from 'lucide-react';
import './AstroCommunityPage.css';

type Channel = {
  id: string;
  name: string;
  group: string;
  description: string;
  locked?: boolean;
};

type MemberStatus = 'online' | 'away' | 'offline';

type ApiMessage = {
  id: string;
  channel_name?: string;
  sender_id?: string;
  user_name?: string;
  content?: string;
  image_base64?: string | null;
  content_type?: string;
  is_deleted?: boolean;
  stars?: number;
  created_at?: string;
  edited_at?: string | null;
};

type Message = {
  id: string;
  channelId: string;
  senderId?: string;
  author: string;
  time: string;
  body: string;
  contentType: string;
  adminPost?: {
    title?: string;
    body?: string;
    linkUrl?: string;
    linkLabel?: string;
  };
  imageBase64?: string | null;
  stars: number;
  replyCount?: number;
  isDeleted: boolean;
  edited: boolean;
};

type ThreadReply = Message;

type Profile = {
  user_id?: string;
  display_name?: string;
  username?: string;
  role?: string;
};

const channelMetadata: Record<string, Pick<Channel, 'group' | 'description' | 'locked'>> = {
  announcements: { group: 'Important', description: 'Admin updates and platform notices.' },
  'community-guidelines': { group: 'Important', description: 'Shared norms for respectful learning and case privacy.' },
  general: { group: 'General Community', description: 'Daily discussion for verified astrologers.' },
  introductions: { group: 'General Community', description: 'Meet practitioners and share your background.' },
  'general-discussion': { group: 'General Community', description: 'Open questions, observations, and peer review.' },
  'parashar-astrology': { group: 'Astrology Systems', description: 'Classical principles, yogas, dashas, and house judgement.' },
  'kp-astrology': { group: 'Astrology Systems', description: 'KP significators, ruling planets, and cuspal analysis.' },
  'jaimini-astrology': { group: 'Astrology Systems', description: 'Karakas, rashi drishti, padas, and chara dashas.' },
  'nadi-astrology': { group: 'Astrology Systems', description: 'Nadi combinations and research notes.' },
  'tajika-astrology': { group: 'Astrology Systems', description: 'Varshaphal, muntha, saham, and tajika yogas.' },
  'prashna-astrology': { group: 'Kundali and Prediction', description: 'Question charts, timing, and event judgement.' },
  'lagna-kundali': { group: 'Kundali and Prediction', description: 'Birth chart analysis and rectification support.' },
  'chart-discussions': { group: 'Kundali and Prediction', description: 'Share charts, compare methods, and discuss outcomes.' },
  'marriage-matching': { group: 'Kundali and Prediction', description: 'Compatibility, guna milan, and relationship timing.' },
  muhurta: { group: 'Kundali and Prediction', description: 'Electional astrology and auspicious timings.' },
  'case-studies': { group: 'Learning and Research', description: 'Anonymized cases, peer review, and documented predictions.' },
  'techniques-and-learning': { group: 'Learning and Research', description: 'Frameworks, lessons, and guided learning notes.' },
  'research-and-books': { group: 'Learning and Research', description: 'Texts, references, translations, and research papers.' },
};

const quickNav = [
  { label: 'Saved Messages', icon: Bookmark, count: 0 },
  { label: 'Search', icon: Search, count: 0 },
];

function StatusDot({ status }: { status: MemberStatus }) {
  return <span className={`astro-status-dot astro-status-${status}`} aria-label={`${status} status`} />;
}

function getToken() {
  return localStorage.getItem('supabase_token') || '';
}

function authHeaders(token: string) {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

function normalizeChannel(row: { id?: string; name?: string; slug?: string; category?: string; description?: string; is_read_only?: boolean }): Channel {
  const name = row.name || row.slug || row.id || 'channel';
  const metadata = channelMetadata[name] || { group: 'Channels', description: '' };
  return {
    id: name,
    name,
    group: row.category || metadata.group,
    description: row.description || metadata.description,
    locked: row.is_read_only ?? metadata.locked,
  };
}

function parseAdminPostContent(content?: any): Message['adminPost'] {
  if (!content) return undefined;

  try {
    const parsed = typeof content === 'string' ? JSON.parse(content) : content;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return undefined;

    const post = parsed as Record<string, unknown>;
    const hasAdminPostShape = ['title', 'body', 'link_url', 'link_label'].some((key) => key in post);
    if (!hasAdminPostShape) return undefined;

    const title = typeof post.title === 'string' ? post.title : '';
    const body = typeof post.body === 'string' ? post.body : '';
    const linkUrl = typeof post.link_url === 'string' ? post.link_url : '';
    const linkLabel = typeof post.link_label === 'string' ? post.link_label : linkUrl;

    return { title, body, linkUrl, linkLabel };
  } catch {
    return undefined;
  }
}

function mapMessage(row: ApiMessage, channelId: string): Message {
  const created = row.created_at ? new Date(row.created_at) : null;
  let contentType = row.content_type || 'STANDARD';
  let body = row.is_deleted ? 'This message was deleted.' : row.content || '';
  let adminPost: Message['adminPost'];

  if (row.content && !row.is_deleted) {
    adminPost = parseAdminPostContent(row.content);
    if (adminPost) {
      contentType = 'ADMIN_POST';
      body = adminPost.body || adminPost.title || adminPost.linkUrl || '';
    } else if (contentType === 'ADMIN_POST') {
      body = row.content;
    }
  }

  return {
    id: row.id,
    channelId: row.channel_name || channelId,
    senderId: row.sender_id,
    author: row.user_name || 'Astrologer',
    time: created && !Number.isNaN(created.getTime()) ? created.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
    body,
    contentType,
    adminPost,
    imageBase64: row.image_base64,
    stars: row.stars || 0,
    isDeleted: Boolean(row.is_deleted),
    edited: Boolean(row.edited_at),
  };
}

function isUuidLike(value?: string) {
  return Boolean(value && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value));
}

function displayAuthor(message: Message, currentUserName: string, currentUserId?: string) {
  if (message.senderId && currentUserId && message.senderId === currentUserId) return currentUserName;
  if (isUuidLike(message.author)) return currentUserName;
  return message.author;
}

function initials(name: string) {
  return name
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || 'A';
}

function groupChannels(channelList: Channel[]) {
  return channelList.reduce<Record<string, Channel[]>>((acc, channel) => {
    acc[channel.group] = [...(acc[channel.group] || []), channel];
    return acc;
  }, {});
}

function AstroCommunityPage() {
  const [channels, setChannels] = React.useState<Channel[]>([]);
  const [activeChannelId, setActiveChannelId] = React.useState('');
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [profile, setProfile] = React.useState<Profile | null>(null);
  const [draft, setDraft] = React.useState('');
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [channelQuery, setChannelQuery] = React.useState('');
  const [isChannelSearchOpen, setIsChannelSearchOpen] = React.useState(false);
  const [pendingAttachment, setPendingAttachment] = React.useState<{ name: string; dataUrl: string; kind: 'file' | 'image' } | null>(null);
  const [savedMessages, setSavedMessages] = React.useState<Set<string>>(() => new Set(JSON.parse(localStorage.getItem('community_saved_messages') || '[]')));
  const [savedMessageRows, setSavedMessageRows] = React.useState<Message[]>(() => {
    try { return JSON.parse(localStorage.getItem('community_saved_message_rows') || '[]'); } catch { return []; }
  });
  const [selectedThread, setSelectedThread] = React.useState<Message | null>(null);
  const [threadReplies, setThreadReplies] = React.useState<ThreadReply[]>([]);
  const [threadDraft, setThreadDraft] = React.useState('');
  const [loadingThread, setLoadingThread] = React.useState(false);
  const [sendingThread, setSendingThread] = React.useState(false);
  const [contextPanelOpen, setContextPanelOpen] = React.useState(false);
  const [threadViewActive, setThreadViewActive] = React.useState(false);
  const [myReactions, setMyReactions] = React.useState<Set<string>>(() => new Set(JSON.parse(localStorage.getItem('community_my_reactions') || '[]')));
  const threadRepliesRef = React.useRef<HTMLDivElement>(null);
  const [loadingChannels, setLoadingChannels] = React.useState(true);
  const [loadingMessages, setLoadingMessages] = React.useState(false);
  const [sending, setSending] = React.useState(false);
  const [error, setError] = React.useState('');
  const [connectionState, setConnectionState] = React.useState<'idle' | 'connecting' | 'connected' | 'offline'>('idle');
  const [onlineCount, setOnlineCount] = React.useState(0);
  const [theme, setTheme] = React.useState('dark');
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [compactMode, setCompactMode] = React.useState(() => localStorage.getItem('community_compact_mode') === 'true');
  const [notifySounds, setNotifySounds] = React.useState(() => localStorage.getItem('community_notify_sounds') !== 'false');
  const [showTimestamps, setShowTimestamps] = React.useState(() => localStorage.getItem('community_show_timestamps') !== 'false');
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const imageInputRef = React.useRef<HTMLInputElement>(null);
  const composerInputRef = React.useRef<HTMLInputElement>(null);
  const wsRef = React.useRef<WebSocket | null>(null);
  const messageListRef = React.useRef<HTMLDivElement>(null);
  const userIdRef = React.useRef<string | null>(null);

  const token = getToken();
  const activeChannel = channels.find((channel) => channel.id === activeChannelId);
  const searchedChannels = channelQuery.trim()
    ? channels.filter((channel) => `${channel.name} ${channel.group} ${channel.description}`.toLowerCase().includes(channelQuery.toLowerCase()))
    : channels;
  const groupedVisibleChannels = groupChannels(searchedChannels);
  const channelSavedMessages = savedMessageRows.filter((message) => message.channelId === activeChannelId);

  React.useEffect(() => {
    localStorage.setItem('community_saved_messages', JSON.stringify([...savedMessages]));
  }, [savedMessages]);

  React.useEffect(() => {
    if (savedMessageRows.length > 0) {
      localStorage.setItem('community_saved_message_rows', JSON.stringify(savedMessageRows));
    }
  }, [savedMessageRows]);

  React.useEffect(() => {
    localStorage.setItem('community_my_reactions', JSON.stringify([...myReactions]));
  }, [myReactions]);

  React.useEffect(() => {
    let cancelled = false;
    async function loadSavedMessages() {
      if (!token) return;
      try {
        const response = await fetch('/api/community/saved-messages', { headers: authHeaders(token) });
        // If server fails (e.g. DB table missing → 503), keep localStorage data intact
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled && Array.isArray(data)) {
          // Only update if server returned actual data (non-empty means DB is working)
          if (data.length > 0) {
            setSavedMessages(new Set(data.map((row: ApiMessage) => row.id).filter(Boolean)));
            setSavedMessageRows(data.map((row: ApiMessage) => mapMessage(row, row.channel_name || activeChannelId || 'saved')));
          }
          // If data is empty and we have localStorage data, keep localStorage (don't wipe it)
          // The user's saves are only cleared when they explicitly unsave
        }
      } catch {
        // Network error — local saved state remains as fallback
      }
    }
    loadSavedMessages();
    return () => { cancelled = true; };
  }, [token]);


  React.useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      if (!token) {
        setLoadingChannels(false);
        setError('Please sign in before opening Astro Community.');
        return;
      }

      try {
        setLoadingChannels(true);
        setError('');

        const [profileResponse, channelResponse] = await Promise.all([
          fetch('/api/community/profile', { headers: authHeaders(token) }),
          fetch('/api/community/channels', { headers: authHeaders(token) }),
        ]);

        if (!profileResponse.ok || !channelResponse.ok) {
          throw new Error('Unable to load community. Please check your access and sign in again.');
        }

        const profileData = await profileResponse.json();
        const channelData = await channelResponse.json();
        const normalizedChannels = Array.isArray(channelData)
          ? channelData.map(normalizeChannel).filter((channel) => channel.id !== 'community-guidelines')
          : [];

        if (cancelled) return;
        setProfile(profileData);
        setChannels(normalizedChannels);
        setActiveChannelId((current) => current || normalizedChannels[0]?.id || '');
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : 'Unable to load community.');
          setChannels([]);
        }
      } finally {
        if (!cancelled) setLoadingChannels(false);
      }
    }

    loadInitialData();
    return () => {
      cancelled = true;
    };
  }, [token]);

  React.useEffect(() => {
    let cancelled = false;

    async function loadMessages() {
      if (!activeChannelId || !token) {
        setMessages([]);
        return;
      }

      try {
        setLoadingMessages(true);
        setError('');
        const response = await fetch(`/api/community/messages/${encodeURIComponent(activeChannelId)}`, {
          headers: authHeaders(token),
        });

        if (!response.ok) throw new Error('Unable to load messages for this channel.');

        const data = await response.json();
        if (!cancelled) {
          setMessages(Array.isArray(data) ? data.map((row) => mapMessage(row, activeChannelId)) : []);
        }
      } catch (exc) {
        if (!cancelled) {
          setMessages([]);
          setError(exc instanceof Error ? exc.message : 'Unable to load messages.');
        }
      } finally {
        if (!cancelled) setLoadingMessages(false);
      }
    }

    loadMessages();
    return () => {
      cancelled = true;
    };
  }, [activeChannelId, token]);

  React.useEffect(() => {
    wsRef.current?.close();
    wsRef.current = null;

    if (!activeChannelId || !token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/api/community/ws/${encodeURIComponent(activeChannelId)}?token=${encodeURIComponent(token)}`);
    wsRef.current = socket;
    setConnectionState('connecting');

    socket.onopen = () => setConnectionState('connected');
    socket.onclose = () => setConnectionState('offline');
    socket.onerror = () => setConnectionState('offline');
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const row = payload.data || payload.message;
        if ((payload.type === 'new_message' || payload.type === 'message_created') && row?.id) {
          const next = mapMessage(row, activeChannelId);
          setMessages((current) => {
            if (current.some((message) => message.id === next.id)) return current;
            if (localStorage.getItem('community_notify_sounds') !== 'false' && next.senderId !== userIdRef.current) {
              try {
                const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(440, audioCtx.currentTime);
                gainNode.gain.setValueAtTime(0.05, audioCtx.currentTime);
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.start();
                oscillator.stop(audioCtx.currentTime + 0.1);
              } catch (e) {
                // Ignore audio errors
              }
            }
            return [...current, next];
          });
        }
        if (payload.type === 'message_updated' && row?.id) {
          const next = mapMessage(row, activeChannelId);
          setMessages((current) => current.map((message) => (message.id === next.id ? next : message)));
        }
        if (payload.type === 'message_deleted' && payload.message_id) {
          setMessages((current) => current.map((message) => message.id === payload.message_id ? { ...message, isDeleted: true, body: row?.content || 'This message was deleted.', imageBase64: null } : message));
        }
        if ((payload.type === 'message_starred' || payload.type === 'reaction_added') && payload.message_id) {
          setMessages((current) => current.map((message) => message.id === payload.message_id ? { ...message, stars: message.stars + 1 } : message));
        }
        if (payload.type === 'reaction_removed' && payload.message_id) {
          setMessages((current) => current.map((message) => message.id === payload.message_id ? { ...message, stars: Math.max(0, message.stars - 1) } : message));
        }
        if (payload.type === 'thread_reply_created' && payload.parent_message_id && row?.id) {
          const next = mapMessage(row, activeChannelId);
          if (selectedThread?.id === payload.parent_message_id) {
            setThreadReplies((current) => (current.some((reply) => reply.id === next.id) ? current : [...current, next as ThreadReply]));
          }
          setMessages((current) => current.map((message) => message.id === payload.parent_message_id ? { ...message, replyCount: (message.replyCount || 0) + 1 } : message));
        }
        if (payload.type === 'online_count') {
          setOnlineCount(payload.count || 0);
        }
      } catch (err) {
        console.error('Error parsing WS message:', err);
      }
    };

    return () => socket.close();
  }, [activeChannelId, token, selectedThread?.id]);

  React.useEffect(() => {
    setSelectedThread(null);
    setThreadReplies([]);
    setThreadDraft('');
    setContextPanelOpen(false);
    setThreadViewActive(false);
  }, [activeChannelId]);

  React.useEffect(() => {
    const list = threadRepliesRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [threadReplies.length]);

  React.useEffect(() => {
    const list = messageListRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages.length, activeChannelId]);

  React.useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || !activeChannelId || !token) return;
    fetch(`/api/community/channels/${encodeURIComponent(activeChannelId)}/read`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify({ last_read_message_id: lastMessage.id }),
    }).catch(() => undefined);
  }, [messages, activeChannelId, token]);

  const handleSend = async (event: React.FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    // Block sending in announcements channel — only admins can post there
    if (activeChannelId === 'announcements') return;
    if ((!content && !pendingAttachment) || !activeChannelId || !token || sending) return;

    try {
      setSending(true);
      setError('');
      
      const payload = {
        action: 'send_message',
        content,
        content_type: pendingAttachment ? (pendingAttachment.kind === 'image' ? 'IMAGE' : 'ATTACHMENT') : 'STANDARD',
        image_base64: pendingAttachment?.dataUrl || null,
        client_id: crypto.randomUUID?.() || `${Date.now()}`,
      };

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(payload));
        setDraft('');
        setPendingAttachment(null);
        setSending(false);
        return;
      }

      const response = await fetch(`/api/community/messages/${encodeURIComponent(activeChannelId)}`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({
          content,
          content_type: pendingAttachment ? (pendingAttachment.kind === 'image' ? 'IMAGE' : 'ATTACHMENT') : 'STANDARD',
          image_base64: pendingAttachment?.dataUrl || null,
          client_id: crypto.randomUUID?.() || `${Date.now()}`,
        }),
      });

      if (!response.ok) throw new Error('Message could not be sent.');

      const result = await response.json();
      if (result?.message?.id) {
        const sent = mapMessage(result.message, activeChannelId);
        setMessages((current) => (current.some((message) => message.id === sent.id) ? current : [...current, sent]));
      }

      setDraft('');
      setPendingAttachment(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Message could not be sent.');
    } finally {
      setSending(false);
    }
  };

  const toggleReaction = async (messageId: string, reaction: string) => {
    if (!token) return;
    // Each user can only react once per message
    if (myReactions.has(messageId)) return;
    setMyReactions((current) => new Set([...current, messageId]));
    setMessages((current) => current.map((message) => message.id === messageId ? { ...message, stars: message.stars + 1 } : message));

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'toggle_reaction',
        message_id: messageId,
        reaction_type: reaction,
      }));
      return;
    }

    try {
      await fetch(`/api/community/messages/${encodeURIComponent(messageId)}/reactions`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ reaction_type: reaction }),
      });
    } catch {
      setMyReactions((current) => { const next = new Set(current); next.delete(messageId); return next; });
      setMessages((current) => current.map((message) => message.id === messageId ? { ...message, stars: Math.max(0, message.stars - 1) } : message));
    }
  };

  const toggleSaved = async (messageId: string) => {
    if (!token) return;
    const wasSaved = savedMessages.has(messageId);
    const message = messages.find((item) => item.id === messageId);

    // Optimistic update — immediately reflect in UI
    setSavedMessages((current) => {
      const next = new Set(current);
      if (wasSaved) next.delete(messageId);
      else next.add(messageId);
      return next;
    });
    setSavedMessageRows((current) => {
      const filtered = current.filter((item) => item.id !== messageId);
      if (!wasSaved && message) return [message, ...filtered];
      return filtered;
    });

    try {
      const response = await fetch(`/api/community/messages/${encodeURIComponent(messageId)}/save`, {
        method: 'POST',
        headers: authHeaders(token),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Unable to save message');
      }
      const result = await response.json();
      // Sync with server state
      setSavedMessages((current) => {
        const next = new Set(current);
        if (result.saved) next.add(messageId);
        else next.delete(messageId);
        return next;
      });
      setSavedMessageRows((current) => {
        const filtered = current.filter((item) => item.id !== messageId);
        if (result.saved && message) return [message, ...filtered];
        return filtered;
      });
    } catch (exc) {
      // Only show error — keep optimistic state so user can see saved in UI
      console.error('Save failed:', exc);
      // Silently keep the local save — it's already persisted to localStorage via the effect
    }
  };

  const openThread = async (message: Message) => {
    if (!token || message.isDeleted) return;
    setSelectedThread(message);
    setThreadViewActive(true);
    setContextPanelOpen(false);
    setLoadingThread(true);
    setThreadDraft('');
    setThreadReplies([]);
    try {
      const response = await fetch(`/api/community/messages/${encodeURIComponent(message.id)}/replies`, {
        headers: authHeaders(token),
      });
      if (!response.ok) throw new Error('Unable to load thread replies.');
      const data = await response.json();
      setThreadReplies(Array.isArray(data) ? data.map((row: ApiMessage) => mapMessage(row, message.channelId)) : []);
    } catch (exc) {
      setThreadReplies([]);
      setError(exc instanceof Error ? exc.message : 'Unable to load thread replies.');
    } finally {
      setLoadingThread(false);
    }
  };

  const backToChannel = () => {
    setThreadViewActive(false);
    setSelectedThread(null);
    setThreadReplies([]);
    setThreadDraft('');
  };

  const sendThreadReply = async (event: React.FormEvent) => {
    event.preventDefault();
    const content = threadDraft.trim();
    if (!selectedThread || !content || !token || sendingThread) return;

    try {
      setSendingThread(true);
      
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          action: 'send_thread_reply',
          parent_message_id: selectedThread.id,
          content,
        }));
        setThreadDraft('');
        setSendingThread(false);
        return;
      }

      const response = await fetch(`/api/community/messages/${encodeURIComponent(selectedThread.id)}/replies`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ content }),
      });
      if (!response.ok) throw new Error('Thread reply could not be sent.');
      const result = await response.json();
      if (result?.reply?.id) {
        const reply = mapMessage(result.reply, selectedThread.channelId);
        setThreadReplies((current) => (current.some((item) => item.id === reply.id) ? current : [...current, reply]));
      }
      setThreadDraft('');
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Thread reply could not be sent.');
    } finally {
      setSendingThread(false);
    }
  };


  const closeContextPanel = () => {
    setContextPanelOpen(false);
    setSelectedThread(null);
  };

  const deleteMessage = async (messageId: string) => {
    if (!token) return;
    setMessages((current) => current.map((message) => message.id === messageId ? { ...message, isDeleted: true, body: 'This message was deleted.', imageBase64: null } : message));
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'delete_message',
        message_id: messageId,
      }));
      return;
    }

    try {
      const response = await fetch(`/api/community/messages/${encodeURIComponent(messageId)}`, {
        method: 'DELETE',
        headers: authHeaders(token),
      });
      if (!response.ok) throw new Error('Unable to delete message');
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Unable to delete message.');
    }
  };

  const selectChannel = (channelId: string) => {
    setActiveChannelId(channelId);
    setSidebarOpen(false);
    setChannelQuery('');
  };

  const handleQuickNav = (label: string) => {
    if (label === 'Search') {
      setIsChannelSearchOpen((value) => !value);
      setSidebarOpen(true);
      return;
    }
  };

  const handleAttachment = (event: React.ChangeEvent<HTMLInputElement>, kind: 'file' | 'image') => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setPendingAttachment({ name: file.name, dataUrl: reader.result, kind });
      }
    };
    reader.readAsDataURL(file);
    event.target.value = '';
  };

  const insertMention = () => {
    setDraft((current) => `${current}${current.endsWith(' ') || !current ? '' : ' '}@`);
    requestAnimationFrame(() => composerInputRef.current?.focus());
  };

  const userName = profile?.display_name || profile?.username || 'User';
  const userId = profile?.user_id;
  React.useEffect(() => {
    userIdRef.current = userId || null;
  }, [userId]);
  const userInitials = initials(userName);
  const applyTheme = (t: string) => {
    setTheme(t);
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('community_theme', t);
  };

  const applyCompact = (v: boolean) => {
    setCompactMode(v);
    localStorage.setItem('community_compact_mode', String(v));
  };
  const applyNotify = (v: boolean) => {
    setNotifySounds(v);
    localStorage.setItem('community_notify_sounds', String(v));
  };
  const applyTimestamps = (v: boolean) => {
    setShowTimestamps(v);
    localStorage.setItem('community_show_timestamps', String(v));
  };

  return (
    <div className={`astro-community-shell ${sidebarOpen ? 'is-sidebar-open' : ''} ${compactMode ? 'is-compact' : ''}`}>
      {sidebarOpen && <button className="astro-mobile-scrim" aria-label="Close sidebar" onClick={() => setSidebarOpen(false)} />}

      {/* ── Settings Modal ── */}
      {settingsOpen && (
        <div className="astro-settings-overlay" role="dialog" aria-modal="true" aria-label="Community Settings" onClick={(e) => { if (e.target === e.currentTarget) setSettingsOpen(false); }}>
          <div className="astro-settings-modal">
            <div className="astro-settings-header">
              <div className="astro-settings-title">
                <Settings size={20} />
                <span>Community Settings</span>
              </div>
              <button className="astro-icon-button" onClick={() => setSettingsOpen(false)} aria-label="Close settings"><X size={18} /></button>
            </div>
            <div className="astro-settings-body">
              {/* Appearance */}
              <div className="astro-settings-section">
                <p className="astro-settings-section-label">Appearance</p>
                <div className="astro-settings-row">
                  <div className="astro-settings-row-info">
                    {theme === 'dark' ? <Moon size={16} /> : <Sun size={16} />}
                    <div>
                      <strong>Dark Mode</strong>
                      <span>Switch between light and dark theme</span>
                    </div>
                  </div>
                  <button
                    className={`astro-toggle ${theme === 'dark' ? 'is-on' : ''}`}
                    onClick={() => applyTheme(theme === 'dark' ? 'light' : 'dark')}
                    aria-label="Toggle dark mode"
                  >
                    <span />
                  </button>
                </div>
                <div className="astro-settings-row">
                  <div className="astro-settings-row-info">
                    <Zap size={16} />
                    <div>
                      <strong>Compact Mode</strong>
                      <span>Reduce message spacing for more content</span>
                    </div>
                  </div>
                  <button
                    className={`astro-toggle ${compactMode ? 'is-on' : ''}`}
                    onClick={() => applyCompact(!compactMode)}
                    aria-label="Toggle compact mode"
                  >
                    <span />
                  </button>
                </div>
                <div className="astro-settings-row">
                  <div className="astro-settings-row-info">
                    <Bell size={16} />
                    <div>
                      <strong>Show Timestamps</strong>
                      <span>Display message send times</span>
                    </div>
                  </div>
                  <button
                    className={`astro-toggle ${showTimestamps ? 'is-on' : ''}`}
                    onClick={() => applyTimestamps(!showTimestamps)}
                    aria-label="Toggle timestamps"
                  >
                    <span />
                  </button>
                </div>
              </div>
              {/* Notifications */}
              <div className="astro-settings-section">
                <p className="astro-settings-section-label">Notifications</p>
                <div className="astro-settings-row">
                  <div className="astro-settings-row-info">
                    <Bell size={16} />
                    <div>
                      <strong>Sound Alerts</strong>
                      <span>Play a sound on new messages</span>
                    </div>
                  </div>
                  <button
                    className={`astro-toggle ${notifySounds ? 'is-on' : ''}`}
                    onClick={() => applyNotify(!notifySounds)}
                    aria-label="Toggle sounds"
                  >
                    <span />
                  </button>
                </div>
              </div>
              {/* Account */}
              <div className="astro-settings-section">
                <p className="astro-settings-section-label">Account</p>
                <div className="astro-settings-row">
                  <div className="astro-settings-row-info">
                    <ShieldCheck size={16} />
                    <div>
                      <strong>{userName}</strong>
                      <span>Verified Astrologer · {connectionState === 'connected' ? '🟢 Online' : '🔴 Offline'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <aside className={`astro-community-sidebar ${sidebarOpen ? 'is-open' : ''}`} aria-label="Community navigation">
        <div className="astro-sidebar-profile">
          <button className="astro-workspace-avatar" aria-label="Community workspace">
            AC
          </button>
          <div>
            <div className="astro-community-name">Welcome to<br/>Astro Community</div>
            <div className="astro-user-line" style={{ marginTop: '4px', opacity: 0.8, fontSize: '0.85rem' }}>
              <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#2d8a5d', marginRight: '6px' }}></span>
              {onlineCount} {onlineCount === 1 ? 'person' : 'people'} online
            </div>
          </div>
          <button className="astro-icon-button" aria-label="Open settings" onClick={() => setSettingsOpen(true)}>
            <Settings size={18} />
          </button>
        </div>

        <nav className="astro-quick-nav" aria-label="Primary community sections">
          {quickNav.map(({ label, icon: Icon }) => (
            <button className="astro-nav-item" key={label} onClick={() => handleQuickNav(label)}>
              <Icon size={17} />
              <span>{label}</span>
              {label === 'Saved Messages' && savedMessages.size > 0 && <span className="astro-badge">{savedMessages.size}</span>}
            </button>
          ))}
        </nav>

        <div className="astro-channel-scroll">
          {isChannelSearchOpen && (
            <label className="astro-channel-search">
              <Search size={16} />
              <input
                autoFocus
                value={channelQuery}
                onChange={(event) => setChannelQuery(event.target.value)}
                placeholder="Search channels"
              />
            </label>
          )}

          {loadingChannels && <p className="astro-sidebar-empty">Loading channels...</p>}

          {!loadingChannels && Object.entries(groupedVisibleChannels).map(([group, groupChannels]) => (
            <section className="astro-channel-group" key={group}>
              <button className="astro-group-title">
                <ChevronDown size={14} />
                <span>{group}</span>
              </button>
              {groupChannels.map((channel) => (
                <button
                  className={`astro-channel-link ${activeChannel?.id === channel.id ? 'is-active' : ''}`}
                  key={channel.id}
                  onClick={() => selectChannel(channel.id)}
                >
                  <Hash size={15} />
                  <span>{channel.name}</span>
                  {channel.locked && <ShieldCheck size={13} />}
                </button>
              ))}
            </section>
          ))}

          {!loadingChannels && !searchedChannels.length && (
            <p className="astro-sidebar-empty">No channels found.</p>
          )}
        </div>


      </aside>

      <main className="astro-community-main">
        <header className="astro-user-strip">
          <button className="astro-icon-button desktop-hidden" type="button" aria-label="Open channels" onClick={() => setSidebarOpen(true)}>
            <Hash size={18} />
          </button>
          <button className="astro-channel-titlebar" type="button" onClick={() => setContextPanelOpen((prev) => !prev)} aria-label="Toggle saved messages panel">
            <Hash size={24} />
            <div>
              <h1>{activeChannel?.name || 'general'}</h1>
              <p>{activeChannel?.description || 'General discussion for everyone.'}</p>
            </div>
            {channelSavedMessages.length > 0 && <span className="astro-header-badge">{channelSavedMessages.length}</span>}
          </button>
          <button className="astro-avatar astro-avatar-button" aria-label="Open profile menu">
            {userInitials}
            <StatusDot status={connectionState === 'connected' ? 'online' : 'away'} />
          </button>
        </header>

        <div className="astro-workspace">
          {threadViewActive && selectedThread ? (
            /* ── Full-screen Thread View ── */
            <section className="astro-thread-fullview" aria-label="Thread conversation">
              <header className="astro-thread-topbar">
                <button className="astro-back-button" type="button" onClick={backToChannel} aria-label="Back to channel">
                  <ChevronDown size={18} style={{ transform: 'rotate(90deg)' }} />
                  <span>#{activeChannel?.name || 'channel'}</span>
                </button>
                <div className="astro-thread-title">
                  <MessageSquare size={15} />
                  <span>Thread</span>
                </div>
              </header>

              {/* Parent message */}
              <div className="astro-thread-parent-msg">
                <button className="astro-avatar large" aria-label={displayAuthor(selectedThread, userName, userId)}>
                  {initials(displayAuthor(selectedThread, userName, userId))}
                </button>
                <div>
                  <div className="astro-message-meta">
                    <strong>{displayAuthor(selectedThread, userName, userId)}</strong>
                    {showTimestamps && <time>{selectedThread.time}</time>}
                  </div>
                  {selectedThread.adminPost ? (
                    <div className="astro-admin-post">
                      {selectedThread.adminPost.title && <h3>{selectedThread.adminPost.title}</h3>}
                      {selectedThread.adminPost.body && <p>{selectedThread.adminPost.body}</p>}
                      {selectedThread.adminPost.linkUrl && (
                        <a href={selectedThread.adminPost.linkUrl} target="_blank" rel="noreferrer">
                          {selectedThread.adminPost.linkLabel || selectedThread.adminPost.linkUrl}
                        </a>
                      )}
                    </div>
                  ) : (
                    selectedThread.body && <p>{selectedThread.body}</p>
                  )}
                  {Boolean(selectedThread.imageBase64?.startsWith('data:image')) && selectedThread.imageBase64 && (
                    <img className="astro-message-image" src={selectedThread.imageBase64} alt="Uploaded attachment" />
                  )}
                </div>
              </div>

              <div className="astro-thread-divider"><span>{threadReplies.length} {threadReplies.length === 1 ? 'reply' : 'replies'}</span></div>

              {/* Replies list */}
              <div className="astro-thread-reply-list" ref={threadRepliesRef}>
                {loadingThread && <div className="astro-empty-channel"><h3>Loading thread...</h3></div>}
                {!loadingThread && !threadReplies.length && (
                  <div className="astro-empty-channel">
                    <MessageSquare size={32} />
                    <h3>No replies yet</h3>
                    <p>Start the discussion on this message.</p>
                  </div>
                )}
                {!loadingThread && threadReplies.map((reply) => {
                  const replyAuthor = displayAuthor(reply, userName, userId);
                  return (
                    <article className="astro-message" key={reply.id}>
                      <button className="astro-avatar large" aria-label={`${replyAuthor} profile`}>
                        {initials(replyAuthor)}
                      </button>
                      <div className="astro-message-body">
                        <div className="astro-message-meta">
                          <strong>{replyAuthor}</strong>
                          {showTimestamps && <time>{reply.time}</time>}
                        </div>
                        <p>{reply.body}</p>
                      </div>
                    </article>
                  );
                })}
              </div>

              {/* Reply composer */}
              <form className="astro-composer" onSubmit={sendThreadReply}>
                <div className="astro-composer-field">
                  <input
                    value={threadDraft}
                    onChange={(event) => setThreadDraft(event.target.value)}
                    placeholder={`Reply in thread · #${activeChannel?.name || 'channel'}`}
                    disabled={sendingThread}
                    autoFocus
                  />
                </div>
                <button className="astro-send-button" type="submit" aria-label="Send reply" disabled={sendingThread || !threadDraft.trim()}>
                  <Send size={18} />
                </button>
              </form>
            </section>
          ) : (
          <div className="astro-channel-wrap">
            <section className="astro-conversation" aria-label={activeChannel ? `${activeChannel.name} conversation` : 'Community conversation'}>
              {error && <div className="astro-error-banner">{error}</div>}

              <div className="astro-message-list" ref={messageListRef}>
                {loadingMessages && <div className="astro-empty-channel"><h3>Loading messages...</h3></div>}

                {!loadingMessages && activeChannel && !messages.length && (
                  <div className="astro-empty-channel">
                    <h3>No messages yet</h3>
                    <p>Start the first real discussion in #{activeChannel.name}.</p>
                  </div>
                )}

                {!loadingMessages && !activeChannel && (
                  <div className="astro-empty-channel">
                    <h3>No channels available</h3>
                    <p>Ask an admin to create community channels.</p>
                  </div>
                )}

                {!loadingMessages && messages.length > 0 && (
                  <div className="astro-date-divider">
                    <span>Today</span>
                  </div>
                )}

                {!loadingMessages && messages.map((message) => {
                  const authorName = displayAuthor(message, userName, userId);
                  const isOwnMessage = message.senderId === userId || authorName === userName;
                  const isImageAttachment = Boolean(message.imageBase64?.startsWith('data:image'));
                  return (
                  <article className={`astro-message ${isOwnMessage ? 'is-own' : ''}`} key={message.id}>
                    <button className="astro-avatar large" aria-label={`${authorName} profile`}>
                      {initials(authorName)}
                    </button>
                    <div className="astro-message-body">
                      <div className="astro-message-meta">
                        <strong>{authorName}</strong>
                        {showTimestamps && <time>{message.time}</time>}
                        {message.edited && !message.isDeleted && <span>edited</span>}
                      </div>
                      {message.adminPost ? (
                        <div className="astro-admin-post">
                          {message.adminPost.title && <h3>{message.adminPost.title}</h3>}
                          {message.adminPost.body && <p>{message.adminPost.body}</p>}
                          {message.adminPost.linkUrl && (
                            <a href={message.adminPost.linkUrl} target="_blank" rel="noreferrer">
                              {message.adminPost.linkLabel || message.adminPost.linkUrl}
                            </a>
                          )}
                        </div>
                      ) : (
                        message.body && <p>{message.body}</p>
                      )}
                      {isImageAttachment && message.imageBase64 && (
                        <img className="astro-message-image" src={message.imageBase64} alt="Uploaded attachment" />
                      )}
                      {!isImageAttachment && message.imageBase64 && (
                        <button className="astro-attachment" type="button">
                          <Image size={17} />
                          <span>File attachment</span>
                        </button>
                      )}
                      <div className="astro-message-actions">
                        <button onClick={() => toggleReaction(message.id, 'Helpful')} disabled={message.isDeleted || myReactions.has(message.id)} className={myReactions.has(message.id) ? 'is-reacted' : ''}>
                          <Smile size={14} />
                          Helpful {message.stars > 0 ? message.stars : ''}
                        </button>
                        <button onClick={() => toggleSaved(message.id)} disabled={message.isDeleted} className={savedMessages.has(message.id) ? 'is-saved' : ''}>
                          <Bookmark size={14} />
                          {savedMessages.has(message.id) ? 'Saved ✓' : 'Save'}
                        </button>
                        <button onClick={() => openThread(message)} disabled={message.isDeleted}>
                          <MessageSquare size={14} />
                          Thread
                        </button>
                        <button onClick={() => deleteMessage(message.id)} disabled={message.isDeleted} aria-label="Delete message">
                          <Trash2 size={14} />
                          Delete
                        </button>
                        <button aria-label="More message actions" disabled={message.isDeleted}>
                          <MoreHorizontal size={15} />
                        </button>
                      </div>
                    </div>
                  </article>
                );
                })}
              </div>
            </section>

            {/* Composer / Read-only notice — always at bottom */}
            {activeChannel?.name === 'announcements' ? (
              <div className="astro-announcements-notice">
                <ShieldCheck size={16} />
                <span>This channel is read-only. Only admins can post announcements.</span>
              </div>
            ) : (
            <form className="astro-composer" onSubmit={handleSend}>
              <input
                ref={fileInputRef}
                className="astro-hidden-input"
                type="file"
                onChange={(event) => handleAttachment(event, 'file')}
              />
              <input
                ref={imageInputRef}
                className="astro-hidden-input"
                type="file"
                accept="image/*"
                onChange={(event) => handleAttachment(event, 'image')}
              />
              <div className="astro-composer-tools">
                <button type="button" aria-label="Add attachment" onClick={() => fileInputRef.current?.click()} disabled={!activeChannel}>
                  <Plus size={20} />
                </button>
                <button type="button" aria-label="Add image" onClick={() => imageInputRef.current?.click()} disabled={!activeChannel}>
                  <Image size={18} />
                </button>
                <button type="button" aria-label="Mention member" onClick={insertMention} disabled={!activeChannel}>
                  <AtSign size={18} />
                </button>
              </div>
              <div className="astro-composer-field">
                {pendingAttachment && (
                  <button type="button" className="astro-pending-attachment" onClick={() => setPendingAttachment(null)}>
                    {pendingAttachment.name}
                    <span>Remove</span>
                  </button>
                )}
                <input
                  ref={composerInputRef}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder={activeChannel ? `Message #${activeChannel.name}` : 'Select a channel to message'}
                  disabled={!activeChannel || sending}
                />
              </div>
              <button className="astro-send-button" type="submit" aria-label="Send message" disabled={!activeChannel || sending}>
                <Send size={18} />
              </button>
            </form>
            )}
          </div>
          )}

          <aside className={`astro-context-panel${contextPanelOpen ? ' is-open' : ''}`} aria-label="Saved messages">
              <div className="astro-context-section">
                <div className="astro-section-title">
                  <div>
                    <p className="astro-panel-kicker">Saved</p>
                    <h2>Saved messages</h2>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {channelSavedMessages.length > 0 && <span className="astro-badge">{channelSavedMessages.length}</span>}
                    <button type="button" className="astro-icon-button" onClick={closeContextPanel} aria-label="Close panel">
                      <X size={17} />
                    </button>
                  </div>
                </div>
                <div className="astro-saved-list">
                  {!channelSavedMessages.length && <p className="astro-muted">Saved posts from #{activeChannel?.name || 'this channel'} will appear here.</p>}
                  {channelSavedMessages.map((message) => (
                    <button className="astro-saved-item" type="button" key={message.id} onClick={() => openThread(message)}>
                      <strong>{displayAuthor(message, userName, userId)}</strong>
                      <span>{message.body || 'Attachment message'}</span>
                      {Boolean(message.imageBase64?.startsWith('data:image')) && message.imageBase64 && (
                        <div style={{ marginTop: '6px', borderRadius: '8px', overflow: 'hidden', maxHeight: '120px', display: 'flex' }}>
                          <img src={message.imageBase64} alt="Attachment" style={{ width: '100%', objectFit: 'cover' }} />
                        </div>
                      )}
                      {message.adminPost?.linkUrl && (
                        <div style={{ marginTop: '6px', fontSize: '0.8rem', color: '#6b7fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {message.adminPost.linkLabel || message.adminPost.linkUrl}
                        </div>
                      )}
                      <em>{message.time}</em>
                    </button>
                  ))}
                </div>
              </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

export default AstroCommunityPage;
