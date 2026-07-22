import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Calendar,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Filter,
  History,
  MapPin,
  PlayCircle,
  RefreshCcw,
  Search,
  ShieldCheck,
  Users,
  X,
  XCircle,
} from 'lucide-react';
import { adminApi } from '../api/adminApi';
import type {
  AdminAstrologerApplication,
  AdminAuditLog,
  AdminMetrics,
  ConsultationRequest,
} from '../api/adminApi';
import { apiErrorMessage } from '../api/errors';
import { useAuth } from '../auth/useAuth';
import KundaliChartWrapper from '../components/charts/KundaliChartWrapper';
import type {
  AstrologySnapshot,
  ChartData,
  ChartSignMap,
  ConsultationCase,
  PlanetaryPosition,
} from '../features/consultation/types';

type AdminTab = 'overview' | 'consultations' | 'applications' | 'audit';

type ConfirmConfig = {
  title: string;
  message: string;
  confirmLabel: string;
  tone?: 'primary' | 'danger';
  noteLabel?: string;
  noteRequired?: boolean;
  meetingLinkLabel?: string;
  onConfirm: (values: { note: string; meetingLink: string }) => Promise<void>;
};

const notAvailable = '-';

const displayValue = (value: unknown) => {
  if (value === null || value === undefined || value === '') return notAvailable;
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
};

const formatDateTime = (value?: string) => {
  if (!value) return notAvailable;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

const normalizeStatus = (value?: string) => (value || '').toLowerCase();

const statusClass = (status?: string) => {
  const normalized = normalizeStatus(status);
  const classes: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800',
    requested: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800',
    pending_payment: 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800',
    submitted: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800',
    accepted: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800',
    confirmed: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800',
    in_progress: 'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-800',
    active: 'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-800',
    completed: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800',
    approved: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800',
    rejected: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800',
    suspended: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800',
    needs_more_information: 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800',
  };
  return classes[normalized] || 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700';
};

const compactStatus = (status?: string) => displayValue(status).replaceAll('_', ' ');

const paymentStatusFor = (request: ConsultationRequest, detail?: ConsultationCase) => {
  const consultationPayment = detail?.consultation?.payment_status;
  const directPayment = request.payment_status || detail?.consultation?.payment_status;
  const amount = Number(request.amount ?? request.quoted_price ?? detail?.consultation?.quoted_price ?? 0);
  if (normalizeStatus(consultationPayment || directPayment) === 'paid') return 'paid';
  if (Number.isFinite(amount) && amount > 0 && ['confirmed', 'queued', 'requested', 'active', 'completed'].includes(normalizeStatus(request.status))) {
    return 'paid';
  }
  return normalizeStatus(directPayment);
};

const paymentAmountFor = (request: ConsultationRequest, detail?: ConsultationCase) => {
  const amount = request.amount ?? request.quoted_price ?? detail?.consultation?.quoted_price;
  const numeric = Number(amount);
  if (!Number.isFinite(numeric) || numeric <= 0) return '';
  return `₹${numeric}`;
};

const snapshotFor = (request: ConsultationRequest | ConsultationCase): AstrologySnapshot | null =>
  request.chart_snapshot || request.astrological_snapshot || null;

const chartFor = (snapshot: AstrologySnapshot | null): ChartData | null => {
  const chart = snapshot?.chart;
  if (chart) return chart;
  const sourceChart = snapshot?.source_result?.chart;
  return sourceChart && typeof sourceChart === 'object' ? sourceChart as ChartData : null;
};

const mainChartData = (chart: ChartData | null): ChartSignMap | null =>
  chart?.signs || chart?.divisional_charts?.D1 || null;

const interpretationText = (value: unknown) => {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (typeof value !== 'object') return '';
  const data = value as { answer?: { text?: string }; verdict?: { summary?: string }; title?: string };
  return data.answer?.text || data.verdict?.summary || data.title || '';
};

