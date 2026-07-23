import React from 'react';
import {
  ArrowLeft,
  AtSign,
  Bell,
  Bookmark,
  ChevronDown,
  Copy,
  Forward,
  Hash,
  Image,
  Info,
  Menu,
  MessageSquare,
  Moon,
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
  client_id?: string;
  user_name?: string;
  content?: string;
  mentions?: MentionTarget[];
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
  clientId?: string;
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
  pending?: boolean;
  failed?: boolean;
};

type ThreadReply = Message;

type Profile = {
  user_id?: string;
  display_name?: string;
  username?: string;
  role?: string;
};

type CommunityMember = {
  user_id?: string;
  display_name?: string;
  username?: string;
  email?: string;
  bio?: string;
  systems_practiced?: string[];
};

type OnlineUser = {
  user_id?: string;
  display_name?: string;
};

type MentionTarget = {
  user_id?: string;
  display_name?: string;
  username?: string;
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

const defaultCommunityChannels: Channel[] = Object.entries(channelMetadata)
  .filter(([id]) => id !== 'community-guidelines')
  .map(([id, metadata]) => ({
    id,
    name: id,
    group: metadata.group,
    description: metadata.description,
    locked: metadata.locked,
  }));

const quickNav = [
  { label: 'Saved Messages', icon: Bookmark, count: 0 },
  { label: 'Search', icon: Search, count: 0 },
];

const reactionOptions = [
  { type: 'Helpful', emoji: '😊', label: 'Helpful' },
  { type: 'heart', emoji: '❤️', label: 'Love' },
  { type: 'thumbs_up', emoji: '👍', label: 'Agree' },
  { type: 'insightful', emoji: '💡', label: 'Insightful' },
  { type: 'thanks', emoji: '🙏', label: 'Thanks' },
];

const reactionEmojiByType = reactionOptions.reduce<Record<string, string>>((acc, reaction) => {
  acc[reaction.type] = reaction.emoji;
  return acc;
}, {});

const COMMUNITY_PROFILE_CACHE_KEY = 'community_profile_cache_v1';
const COMMUNITY_CHANNELS_CACHE_KEY = 'community_channels_cache_v1';
const COMMUNITY_ACTIVE_CHANNEL_KEY = 'community_active_channel_v1';
const COMMUNITY_MESSAGE_CACHE_PREFIX = 'community_messages_cache_v1:';
const MESSAGE_CACHE_LIMIT = 80;
const MESSAGE_IMAGE_CACHE_LIMIT = 700_000;
const PREFETCH_CACHE_TTL = 60_000;
const PREFETCH_CHANNEL_LIMIT = 3;

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
    clientId: row.client_id,
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

function readJsonCache<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) as T : fallback;
  } catch {
    return fallback;
  }
}

function writeJsonCache(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Cached chat snapshots are an acceleration layer. If storage is full, live API data still works.
  }
}

function messageCacheKey(channelId: string) {
  return `${COMMUNITY_MESSAGE_CACHE_PREFIX}${channelId}`;
}

function readCachedChannels() {
  const cachedChannels = readJsonCache<Channel[]>(COMMUNITY_CHANNELS_CACHE_KEY, []);
  return cachedChannels.length ? cachedChannels : defaultCommunityChannels;
}

function readCachedProfile() {
  return readJsonCache<Profile | null>(COMMUNITY_PROFILE_CACHE_KEY, null);
}

function readCachedMessagesPayload(channelId: string) {
  return readJsonCache<{ savedAt?: number; messages?: Message[] }>(messageCacheKey(channelId), { savedAt: 0, messages: [] });
}

function readCachedMessages(channelId: string) {
  return readCachedMessagesPayload(channelId).messages || [];
}

function getInitialActiveChannelId(channels: Channel[]) {
  try {
    const cached = localStorage.getItem(COMMUNITY_ACTIVE_CHANNEL_KEY);
    if (cached) return cached;
  } catch {
    // Ignore storage access errors.
  }
  return channels.find((channel) => channel.id === 'general')?.id || channels[0]?.id || '';
}

function cacheMessages(channelId: string, rows: Message[]) {
  const compactRows = rows
    .filter((message) => !message.pending && !message.failed)
    .slice(-MESSAGE_CACHE_LIMIT)
    .map((message) => ({
      ...message,
      imageBase64: message.imageBase64 && message.imageBase64.length <= MESSAGE_IMAGE_CACHE_LIMIT ? message.imageBase64 : null,
    }));
  writeJsonCache(messageCacheKey(channelId), { savedAt: Date.now(), messages: compactRows });
}