const metricItems = (metrics: AdminMetrics | null) => {
  if (!metrics) return [];
  const preferred = [
    ['total_users', 'Total Users'],
    ['active_consultations', 'Active Consultations'],
    ['completed_consultations', 'Completed Consultations'],
    ['revenue', 'Revenue'],
  ];
  const known = preferred
    .filter(([key]) => metrics[key] !== undefined)
    .map(([key, label]) => ({ key, label, value: metrics[key] }));
  const extras = Object.entries(metrics)
    .filter(([key]) => !preferred.some(([preferredKey]) => preferredKey === key))
    .slice(0, 4)
    .map(([key, value]) => ({ key, label: key.replaceAll('_', ' '), value }));
  return [...known, ...extras];
};

const DataRow = ({ label, value }: { label: string; value: unknown }) => (
  <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
    <dt className="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">{label}</dt>
    <dd className="mt-1 break-words text-sm text-gray-800 dark:text-gray-100">{displayValue(value)}</dd>
  </div>
);

const EmptyState = ({ title, message }: { title: string; message: string }) => (
  <div className="state-panel">
    <h3 className="text-lg font-bold">{title}</h3>
    <p>{message}</p>
  </div>
);

const StatusBadge = ({ status }: { status?: string }) => (
  <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${statusClass(status)}`}>
    {compactStatus(status)}
  </span>
);

const JsonDetails = ({ title, data }: { title: string; data: unknown }) => {
  if (!data) return null;
  return (
    <details className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
      <summary className="cursor-pointer text-sm font-bold text-gray-700 dark:text-gray-200">{title}</summary>
      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded bg-gray-50 p-3 text-xs leading-relaxed text-gray-700 dark:bg-gray-900 dark:text-gray-300">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
};

const PlanetTable = ({ planets }: { planets?: PlanetaryPosition[] }) => {
  if (!Array.isArray(planets) || planets.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-200 px-3 py-2 text-sm font-bold dark:border-gray-700">Planetary Positions</div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-500 dark:bg-gray-900 dark:text-gray-400">
            <tr>
              <th className="px-3 py-2">Planet</th>
              <th className="px-3 py-2">Sign</th>
              <th className="px-3 py-2">House</th>
              <th className="px-3 py-2">Degree</th>
              <th className="px-3 py-2">Nakshatra</th>
              <th className="px-3 py-2">Pada</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {planets.map((planet, index) => (
              <tr key={`${planet.name}-${index}`}>
                <td className="px-3 py-2 font-medium">{planet.name}</td>
                <td className="px-3 py-2">{displayValue(planet.sign)}</td>
                <td className="px-3 py-2">{displayValue(planet.house)}</td>
                <td className="px-3 py-2">{displayValue(planet.formatted_degree || planet.longitude)}</td>
                <td className="px-3 py-2">{displayValue(planet.nakshatra)}</td>
                <td className="px-3 py-2">{displayValue(planet.pada)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const CaseDetail = ({ request, detail, loading }: { request: ConsultationRequest; detail?: ConsultationCase; loading: boolean }) => {
  const activeCase = detail || request;
  const snapshot = snapshotFor(activeCase);
  const chart = chartFor(snapshot);
  const d1 = mainChartData(chart);
  const planets = snapshot?.planetary_positions || chart?.planets;
  const interpretation = interpretationText(snapshot?.interpretation || chart?.interpretation);
  const user = detail?.user;
  const consultation = detail?.consultation;

  return (
    <div className="border-t border-gray-100 bg-gray-50/80 p-4 dark:border-gray-700 dark:bg-gray-900/30 sm:p-5">
      {loading && <div className="mb-4 text-sm text-gray-500">Loading complete case details...</div>}

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section>
          <h4 className="mb-3 text-sm font-bold uppercase tracking-wider text-gray-500">User Details</h4>
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <DataRow label="Name" value={user?.full_name || request.name} />
            <DataRow label="Email" value={user?.email || request.email} />
            <DataRow label="Phone" value={user?.mobile_number || request.phone} />
            <DataRow label="Birth date" value={user?.date_of_birth || request.date_of_birth} />
            <DataRow label="Birth time" value={user?.time_of_birth || request.time_of_birth} />
            <DataRow label="Birth place" value={user?.place || request.place_of_birth} />
          </dl>
        </section>

        <section>
          <h4 className="mb-3 text-sm font-bold uppercase tracking-wider text-gray-500">Consultation Details</h4>
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <DataRow label="Case ID" value={activeCase.case_id || activeCase.id} />
            <DataRow label="Source" value={activeCase.source_type} />
            <DataRow label="Chart type" value={activeCase.chart_type} />
            <DataRow label="Preferred date" value={consultation?.preferred_date || request.preferred_date} />
            <DataRow label="Preferred time" value={consultation?.preferred_time || request.preferred_time} />
            <DataRow label="Created" value={formatDateTime(activeCase.created_at)} />
          </dl>
        </section>
      </div>

      <section className="mb-6">
        <h4 className="mb-3 text-sm font-bold uppercase tracking-wider text-gray-500">Question</h4>
        <div className="whitespace-pre-wrap rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          {consultation?.question || request.question}
        </div>
      </section>

      <section>
        <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-gray-500">
          <FileText size={16} /> Kundali Snapshot
        </h4>
        {snapshot ? (
          <div className="space-y-4">
            {d1 && (
              <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                <h5 className="mb-3 text-sm font-bold">Main Lagna / D1 Chart</h5>
                <KundaliChartWrapper data={d1} className="max-w-[420px]" />
              </div>
            )}
            <PlanetTable planets={planets} />
            {interpretation && (
              <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                <h5 className="mb-2 text-sm font-bold">Generated Interpretation</h5>
                <div className="max-h-72 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                  {interpretation}
                </div>
              </div>
            )}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <JsonDetails title="Dasha Details" data={snapshot?.dashas || chart?.dashas} />
              <JsonDetails title="Calculation Metadata" data={snapshot?.calculation_metadata || chart?.meta} />
              <JsonDetails title="Houses" data={snapshot?.house_positions || chart?.houses} />
              <JsonDetails title="Aspects / Yogas" data={{ aspects: snapshot?.aspects || chart?.aspects, yogas: snapshot?.yogas || chart?.yogas }} />
            </div>
          </div>
        ) : (
          <EmptyState title="No chart snapshot" message="This request does not have an attached Kundali snapshot." />
        )}
      </section>
    </div>
  );
};

const ConfirmDialog = ({ config, onClose }: { config: ConfirmConfig; onClose: () => void }) => {
  const [note, setNote] = useState('');
  const [meetingLink, setMeetingLink] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const canSubmit = !config.noteRequired || note.trim().length > 0;

  const submit = async () => {
    if (!canSubmit) return;
    try {
      setSaving(true);
      setError('');
      await config.onConfirm({ note: note.trim(), meetingLink: meetingLink.trim() });
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-xl dark:bg-gray-900" role="dialog" aria-modal="true" aria-labelledby="admin-confirm-title">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 id="admin-confirm-title" className="text-xl font-bold">{config.title}</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{config.message}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-md p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Close dialog">
            <X size={18} />
          </button>
        </div>

        {config.meetingLinkLabel && (
          <label className="mb-4 block text-sm font-medium">
            {config.meetingLinkLabel}
            <input
              value={meetingLink}
              onChange={(event) => setMeetingLink(event.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-950"
              placeholder="https://meet.google.com/..."
            />
          </label>
        )}

        {config.noteLabel && (
          <label className="block text-sm font-medium">
            {config.noteLabel}
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              className="mt-1 min-h-28 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-950"
              maxLength={2000}
            />
          </label>
        )}

        {error && <div className="app-alert app-alert--error mt-4" role="alert">{error}</div>}

        <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button type="button" onClick={onClose} className="rounded-lg border border-gray-300 px-4 py-2 font-medium hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800">
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!canSubmit || saving}
            className={`rounded-lg px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 ${config.tone === 'danger' ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-900 hover:bg-black dark:bg-white dark:text-gray-950 dark:hover:bg-gray-200'}`}
          >
            {saving ? 'Saving...' : config.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

const AdminDashboardPage: React.FC = () => {
  const { session } = useAuth();
  const currentUserId = session?.user?.id;
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [requests, setRequests] = useState<ConsultationRequest[]>([]);
  const [applications, setApplications] = useState<AdminAstrologerApplication[]>([]);
  const [auditLogs, setAuditLogs] = useState<AdminAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [caseDetails, setCaseDetails] = useState<Record<string, ConsultationCase>>({});
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [consultationSearch, setConsultationSearch] = useState('');
  const [consultationStatus, setConsultationStatus] = useState('all');
  const [applicationSearch, setApplicationSearch] = useState('');
  const [applicationStatus, setApplicationStatus] = useState('all');
  const [confirmConfig, setConfirmConfig] = useState<ConfirmConfig | null>(null);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError('');
      const [metricsData, requestsData, applicationsData, logsData] = await Promise.all([
        adminApi.getMetrics(),
        adminApi.getConsultationRequests(),
        adminApi.getAstrologerApplications(),
        adminApi.getAuditLogs({ limit: 100 }),
      ]);
      setMetrics(metricsData);
      setRequests(requestsData.requests || []);
      setApplications(applicationsData.applications || []);
      setAuditLogs(logsData.logs || []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const filteredRequests = useMemo(() => {
    const search = consultationSearch.trim().toLowerCase();
    return requests.filter((request) => {
      const matchesStatus = consultationStatus === 'all' || normalizeStatus(request.status) === consultationStatus;
      const haystack = [
        request.name,
        request.email,
        request.phone,
        request.topic,
        request.question,
        request.case_id,
      ].join(' ').toLowerCase();
      return matchesStatus && (!search || haystack.includes(search));
    });
  }, [consultationSearch, consultationStatus, requests]);

  const filteredApplications = useMemo(() => {
    const search = applicationSearch.trim().toLowerCase();
    return applications.filter((application) => {
      const status = normalizeStatus(application.status);
      const matchesStatus = applicationStatus === 'all' || status === applicationStatus;
      const haystack = [
        application.name,
        application.email,
        application.phone,
        application.expertise,
        application.bio,
        application.state,
        application.country,
      ].join(' ').toLowerCase();
      return matchesStatus && (!search || haystack.includes(search));
    });
  }, [applicationSearch, applicationStatus, applications]);

  const consultationStatuses = useMemo(
    () => Array.from(new Set(requests.map((request) => normalizeStatus(request.status)).filter(Boolean))).sort(),
    [requests],
  );

  const applicationStatuses = useMemo(
    () => Array.from(new Set(applications.map((application) => normalizeStatus(application.status)).filter(Boolean))).sort(),
    [applications],
  );

  const refreshAudit = async () => {
    const logsData = await adminApi.getAuditLogs({ limit: 100 });
    setAuditLogs(logsData.logs || []);
  };

  const updateStatus = async (id: string, status: string, link?: string) => {
    await adminApi.updateConsultationStatus(id, { status, meeting_link: link || undefined });
    await loadDashboard();
  };

  const updateApplication = async (application: AdminAstrologerApplication, status: 'approved' | 'rejected' | 'pending' | 'needs_more_information' | 'suspended', message: string) => {
    await adminApi.updateAstrologerApplication(application.id, {
      status,
      message,
      reapply_allowed: status === 'rejected',
      reapply_after_days: status === 'rejected' ? 30 : 0,
    });
    await loadDashboard();
  };

  const toggleRequest = async (request: ConsultationRequest) => {
    const nextId = expandedId === request.id ? null : request.id;
    setExpandedId(nextId);
    if (!nextId || caseDetails[request.id]) return;

    setDetailLoadingId(request.id);
    try {
      const data = await adminApi.getConsultationCase(request.case_id || request.id);
      if (data.case) setCaseDetails(prev => ({ ...prev, [request.id]: data.case }));
    } catch {
      setError('Full case detail could not be loaded. Showing summary data only.');
    } finally {
      setDetailLoadingId(null);
    }
  };

  const tabs: Array<{ id: AdminTab; label: string; icon: React.ReactNode }> = [
    { id: 'overview', label: 'Overview', icon: <ShieldCheck size={16} /> },
    { id: 'consultations', label: 'Consultations', icon: <Calendar size={16} /> },
    { id: 'applications', label: 'Applications', icon: <Users size={16} /> },
    { id: 'audit', label: 'Audit Log', icon: <History size={16} /> },
  ];

  return (
    <div className="app-page">
      <div className="page-header gap-4">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">Admin Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage consultations, astrologer approvals, and admin audit history.</p>
        </div>
        <button
          type="button"
          onClick={loadDashboard}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-gray-100 px-4 py-2 text-sm font-medium transition hover:bg-gray-200 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700"
        >
          <RefreshCcw size={16} /> Refresh
        </button>
      </div>

      {error && <div className="app-alert app-alert--error mb-4" role="alert">{error}</div>}

      <div className="mb-6 overflow-x-auto border-b border-gray-200 dark:border-gray-700">
        <div className="flex min-w-max gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-bold ${activeTab === tab.id ? 'border-gray-900 text-gray-950 dark:border-white dark:text-white' : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-gray-100'}`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="state-panel" role="status">Loading admin workspace...</div>
      ) : (
        <>
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {metricItems(metrics).map((item) => (
                  <div key={item.key} className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
                    <div className="text-sm font-bold uppercase tracking-wider text-gray-500">{item.label}</div>
                    <div className="mt-2 text-3xl font-bold">{displayValue(item.value)}</div>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
                  <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-gray-500"><Calendar size={16} /> Consultations</div>
                  <div className="mt-3 text-2xl font-bold">{requests.length}</div>
                  <p className="mt-1 text-sm text-gray-500">{requests.filter(req => ['pending', 'requested'].includes(normalizeStatus(req.status))).length} pending review</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
                  <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-gray-500"><Users size={16} /> Applications</div>
                  <div className="mt-3 text-2xl font-bold">{applications.length}</div>
                  <p className="mt-1 text-sm text-gray-500">{applications.filter(app => ['pending', 'submitted'].includes(normalizeStatus(app.status))).length} awaiting admin action</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
                  <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-gray-500"><History size={16} /> Audit Events</div>
                  <div className="mt-3 text-2xl font-bold">{auditLogs.length}</div>
                  <p className="mt-1 text-sm text-gray-500">Latest admin actions loaded</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'consultations' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800 md:grid-cols-[1fr_220px]">
                <label className="text-sm font-medium">
                  <span className="mb-1 flex items-center gap-2"><Search size={16} /> Search</span>
                  <input value={consultationSearch} onChange={(event) => setConsultationSearch(event.target.value)} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-950" placeholder="Name, email, topic, case ID" />
                </label>
                <label className="text-sm font-medium">
                  <span className="mb-1 flex items-center gap-2"><Filter size={16} /> Status</span>
                  <select value={consultationStatus} onChange={(event) => setConsultationStatus(event.target.value)} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-950">
                    <option value="all">All statuses</option>
                    {consultationStatuses.map(status => <option key={status} value={status}>{compactStatus(status)}</option>)}
                  </select>
                </label>
              </div>

              {filteredRequests.length === 0 ? (
                <EmptyState title="No consultation requests" message="No requests match the current filters." />
              ) : (
                <div className="grid gap-4">
                  {filteredRequests.map((req) => {
                    const isExpanded = expandedId === req.id;
                    const detail = caseDetails[req.id];
                    const paymentStatus = paymentStatusFor(req, detail);
                    const paymentAmount = paymentAmountFor(req, detail);
                    return (
                      <div key={req.id} className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
                        {paymentStatus === 'paid' && (
                          <div className="flex flex-wrap items-center gap-2 border-b border-green-200 bg-green-50 px-4 py-3 text-sm font-bold text-green-800 dark:border-green-800 dark:bg-green-900/25 dark:text-green-200 sm:px-5">
                            <CheckCircle size={18} />
                            <span>Payment Successful</span>
                            <span className="font-medium text-green-700 dark:text-green-300">Verified for admin cross-check{paymentAmount ? ` · ${paymentAmount}` : ''}</span>
                          </div>
                        )}
                        <button type="button" className="w-full p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 sm:p-5" onClick={() => toggleRequest(req)}>
                          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                            <div className="min-w-0 flex-1">
                              <div className="mb-2 flex flex-wrap items-center gap-3">
                                <h3 className="break-words text-lg font-bold">{req.name}</h3>
                                <StatusBadge status={req.status} />
                                {paymentStatus && paymentStatus !== 'paid' && <StatusBadge status={`payment ${paymentStatus}`} />}
                              </div>
                              <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-500">
                                <span className="flex items-center gap-1"><FileText size={14} /> {displayValue(req.topic)}</span>
                                <span className="flex items-center gap-1"><Calendar size={14} /> {displayValue(req.date_of_birth)}</span>
                                <span className="flex items-center gap-1"><Clock size={14} /> {displayValue(req.time_of_birth)}</span>
                                <span className="flex items-center gap-1"><MapPin size={14} /> {displayValue(req.place_of_birth)}</span>
                              </div>
                            </div>
                            <div className="flex items-center justify-between gap-4 md:justify-end">
                              <div className="text-sm md:text-right">
                                <div className="text-gray-400">Created</div>
                                <div className="font-medium">{formatDateTime(req.created_at)}</div>
                              </div>
                              {isExpanded ? <ChevronUp className="text-gray-400" /> : <ChevronDown className="text-gray-400" />}
                            </div>
                          </div>
                        </button>

                        {isExpanded && (
                          <>
                            <CaseDetail request={req} detail={detail} loading={detailLoadingId === req.id} />
                            <div className="flex flex-wrap gap-3 px-4 pb-4 sm:px-5 sm:pb-5">
                              {['pending', 'requested'].includes(req.status) && (
                                <>
                                  <button type="button" onClick={() => setConfirmConfig({
                                    title: 'Accept consultation',
                                    message: 'Confirm this booking and optionally attach the meeting link.',
                                    confirmLabel: 'Accept',
                                    meetingLinkLabel: 'Meeting link',
                                    onConfirm: ({ meetingLink }) => updateStatus(req.id, 'confirmed', meetingLink),
                                  })} className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700">
                                    <CheckCircle size={18} /> Accept
                                  </button>
                                  <button type="button" onClick={() => setConfirmConfig({
                                    title: 'Reject consultation',
                                    message: 'This will reject the consultation request.',
                                    confirmLabel: 'Reject',
                                    tone: 'danger',
                                    onConfirm: () => updateStatus(req.id, 'rejected'),
                                  })} className="inline-flex items-center gap-2 rounded-lg bg-red-100 px-4 py-2 font-medium text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-300">
                                    <XCircle size={18} /> Reject
                                  </button>
                                </>
                              )}
                              {['accepted', 'confirmed'].includes(req.status) && (
                                <button type="button" onClick={() => setConfirmConfig({
                                  title: 'Start consultation',
                                  message: 'Move this accepted consultation into progress.',
                                  confirmLabel: 'Start',
                                  onConfirm: () => updateStatus(req.id, 'active'),
                                })} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700">
                                  <PlayCircle size={18} /> Start Progress
                                </button>
                              )}
                              {['accepted', 'confirmed', 'in_progress', 'active'].includes(req.status) && (
                                <button type="button" onClick={() => setConfirmConfig({
                                  title: 'Complete consultation',
                                  message: 'Mark this consultation complete.',
                                  confirmLabel: 'Complete',
                                  onConfirm: () => updateStatus(req.id, 'completed'),
                                })} className="inline-flex items-center gap-2 rounded-lg bg-green-100 px-4 py-2 font-medium text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-300">
                                  <CheckCircle size={18} /> Mark Completed
                                </button>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === 'applications' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800 md:grid-cols-[1fr_220px]">
                <label className="text-sm font-medium">
                  <span className="mb-1 flex items-center gap-2"><Search size={16} /> Search</span>
                  <input value={applicationSearch} onChange={(event) => setApplicationSearch(event.target.value)} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-950" placeholder="Name, email, phone, expertise" />
                </label>
                <label className="text-sm font-medium">
                  <span className="mb-1 flex items-center gap-2"><Filter size={16} /> Status</span>
                  <select value={applicationStatus} onChange={(event) => setApplicationStatus(event.target.value)} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-950">
                    <option value="all">All statuses</option>
                    {applicationStatuses.map(status => <option key={status} value={status}>{compactStatus(status)}</option>)}
                  </select>
                </label>
              </div>

              {filteredApplications.length === 0 ? (
                <EmptyState title="No astrologer applications" message="No applications match the current filters." />
              ) : (
                <div className="grid gap-4">
                  {filteredApplications.map((application) => {
                    const ownsApplication = Boolean(currentUserId && (application.user_id === currentUserId || application.id === currentUserId));
                    return (
                      <article key={application.id} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800 sm:p-5">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                          <div className="min-w-0">
                            <div className="mb-2 flex flex-wrap items-center gap-3">
                              <h3 className="break-words text-lg font-bold">{application.name}</h3>
                              <StatusBadge status={application.status} />
                            </div>
                            <div className="grid grid-cols-1 gap-2 text-sm text-gray-600 dark:text-gray-300 sm:grid-cols-2">
                              <div>Email: {displayValue(application.email)}</div>
                              <div>Phone: {displayValue(application.phone)}</div>
                              <div>Experience: {displayValue(application.experience)}</div>
                              <div>Location: {displayValue([application.state, application.country].filter(Boolean).join(', '))}</div>
                            </div>
                          </div>
                          {ownsApplication && (
                            <div className="inline-flex items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-sm text-orange-700 dark:border-orange-800 dark:bg-orange-900/20 dark:text-orange-300">
                              <AlertTriangle size={16} /> Self-review disabled
                            </div>
                          )}
                        </div>

                        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                          <DataRow label="Expertise" value={application.expertise} />
                          <DataRow label="Submitted" value={formatDateTime(application.created_at)} />
                        </div>
                        {application.bio && <p className="mt-4 max-h-32 overflow-y-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-900 dark:text-gray-300">{application.bio}</p>}

                        {application.proofs && application.proofs.length > 0 && (
                          <details className="mt-4 rounded-lg border border-gray-200 p-3 dark:border-gray-700">
                            <summary className="cursor-pointer text-sm font-bold">Supporting Proofs</summary>
                            <div className="mt-3 grid gap-2">
                              {application.proofs.map((proof) => (
                                <a key={proof.id || proof.url} href={proof.url} target="_blank" rel="noreferrer" className="break-all text-sm font-medium text-blue-700 hover:underline dark:text-blue-300">
                                  {proof.filename || proof.type || proof.url}
                                </a>
                              ))}
                            </div>
                          </details>
                        )}

                        <div className="mt-5 flex flex-wrap gap-3">
                          <button type="button" disabled={ownsApplication} onClick={() => setConfirmConfig({
                            title: 'Approve astrologer',
                            message: 'This grants verified astrologer and community access.',
                            confirmLabel: 'Approve',
                            noteLabel: 'Audit note',
                            onConfirm: ({ note }) => updateApplication(application, 'approved', note),
                          })} className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50">
                            <CheckCircle size={18} /> Approve
                          </button>
                          <button type="button" disabled={ownsApplication} onClick={() => setConfirmConfig({
                            title: 'Request more information',
                            message: 'The applicant remains pending and will see your message.',
                            confirmLabel: 'Request Info',
                            noteLabel: 'Message to applicant',
                            noteRequired: true,
                            onConfirm: ({ note }) => updateApplication(application, 'needs_more_information', note),
                          })} className="inline-flex items-center gap-2 rounded-lg bg-orange-100 px-4 py-2 font-medium text-orange-700 hover:bg-orange-200 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-orange-900/30 dark:text-orange-300">
                            <AlertTriangle size={18} /> Needs Info
                          </button>
                          <button type="button" disabled={ownsApplication} onClick={() => setConfirmConfig({
                            title: 'Reject astrologer',
                            message: 'This removes pending astrologer access and records the reason.',
                            confirmLabel: 'Reject',
                            tone: 'danger',
                            noteLabel: 'Reason',
                            noteRequired: true,
                            onConfirm: ({ note }) => updateApplication(application, 'rejected', note),
                          })} className="inline-flex items-center gap-2 rounded-lg bg-red-100 px-4 py-2 font-medium text-red-700 hover:bg-red-200 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-red-900/30 dark:text-red-300">
                            <XCircle size={18} /> Reject
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === 'audit' && (
            <div className="space-y-4">
              <div className="flex justify-end">
                <button type="button" onClick={refreshAudit} className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700">
                  <RefreshCcw size={16} /> Refresh Audit
                </button>
              </div>
              {auditLogs.length === 0 ? (
                <EmptyState title="No audit events" message="No admin audit events were returned." />
              ) : (
                <div className="overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-500 dark:bg-gray-900 dark:text-gray-400">
                        <tr>
                          <th className="px-4 py-3">Time</th>
                          <th className="px-4 py-3">Actor</th>
                          <th className="px-4 py-3">Entity</th>
                          <th className="px-4 py-3">Action</th>
                          <th className="px-4 py-3">Details</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                        {auditLogs.map((log, index) => (
                          <tr key={log.id || `${log.entity_id}-${index}`}>
                            <td className="px-4 py-3 align-top">{formatDateTime(log.created_at)}</td>
                            <td className="max-w-[180px] break-all px-4 py-3 align-top">{displayValue(log.actor_user_id)}</td>
                            <td className="px-4 py-3 align-top">
                              <div className="font-medium">{log.entity_type}</div>
                              <div className="max-w-[220px] break-all text-xs text-gray-500">{log.entity_id}</div>
                            </td>
                            <td className="px-4 py-3 align-top font-medium">{compactStatus(log.action)}</td>
                            <td className="px-4 py-3 align-top">
                              <details>
                                <summary className="cursor-pointer font-medium text-blue-700 dark:text-blue-300">View change</summary>
                                <pre className="mt-2 max-h-56 min-w-[280px] overflow-auto whitespace-pre-wrap rounded bg-gray-50 p-3 text-xs dark:bg-gray-900">
                                  {JSON.stringify({ before: log.before_json, after: log.after_json }, null, 2)}
                                </pre>
                              </details>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {confirmConfig && <ConfirmDialog config={confirmConfig} onClose={() => setConfirmConfig(null)} />}
    </div>
  );
};

export default AdminDashboardPage;