function makeOptimisticMessage(params: {
  channelId: string;
  senderId?: string;
  author: string;
  body: string;
  contentType: string;
  imageBase64?: string | null;
  clientId: string;
}): Message {
  return {
    id: `optimistic-${params.clientId}`,
    channelId: params.channelId,
    senderId: params.senderId,
    clientId: params.clientId,
    author: params.author,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    body: params.body,
    contentType: params.contentType,
    imageBase64: params.imageBase64 || null,
    stars: 0,
    isDeleted: false,
    edited: false,
    pending: true,
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

function mentionHandle(member: CommunityMember) {
  const displayName = member.display_name || member.username || member.email || 'Astrologer';
  return (member.username || displayName).replace(/^@/, '').replace(/\s+/g, '.').toLowerCase();
}

function normalizeMention(value?: string) {
  return (value || '').replace(/^@/, '').replace(/[^a-z0-9_.-]+/gi, '').toLowerCase();
}

function renderMessageText(text: string) {
  const parts = text.split(/(@[\w.-]+)/g);
  return parts.map((part, index) => (
    /^@[\w.-]+$/.test(part)
      ? <span className="astro-mention-token" key={`${part}-${index}`}>{part}</span>
      : <React.Fragment key={`${part}-${index}`}>{part}</React.Fragment>
  ));
}

function AstroCommunityPage() {
  const [channels, setChannels] = React.useState<Channel[]>(() => readCachedChannels());
  const [activeChannelId, setActiveChannelId] = React.useState(() => getInitialActiveChannelId(readCachedChannels()));
  const [messages, setMessages] = React.useState<Message[]>(() => {
    const initialChannelId = getInitialActiveChannelId(readCachedChannels());
    return initialChannelId ? readCachedMessages(initialChannelId) : [];
  });
  const [profile, setProfile] = React.useState<Profile | null>(() => readCachedProfile());
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
  const [pendingThreadAttachment, setPendingThreadAttachment] = React.useState<{ name: string; dataUrl: string; kind: 'file' | 'image' } | null>(null);
  const [loadingThread, setLoadingThread] = React.useState(false);
  const [sendingThread, setSendingThread] = React.useState(false);
  const [contextPanelOpen, setContextPanelOpen] = React.useState(false);
  const [threadViewActive, setThreadViewActive] = React.useState(false);
  const [myReactions, setMyReactions] = React.useState<Set<string>>(() => new Set(JSON.parse(localStorage.getItem('community_my_reactions') || '[]')));
  const threadRepliesRef = React.useRef<HTMLDivElement>(null);
  const [loadingChannels, setLoadingChannels] = React.useState(() => readCachedChannels().length === 0);
  const [loadingMessages, setLoadingMessages] = React.useState(false);
  const [sending, setSending] = React.useState(false);
  const [error, setError] = React.useState('');
  const [infoNotice, setInfoNotice] = React.useState('');
  const [connectionState, setConnectionState] = React.useState<'idle' | 'connecting' | 'connected' | 'offline'>('idle');
  const [onlineCount, setOnlineCount] = React.useState(0);
  const [onlineUsers, setOnlineUsers] = React.useState<OnlineUser[]>([]);
  const [typingUsers, setTypingUsers] = React.useState<Record<string, string>>({});
  const [theme, setTheme] = React.useState('dark');
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [communityMembers, setCommunityMembers] = React.useState<CommunityMember[]>([]);
  const [mentionPickerOpen, setMentionPickerOpen] = React.useState(false);
  const [activeMessageMenuId, setActiveMessageMenuId] = React.useState<string | null>(null);
  const [forwardingMessage, setForwardingMessage] = React.useState<Message | null>(null);
  const [reactionBadges, setReactionBadges] = React.useState<Record<string, { emoji: string; count: number }>>({});
  const [compactMode, setCompactMode] = React.useState(() => localStorage.getItem('community_compact_mode') === 'true');
  const [notifySounds, setNotifySounds] = React.useState(() => localStorage.getItem('community_notify_sounds') !== 'false');
  const [showTimestamps, setShowTimestamps] = React.useState(() => localStorage.getItem('community_show_timestamps') !== 'false');
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const imageInputRef = React.useRef<HTMLInputElement>(null);
  const threadFileInputRef = React.useRef<HTMLInputElement>(null);
  const threadImageInputRef = React.useRef<HTMLInputElement>(null);
  const composerInputRef = React.useRef<HTMLInputElement>(null);
  const threadComposerInputRef = React.useRef<HTMLInputElement>(null);
  const wsRef = React.useRef<WebSocket | null>(null);
  const typingTimeoutRef = React.useRef<number | null>(null);
  const messageListRef = React.useRef<HTMLDivElement>(null);
  const userIdRef = React.useRef<string | null>(null);
  const messagesRef = React.useRef<Message[]>([]);

  const token = getToken();
  const activeChannel = channels.find((channel) => channel.id === activeChannelId);
  const searchedChannels = channelQuery.trim()
    ? channels.filter((channel) => `${channel.name} ${channel.group} ${channel.description}`.toLowerCase().includes(channelQuery.toLowerCase()))
    : channels;
  const groupedVisibleChannels = groupChannels(searchedChannels);
  const channelSavedMessages = savedMessageRows.filter((message) => message.channelId === activeChannelId);
  const forwardableChannels = channels.filter((channel) => channel.name !== 'announcements' && !channel.locked);

  React.useEffect(() => {
    localStorage.setItem('community_saved_messages', JSON.stringify([...savedMessages]));
  }, [savedMessages]);

  React.useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  React.useEffect(() => {
    if (savedMessageRows.length > 0) {
      localStorage.setItem('community_saved_message_rows', JSON.stringify(savedMessageRows));
    }
  }, [savedMessageRows]);

  React.useEffect(() => {
    localStorage.setItem('community_my_reactions', JSON.stringify([...myReactions]));
  }, [myReactions]);

  React.useEffect(() => {
    const closeFloatingMenus = (event: PointerEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest('[data-message-menu-root="true"]')) return;
      setActiveMessageMenuId(null);
    };
    document.addEventListener('pointerdown', closeFloatingMenus);
    return () => document.removeEventListener('pointerdown', closeFloatingMenus);
  }, []);

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
  }, [activeChannelId, token]);

  React.useEffect(() => {
    let cancelled = false;

    async function loadMembers() {
      if (!token) return;
      try {
        const response = await fetch('/api/community/members', { headers: authHeaders(token) });
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled && Array.isArray(data)) setCommunityMembers(data);
      } catch {
        if (!cancelled) setCommunityMembers([]);
      }
    }

    loadMembers();
    return () => {
      cancelled = true;
    };
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

        const profileData = profileResponse.ok ? await profileResponse.json() : readCachedProfile();
        const channelData = channelResponse.ok ? await channelResponse.json() : readCachedChannels();
        const normalizedChannels = Array.isArray(channelData)
          ? channelData.map(normalizeChannel).filter((channel) => channel.id !== 'community-guidelines')
          : readCachedChannels();

        if (!profileResponse.ok || !channelResponse.ok) {
          const accessRejected = profileResponse.status === 401 || profileResponse.status === 403 || channelResponse.status === 401 || channelResponse.status === 403;
          if (!normalizedChannels.length) {
            throw new Error(accessRejected ? 'Community access is still syncing. Please refresh once after sign in.' : 'Unable to load community.');
          }
          setInfoNotice(accessRejected ? 'Community access is syncing. Showing cached channels while reconnecting.' : 'Showing cached community channels while reconnecting.');
          window.setTimeout(() => setInfoNotice(''), 4000);
        }

        if (cancelled) return;
        if (profileData) {
          setProfile(profileData);
          writeJsonCache(COMMUNITY_PROFILE_CACHE_KEY, profileData);
        }
        setChannels(normalizedChannels.length ? normalizedChannels : defaultCommunityChannels);
        writeJsonCache(COMMUNITY_CHANNELS_CACHE_KEY, normalizedChannels.length ? normalizedChannels : defaultCommunityChannels);
        setActiveChannelId((current) => {
          const preferred = normalizedChannels.find((channel) => channel.id === 'general')
            || normalizedChannels.find((channel) => channel.id !== 'announcements' && !channel.locked)
            || normalizedChannels[0]
            || defaultCommunityChannels.find((channel) => channel.id === 'general')
            || defaultCommunityChannels[0];
          const nextChannelId = current || preferred?.id || '';
          if (nextChannelId) writeJsonCache(COMMUNITY_ACTIVE_CHANNEL_KEY, nextChannelId);
          return nextChannelId;
        });
      } catch (exc) {
        if (!cancelled) {
          setError(exc instanceof Error ? exc.message : 'Unable to load community.');
          setChannels((current) => current.length ? current : defaultCommunityChannels);
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
    if (activeChannelId) writeJsonCache(COMMUNITY_ACTIVE_CHANNEL_KEY, activeChannelId);
  }, [activeChannelId]);

  React.useEffect(() => {
    let cancelled = false;

    async function loadMessages() {
      if (!activeChannelId || !token) {
        setMessages([]);
        return;
      }

      const cachedMessages = readCachedMessages(activeChannelId);
      if (cachedMessages.length > 0) {
        setMessages(cachedMessages);
        setLoadingMessages(false);
      } else {
        setLoadingMessages(true);
      }

      try {
        setError('');
        const response = await fetch(`/api/community/messages/${encodeURIComponent(activeChannelId)}`, {
          headers: authHeaders(token),
        });

        if (!response.ok) throw new Error('Unable to load messages for this channel.');

        const data = await response.json();
        if (!cancelled) {
          const nextMessages = Array.isArray(data) ? data.map((row) => mapMessage(row, activeChannelId)) : [];
          setMessages(nextMessages);
          cacheMessages(activeChannelId, nextMessages);
        }
      } catch (exc) {
        if (!cancelled) {
          if (!cachedMessages.length) setMessages([]);
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
    if (activeChannelId && messages.length > 0) cacheMessages(activeChannelId, messages);
  }, [activeChannelId, messages]);

  React.useEffect(() => {
    if (!token || !channels.length) return;
    let cancelled = false;
    let timeoutId = 0;
    const controller = new AbortController();

    async function prefetchChannelMessages() {
      const candidates = channels
        .filter((channel) => channel.id && channel.id !== activeChannelId && channel.id !== 'announcements')
        .slice(0, PREFETCH_CHANNEL_LIMIT);
      for (const channel of candidates) {
        if (cancelled) return;
        const cached = readCachedMessagesPayload(channel.id);
        if ((cached.messages?.length || 0) > 0 && Date.now() - (cached.savedAt || 0) < PREFETCH_CACHE_TTL) continue;

        try {
          const latestToken = getToken();
          if (!latestToken) return;
          const response = await fetch(`/api/community/messages/${encodeURIComponent(channel.id)}`, {
            headers: authHeaders(latestToken),
            signal: controller.signal,
          });
          if (response.status === 401 || response.status === 403) return;
          if (!response.ok) continue;
          const data = await response.json();
          if (cancelled) return;
          const nextMessages = Array.isArray(data) ? data.map((row) => mapMessage(row, channel.id)) : [];
          cacheMessages(channel.id, nextMessages);
        } catch (exc) {
          if ((exc as Error).name === 'AbortError') return;
          // Prefetch is best-effort. The active channel loader remains the source of truth.
        }
      }
    }

    timeoutId = window.setTimeout(prefetchChannelMessages, 350);
    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(timeoutId);
    };
  }, [activeChannelId, channels, token]);

  React.useEffect(() => {
    wsRef.current?.close();
    wsRef.current = null;

    if (!activeChannelId || !token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/api/community/ws/${encodeURIComponent(activeChannelId)}`);
    wsRef.current = socket;
    setConnectionState('connecting');

    socket.onopen = () => {
      socket.send(JSON.stringify({ action: 'authenticate', token }));
    };
    socket.onclose = () => setConnectionState('offline');
    socket.onerror = () => setConnectionState('offline');
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'connection_ready') {
          setConnectionState('connected');
          return;
        }
        const row = payload.data || payload.message;
        if ((payload.type === 'new_message' || payload.type === 'message_created') && row?.id) {
          const next = mapMessage(row, activeChannelId);
          setMessages((current) => {
            if (current.some((message) => message.id === next.id)) return current;
            if (next.clientId && current.some((message) => message.clientId === next.clientId)) {
              return current.map((message) => (message.clientId === next.clientId ? next : message));
            }
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
              } catch {
                // Ignore audio errors
              }
            }
            return [...current, next];
          });
        }
        if (payload.type === 'message_mentioned' && row?.id) {
          const author = row.user_name || 'Someone';
          setInfoNotice(`${author} mentioned you in #${payload.channel_name || activeChannelId}.`);
          window.setTimeout(() => setInfoNotice(''), 4500);
          if (document.hidden && 'Notification' in window) {
            if (Notification.permission === 'granted') {
              new Notification(`Mention in #${payload.channel_name || activeChannelId}`, {
                body: `${author}: ${(row.content || '').slice(0, 120)}`,
              });
            } else if (Notification.permission === 'default') {
              Notification.requestPermission().catch(() => undefined);
            }
          }
        }
        if (payload.type === 'message_updated' && row?.id) {
          const next = mapMessage(row, activeChannelId);
          setMessages((current) => current.map((message) => (message.id === next.id ? next : message)));
        }
        if (payload.type === 'message_deleted' && payload.message_id) {
          setMessages((current) => current.filter((message) => message.id !== payload.message_id));
          setSavedMessages((current) => {
            const next = new Set(current);
            next.delete(payload.message_id);
            return next;
          });
          setSavedMessageRows((current) => current.filter((message) => message.id !== payload.message_id));
        }
        if ((payload.type === 'message_starred' || payload.type === 'reaction_added') && payload.message_id) {
          if (payload.user_id && payload.user_id === userIdRef.current) return;
          setMessages((current) => current.map((message) => message.id === payload.message_id ? { ...message, stars: message.stars + 1 } : message));
          setReactionBadges((current) => ({
            ...current,
            [payload.message_id]: {
              emoji: reactionEmojiByType[payload.reaction_type] || '😊',
              count: (current[payload.message_id]?.count || 0) + 1,
            },
          }));
        }
        if (payload.type === 'reaction_removed' && payload.message_id) {
          if (payload.user_id && payload.user_id === userIdRef.current) return;
          setMessages((current) => current.map((message) => message.id === payload.message_id ? { ...message, stars: Math.max(0, message.stars - 1) } : message));
          setReactionBadges((current) => ({
            ...current,
            [payload.message_id]: {
              emoji: current[payload.message_id]?.emoji || reactionEmojiByType[payload.reaction_type] || '😊',
              count: Math.max(0, (current[payload.message_id]?.count || 1) - 1),
            },
          }));
        }
        if (payload.type === 'reaction_replaced' && payload.message_id) {
          if (payload.user_id && payload.user_id === userIdRef.current) return;
          setReactionBadges((current) => ({
            ...current,
            [payload.message_id]: {
              emoji: reactionEmojiByType[payload.reaction_type] || current[payload.message_id]?.emoji || '😊',
              count: current[payload.message_id]?.count || messagesRef.current.find((message) => message.id === payload.message_id)?.stars || 1,
            },
          }));
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
          setOnlineUsers(Array.isArray(payload.users) ? payload.users : []);
        }
        if (payload.type === 'typing_started' && payload.user_id && payload.user_id !== userIdRef.current) {
          setTypingUsers((current) => ({ ...current, [payload.user_id]: payload.display_name || 'Someone' }));
        }
        if (payload.type === 'typing_stopped' && payload.user_id) {
          setTypingUsers((current) => {
            const next = { ...current };
            delete next[payload.user_id];
            return next;
          });
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
    setPendingThreadAttachment(null);
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
    const socket = wsRef.current;
    if (!activeChannelId || !token || !draft.trim() || !socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ action: 'typing_started' }));
    if (typingTimeoutRef.current) window.clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = window.setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'typing_stopped' }));
      }
    }, 1100);
    return () => {
      if (typingTimeoutRef.current) window.clearTimeout(typingTimeoutRef.current);
    };
  }, [draft, activeChannelId, token]);

  React.useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || lastMessage.pending || !activeChannelId || !token) return;
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
    if ((!content && !pendingAttachment) || !activeChannelId || !token) return;

    const attachment = pendingAttachment;
    const contentType = attachment ? (attachment.kind === 'image' ? 'IMAGE' : 'ATTACHMENT') : 'STANDARD';
    const clientId = crypto.randomUUID?.() || `${Date.now()}`;
    const optimisticMessage = makeOptimisticMessage({
      channelId: activeChannelId,
      senderId: userId,
      author: userName,
      body: content,
      contentType,
      imageBase64: attachment?.dataUrl || null,
      clientId,
    });

    setMessages((current) => [...current, optimisticMessage]);
    setDraft('');
    setPendingAttachment(null);
    setMentionPickerOpen(false);

    try {
      setSending(true);
      setError('');
      
      const payload = {
        action: 'send_message',
        content,
        content_type: contentType,
        image_base64: attachment?.dataUrl || null,
        mentions: selectedMentions,
        client_id: clientId,
      };

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(payload));
        setSending(false);
        return;
      }

      const response = await fetch(`/api/community/messages/${encodeURIComponent(activeChannelId)}`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({
          content,
          content_type: contentType,
          image_base64: attachment?.dataUrl || null,
          mentions: selectedMentions,
          client_id: clientId,
        }),
      });

      if (!response.ok) throw new Error('Message could not be sent.');

      const result = await response.json();
      if (result?.message?.id) {
        const sent = mapMessage(result.message, activeChannelId);
        setMessages((current) => current.map((message) => (message.clientId === clientId ? sent : message)));
      }
    } catch (exc) {
      setMessages((current) => current.map((message) => (message.clientId === clientId ? { ...message, pending: false, failed: true } : message)));
      setError(exc instanceof Error ? exc.message : 'Message could not be sent.');
    } finally {
      setSending(false);
    }
  };

  const toggleReaction = async (messageId: string, reaction: string) => {
    if (!token) return;
    const previousReaction = reactionOptions.find((option) => myReactions.has(`${messageId}:${option.type}`))?.type;
    const reactionKey = `${messageId}:${reaction}`;
    const isRemoving = previousReaction === reaction;
    const delta = isRemoving ? -1 : previousReaction ? 0 : 1;
    setActiveMessageMenuId(null);
    setMyReactions((current) => {
      const next = new Set(current);
      reactionOptions.forEach((option) => next.delete(`${messageId}:${option.type}`));
      if (!isRemoving) next.add(reactionKey);
      return next;
    });
    setMessages((current) => current.map((message) => message.id === messageId ? { ...message, stars: Math.max(0, message.stars + delta) } : message));
    setReactionBadges((current) => ({
      ...current,
      [messageId]: {
        emoji: reactionEmojiByType[isRemoving ? previousReaction : reaction] || '😊',
        count: Math.max(0, (current[messageId]?.count ?? messages.find((message) => message.id === messageId)?.stars ?? 0) + delta),
      },
    }));

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'toggle_reaction',
        message_id: messageId,
        reaction_type: reaction,
        previous_reaction: previousReaction || null,
      }));
      return;
    }

    try {
      await fetch(`/api/community/messages/${encodeURIComponent(messageId)}/reactions`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ reaction_type: reaction, previous_reaction: previousReaction || null }),
      });
    } catch {
      setMyReactions((current) => {
        const next = new Set(current);
        reactionOptions.forEach((option) => next.delete(`${messageId}:${option.type}`));
        if (previousReaction) next.add(`${messageId}:${previousReaction}`);
        return next;
      });
      setMessages((current) => current.map((message) => message.id === messageId ? { ...message, stars: Math.max(0, message.stars - delta) } : message));
      setReactionBadges((current) => ({
        ...current,
        [messageId]: {
          emoji: previousReaction ? reactionEmojiByType[previousReaction] : current[messageId]?.emoji || reactionEmojiByType[reaction] || '😊',
          count: Math.max(0, (current[messageId]?.count || 0) - delta),
        },
      }));
    }
  };

  const toggleSaved = async (messageId: string) => {
    if (!token) return;
    const wasSaved = savedMessages.has(messageId);
    const message = messages.find((item) => item.id === messageId);

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
      if (!response.ok) throw new Error('Unable to save message');
      const result = await response.json();
      setSavedMessages((current) => {
        const next = new Set(current);
        if (result.saved) next.add(messageId);
        else next.delete(messageId);
        return next;
      });
    } catch {
      // Keep the local saved state as a fallback when the optional saved table is unavailable.
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
    setPendingThreadAttachment(null);
  };

  const sendThreadReply = async (event: React.FormEvent) => {
    event.preventDefault();
    const content = threadDraft.trim();
    if (!selectedThread || (!content && !pendingThreadAttachment) || !token || sendingThread) return;

    try {
      setSendingThread(true);
      
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          action: 'send_thread_reply',
          parent_message_id: selectedThread.id,
          content,
          image_base64: pendingThreadAttachment?.dataUrl || null,
        }));
        setThreadDraft('');
        setPendingThreadAttachment(null);
        setSendingThread(false);
        return;
      }

      const response = await fetch(`/api/community/messages/${encodeURIComponent(selectedThread.id)}/replies`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ content, image_base64: pendingThreadAttachment?.dataUrl || null }),
      });
      if (!response.ok) throw new Error('Thread reply could not be sent.');
      const result = await response.json();
      if (result?.reply?.id) {
        const reply = mapMessage(result.reply, selectedThread.channelId);
        setThreadReplies((current) => (current.some((item) => item.id === reply.id) ? current : [...current, reply]));
      }
      setThreadDraft('');
      setPendingThreadAttachment(null);
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

  const copyMessage = async (message: Message) => {
    const text = message.body || message.adminPost?.linkUrl || 'Attachment message';
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(text);
      setActiveMessageMenuId(null);
      setInfoNotice('Message copied.');
    } catch {
      try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.setAttribute('readonly', '');
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        setActiveMessageMenuId(null);
        setInfoNotice('Message copied.');
      } catch {
        setError('Unable to copy message.');
      }
    }
  };

  const showMessageInfo = (message: Message, authorName: string) => {
    const seenCount = Math.max(0, onlineCount);
    setInfoNotice(`${authorName} · ${message.time || 'Just now'} · Seen by ${seenCount} ${seenCount === 1 ? 'user' : 'users'}`);
    setActiveMessageMenuId(null);
  };

  const forwardMessage = (message: Message) => {
    setActiveMessageMenuId(null);
    setForwardingMessage(message);
  };

  const forwardMessageToChannel = async (channelId: string) => {
    if (!forwardingMessage || !token) return;
    const targetChannel = channels.find((channel) => channel.id === channelId);
    const content = forwardingMessage.body || forwardingMessage.adminPost?.linkUrl || '';

    try {
      const response = await fetch(`/api/community/messages/${encodeURIComponent(channelId)}`, {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({
          content,
          content_type: forwardingMessage.imageBase64 ? (forwardingMessage.imageBase64.startsWith('data:image') ? 'IMAGE' : 'ATTACHMENT') : 'STANDARD',
          image_base64: forwardingMessage.imageBase64 || null,
          client_id: crypto.randomUUID?.() || `${Date.now()}`,
        }),
      });
      if (!response.ok) throw new Error('Unable to forward message.');

      const result = await response.json();
      if (channelId === activeChannelId && result?.message?.id) {
        const sent = mapMessage(result.message, channelId);
        setMessages((current) => (current.some((message) => message.id === sent.id) ? current : [...current, sent]));
      }
      setForwardingMessage(null);
      setInfoNotice(`Message forwarded to #${targetChannel?.name || channelId}.`);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Unable to forward message.');
    }
  };

  const deleteMessage = async (messageId: string) => {
    if (!token) return;
    const deletedMessage = messages.find((message) => message.id === messageId);
    setMessages((current) => current.filter((message) => message.id !== messageId));
    setSavedMessages((current) => {
      const next = new Set(current);
      next.delete(messageId);
      return next;
    });
    setSavedMessageRows((current) => current.filter((message) => message.id !== messageId));
    
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
      if (deletedMessage) setMessages((current) => current.some((message) => message.id === messageId) ? current : [...current, deletedMessage]);
      setError(exc instanceof Error ? exc.message : 'Unable to delete message.');
    }
  };

  const confirmDeleteMessage = (messageId: string) => {
    setActiveMessageMenuId(null);
    if (window.confirm('Delete this message permanently?')) {
      deleteMessage(messageId);
    }
  };

  const selectChannel = (channelId: string) => {
    const cachedMessages = readCachedMessages(channelId);
    setMessages(cachedMessages);
    setLoadingMessages(cachedMessages.length === 0);
    setActiveChannelId(channelId);
    writeJsonCache(COMMUNITY_ACTIVE_CHANNEL_KEY, channelId);
    setSidebarOpen(false);
    setChannelQuery('');
    setActiveMessageMenuId(null);
  };

  const returnToMainApplication = () => {
    window.location.href = '/index.html';
  };

  const handleQuickNav = (label: string) => {
    if (label === 'Saved Messages') {
      setContextPanelOpen(true);
      setSidebarOpen(false);
      return;
    }
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

  const handleThreadAttachment = (event: React.ChangeEvent<HTMLInputElement>, kind: 'file' | 'image') => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setPendingThreadAttachment({ name: file.name, dataUrl: reader.result, kind });
      }
    };
    reader.readAsDataURL(file);
    event.target.value = '';
  };

  const userName = profile?.display_name || profile?.username || 'User';
  const userId = profile?.user_id;
  const mentionMembers = React.useMemo(() => {
    const fallbackMember = {
      user_id: userId,
      display_name: userName,
      username: profile?.username || userName.toLowerCase().replace(/[^a-z0-9]+/g, ''),
    };
    const members = communityMembers.length ? communityMembers : [fallbackMember];
    const query = (draft.match(/@([\w.-]*)$/)?.[1] || '').toLowerCase();
    return members
      .filter((member) => {
        const displayName = member.display_name || member.username || 'Astrologer';
        const username = member.username || displayName;
        return !query || `${displayName} ${username}`.toLowerCase().includes(query);
      })
      .slice(0, 8);
  }, [communityMembers, draft, profile?.username, userId, userName]);

  const selectedMentions = React.useMemo<MentionTarget[]>(() => {
    const handles = new Set((draft.match(/@[\w.-]+/g) || []).map(normalizeMention).filter(Boolean));
    if (!handles.size) return [];
    return communityMembers
      .filter((member) => {
        const displayName = member.display_name || member.username || member.email || '';
        const candidates = [
          member.username,
          mentionHandle(member),
          displayName,
          displayName.replace(/\s+/g, '.'),
          member.email?.split('@')[0],
        ].map(normalizeMention);
        return candidates.some((candidate) => handles.has(candidate));
      })
      .map((member) => ({
        user_id: member.user_id,
        display_name: member.display_name || member.username || member.email,
        username: mentionHandle(member),
      }))
      .filter((member, index, list) => Boolean(member.user_id) && list.findIndex((item) => item.user_id === member.user_id) === index);
  }, [communityMembers, draft]);

  const visibleOnlineUsers = React.useMemo(() => {
    const rows = onlineUsers.length ? onlineUsers : (connectionState === 'connected' ? [{ user_id: userId, display_name: userName }] : []);
    return rows
      .filter((member, index, list) => Boolean(member.display_name || member.user_id) && list.findIndex((item) => item.user_id === member.user_id) === index)
      .slice(0, 8);
  }, [connectionState, onlineUsers, userId, userName]);
  const typingNames = React.useMemo(() => Object.values(typingUsers).slice(0, 3), [typingUsers]);

  const insertMention = () => {
    setDraft((current) => `${current}${current.endsWith(' ') || !current ? '' : ' '}@`);
    setMentionPickerOpen(true);
    requestAnimationFrame(() => composerInputRef.current?.focus());
  };

  const selectMention = (member: CommunityMember) => {
    const mentionName = mentionHandle(member);
    setDraft((current) => {
      const base = current.match(/@[\w.-]*$/) ? current.replace(/@[\w.-]*$/, '') : `${current}${current.endsWith(' ') || !current ? '' : ' '}`;
      return `${base}@${mentionName} `;
    });
    setMentionPickerOpen(false);
    requestAnimationFrame(() => composerInputRef.current?.focus());
  };

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

        <section className="astro-online-panel" aria-label="Online members">
          <div className="astro-online-title">
            <span>Online now</span>
            <strong>{onlineCount}</strong>
          </div>
          <div className="astro-online-list">
            {visibleOnlineUsers.map((member) => {
              const name = member.display_name || 'Astrologer';
              return (
                <div className="astro-online-member" key={member.user_id || name}>
                  <span className="astro-online-avatar">{initials(name)}</span>
                  <span>{name}</span>
                </div>
              );
            })}
            {!visibleOnlineUsers.length && <p>No one else is online.</p>}
          </div>
        </section>

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
          <button className="astro-mobile-back-btn" type="button" onClick={returnToMainApplication} aria-label="Back to main application">
            <ArrowLeft size={22} />
          </button>
          <button className="astro-mobile-menu-btn" type="button" onClick={() => setSidebarOpen((prev) => !prev)} aria-label="Open channels menu">
            <Menu size={22} />
          </button>
          <button className="astro-channel-titlebar" type="button" onClick={() => setSidebarOpen((prev) => !prev)} aria-label="Switch channel">
            <Hash size={24} />
            <div>
              <h1>#{activeChannel?.name || 'general'}</h1>
              <p>{activeChannel?.description || 'General discussion for everyone.'}</p>
            </div>
            {channelSavedMessages.length > 0 && <span className="astro-header-badge">{channelSavedMessages.length}</span>}
          </button>
          <button className="astro-avatar astro-avatar-button" onClick={() => setContextPanelOpen((prev) => !prev)} aria-label="Open saved messages">
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
                    selectedThread.body && <p>{renderMessageText(selectedThread.body)}</p>
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
                        <p>{renderMessageText(reply.body)}</p>
                      </div>
                    </article>
                  );
                })}
              </div>

              {/* Reply composer */}
              <form className="astro-composer" onSubmit={sendThreadReply}>
                <input
                  ref={threadFileInputRef}
                  className="astro-hidden-input"
                  type="file"
                  onChange={(event) => handleThreadAttachment(event, 'file')}
                />
                <input
                  ref={threadImageInputRef}
                  className="astro-hidden-input"
                  type="file"
                  accept="image/*"
                  onChange={(event) => handleThreadAttachment(event, 'image')}
                />
                <div className="astro-composer-tools">
                  <button type="button" aria-label="Add attachment" onClick={() => threadFileInputRef.current?.click()} disabled={sendingThread}>
                    <Plus size={20} />
                  </button>
                  <button type="button" aria-label="Add image" onClick={() => threadImageInputRef.current?.click()} disabled={sendingThread}>
                    <Image size={18} />
                  </button>
                  <button
                    type="button"
                    aria-label="Mention member"
                    onClick={() => {
                      setThreadDraft((current) => `${current}${current.endsWith(' ') || !current ? '' : ' '}@`);
                      requestAnimationFrame(() => threadComposerInputRef.current?.focus());
                    }}
                    disabled={sendingThread}
                  >
                    <AtSign size={18} />
                  </button>
                </div>
                <div className="astro-composer-field">
                  {pendingThreadAttachment && (
                    <button type="button" className="astro-pending-attachment" onClick={() => setPendingThreadAttachment(null)}>
                      {pendingThreadAttachment.name}
                      <span>Remove</span>
                    </button>
                  )}
                  <input
                    ref={threadComposerInputRef}
                    value={threadDraft}
                    onChange={(event) => setThreadDraft(event.target.value)}
                    placeholder={`Reply in thread · #${activeChannel?.name || 'channel'}`}
                    disabled={sendingThread}
                    autoFocus
                  />
                </div>
                <button className="astro-send-button" type="submit" aria-label="Send reply" disabled={sendingThread || (!threadDraft.trim() && !pendingThreadAttachment)}>
                  <Send size={18} />
                </button>
              </form>
            </section>
          ) : (
          <div className="astro-channel-wrap">
            <section className="astro-conversation" aria-label={activeChannel ? `${activeChannel.name} conversation` : 'Community conversation'}>
              {error && <div className="astro-error-banner">{error}</div>}
              {infoNotice && <div className="astro-info-banner">{infoNotice}</div>}

              <div className="astro-message-list" ref={messageListRef}>
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
                  const hasOpenMenu = activeMessageMenuId === message.id;
                  return (
                  <article className={`astro-message ${isOwnMessage ? 'is-own' : ''} ${hasOpenMenu ? 'has-open-menu' : ''} ${message.pending ? 'is-pending' : ''} ${message.failed ? 'failed' : ''}`} key={message.id}>
                    {!isOwnMessage && (
                      <button className="astro-avatar" aria-label={`${authorName} profile`}>
                        {initials(authorName)}
                      </button>
                    )}
                    <div className="astro-message-body" onClick={() => setActiveMessageMenuId((current) => current === message.id ? null : message.id)}>
                      {!isOwnMessage && (
                        <div className="astro-message-sender-name">
                          {authorName}
                        </div>
                      )}
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
                        message.body && <p>{renderMessageText(message.body)}</p>
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
                      <div className="astro-message-footer">
                        {showTimestamps && <time>{message.time}</time>}
                        {message.edited && !message.isDeleted && <span>edited</span>}
                        {message.pending && <span>sending</span>}
                        {message.failed && <span>failed</span>}
                      </div>
                      {(() => {
                        const badge = reactionBadges[message.id] || (message.stars > 0 ? { emoji: '😊', count: message.stars } : null);
                        return badge && badge.count > 0 ? (
                          <button
                            type="button"
                            className="astro-reaction-badge"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveMessageMenuId((current) => current === message.id ? null : message.id);
                            }}
                            aria-label={`${badge.count} reactions`}
                          >
                            <span>{badge.emoji}</span>
                            <em>{badge.count}</em>
                          </button>
                        ) : null;
                      })()}
                      <div className="astro-message-menu-host" data-message-menu-root="true">
                        <button
                          type="button"
                          className={`astro-message-menu-trigger ${hasOpenMenu ? 'is-open' : ''}`}
                          onClick={(event) => {
                            event.stopPropagation();
                            setActiveMessageMenuId((current) => current === message.id ? null : message.id);
                          }}
                          disabled={message.isDeleted}
                          aria-label="Open message actions"
                          aria-expanded={hasOpenMenu}
                        >
                          <ChevronDown size={14} />
                        </button>
                        {hasOpenMenu && (
                          <div className="astro-message-menu" onClick={(event) => event.stopPropagation()}>
                            <div className="astro-message-menu-list">
                              <button type="button" onClick={() => { toggleReaction(message.id, 'Helpful'); setActiveMessageMenuId(null); }} disabled={message.isDeleted}>
                                <Smile size={18} />
                                <span>{myReactions.has(`${message.id}:Helpful`) ? 'Marked Helpful ✓' : 'Mark Helpful'}</span>
                              </button>
                              <button type="button" onClick={() => { toggleSaved(message.id); setActiveMessageMenuId(null); }} disabled={message.isDeleted}>
                                <Bookmark size={18} />
                                <span>{savedMessages.has(message.id) ? 'Saved ✓' : 'Save Message'}</span>
                              </button>
                              <button type="button" onClick={() => openThread(message)} disabled={message.isDeleted}>
                                <MessageSquare size={18} />
                                <span>Reply in thread</span>
                              </button>
                              <button type="button" onClick={() => copyMessage(message)} disabled={message.isDeleted || (!message.body && !message.imageBase64)}>
                                <Copy size={18} />
                                <span>Copy message</span>
                              </button>
                              <button type="button" onClick={() => forwardMessage(message)} disabled={message.isDeleted || (!message.body && !message.imageBase64)}>
                                <Forward size={18} />
                                <span>Forward</span>
                              </button>
                              <button type="button" onClick={() => showMessageInfo(message, authorName)}>
                                <Info size={18} />
                                <span>Message info</span>
                              </button>
                              {isOwnMessage && (
                                <>
                                  <hr />
                                  <button type="button" className="is-delete" onClick={() => confirmDeleteMessage(message.id)} disabled={message.isDeleted}>
                                    <Trash2 size={18} />
                                    <span>Delete</span>
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </article>
                );
                })}
              </div>
              {typingNames.length > 0 && (
                <div className="astro-typing-line">
                  <span>{typingNames.join(', ')} {typingNames.length === 1 ? 'is' : 'are'} typing</span>
                  <span className="astro-typing-dots"><i /><i /><i /></span>
                </div>
              )}
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
                  onChange={(event) => {
                    const nextDraft = event.target.value;
                    setDraft(nextDraft);
                    setMentionPickerOpen(/@[\w.-]*$/.test(nextDraft));
                  }}
                  onFocus={() => setMentionPickerOpen(/@[\w.-]*$/.test(draft))}
                  onKeyDown={(event) => {
                    if (event.key === 'Escape') setMentionPickerOpen(false);
                  }}
                  placeholder={activeChannel ? `Message #${activeChannel.name}` : 'Select a channel...'}
                  disabled={!activeChannel || sending}
                />
                {mentionPickerOpen && mentionMembers.length > 0 && (
                  <div className="astro-mention-menu" role="listbox" aria-label="Mention member">
                    {mentionMembers.map((member) => {
                      const displayName = member.display_name || member.username || 'Astrologer';
                      const username = mentionHandle(member);
                      return (
                        <button type="button" role="option" key={member.user_id || username} onMouseDown={(event) => event.preventDefault()} onClick={() => selectMention(member)}>
                          <span className="astro-mention-avatar">{initials(displayName)}</span>
                          <span>
                            <strong>{displayName}</strong>
                            <em>@{username.replace(/^@/, '')}</em>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
              <button className="astro-send-button" type="submit" aria-label="Send message" disabled={!activeChannel || sending || (!draft.trim() && !pendingAttachment)}>
                <Send size={18} />
              </button>
            </form>
            )}
          </div>
          )}

          {forwardingMessage && (
            <div className="astro-forward-overlay" role="presentation" onMouseDown={() => setForwardingMessage(null)}>
              <div className="astro-forward-dialog" role="dialog" aria-modal="true" aria-label="Forward message" onMouseDown={(event) => event.stopPropagation()}>
                <div className="astro-forward-head">
                  <div>
                    <span>Forward message</span>
                    <strong>{forwardingMessage.body || 'Attachment message'}</strong>
                  </div>
                  <button type="button" onClick={() => setForwardingMessage(null)} aria-label="Close forward menu">
                    <X size={18} />
                  </button>
                </div>
                <div className="astro-forward-list">
                  {forwardableChannels.map((channel) => (
                    <button type="button" key={channel.id} onClick={() => forwardMessageToChannel(channel.id)} disabled={channel.id === activeChannelId}>
                      <Hash size={17} />
                      <span>{channel.name}</span>
                      <em>{channel.group}</em>
                    </button>
                  ))}
                  {!forwardableChannels.length && <p>No channels available to forward.</p>}
                </div>
              </div>
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
