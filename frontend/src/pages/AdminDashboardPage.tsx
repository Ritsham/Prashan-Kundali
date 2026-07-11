import React, { useEffect, useState } from 'react';
import { adminApi } from '../api/adminApi';
import type { ConsultationRequest } from '../api/adminApi';
import { Calendar, Clock, MapPin, FileText, CheckCircle, XCircle, PlayCircle, Eye, ChevronDown, ChevronUp } from 'lucide-react';
import KundaliChartWrapper from '../components/charts/KundaliChartWrapper';
import type { AstrologySnapshot, ChartData, ChartSignMap, ConsultationCase, PlanetaryPosition } from '../features/consultation/types';

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
  const data = value as {
    answer?: { text?: string };
    verdict?: { summary?: string };
    title?: string;
  };
  return data.answer?.text || data.verdict?.summary || data.title || '';
};

const coordinateText = (latitude: unknown, longitude: unknown) => {
  const hasLatitude = latitude !== null && latitude !== undefined && latitude !== '';
  const hasLongitude = longitude !== null && longitude !== undefined && longitude !== '';
  return hasLatitude && hasLongitude ? `${latitude}, ${longitude}` : notAvailable;
};

const DataRow = ({ label, value }: { label: string; value: unknown }) => (
  <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
    <dt className="text-xs font-bold uppercase tracking-wider text-gray-400">{label}</dt>
    <dd className="mt-1 text-sm text-gray-800 dark:text-gray-100 break-words">{displayValue(value)}</dd>
  </div>
);

const JsonDetails = ({ title, data }: { title: string; data: unknown }) => {
  if (!data) return null;
  return (
    <details className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
      <summary className="cursor-pointer text-sm font-bold text-gray-700 dark:text-gray-200">{title}</summary>
      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded bg-gray-50 dark:bg-gray-900 p-3 text-xs leading-relaxed text-gray-700 dark:text-gray-300">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
};

const PlanetTable = ({ planets }: { planets?: PlanetaryPosition[] }) => {
  if (!Array.isArray(planets) || planets.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <div className="border-b border-gray-200 dark:border-gray-700 px-3 py-2 text-sm font-bold">Planetary Positions</div>
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

const DivisionalCharts = ({ charts }: { charts?: Record<string, ChartSignMap> }) => {
  if (!charts || Object.keys(charts).length === 0) return null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {Object.entries(charts).map(([name, data]) => (
        <div key={name} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
          <h5 className="mb-2 text-sm font-bold">{name}</h5>
          <KundaliChartWrapper data={data} className="max-w-[300px]" />
        </div>
      ))}
    </div>
  );
};

const CaseDetail = ({
  request,
  detail,
  loading,
}: {
  request: ConsultationRequest;
  detail?: ConsultationCase;
  loading: boolean;
}) => {
  const activeCase = detail || request;
  const snapshot = snapshotFor(activeCase);
  const chart = chartFor(snapshot);
  const d1 = mainChartData(chart);
  const planets = snapshot?.planetary_positions || chart?.planets;
  const dashas = snapshot?.dashas || chart?.dashas;
  const kpSystem = snapshot?.kp_system || chart?.kp_system;
  const meta = snapshot?.calculation_metadata || chart?.meta;
  const questionContext = snapshot?.question_context || chart?.question;
  const interpretation = interpretationText(snapshot?.interpretation || chart?.interpretation);
  const user = detail?.user;
  const consultation = detail?.consultation;

  return (
    <div className="p-5 border-t border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/20">
      {loading && <div className="mb-4 text-sm text-gray-500">Loading complete case details...</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <section>
          <h4 className="font-bold text-sm text-gray-400 uppercase tracking-wider mb-3">User Details</h4>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <DataRow label="Name" value={user?.full_name || request.name} />
            <DataRow label="Email" value={user?.email || request.email} />
            <DataRow label="Phone" value={user?.mobile_number || request.phone} />
            <DataRow label="Gender" value={user?.gender} />
            <DataRow label="Birth date" value={user?.date_of_birth || request.date_of_birth} />
            <DataRow label="Birth time" value={user?.time_of_birth || request.time_of_birth} />
            <DataRow label="Birth place" value={user?.place || request.place_of_birth} />
            <DataRow label="Coordinates" value={coordinateText(user?.latitude, user?.longitude)} />
          </dl>
        </section>

        <section>
          <h4 className="font-bold text-sm text-gray-400 uppercase tracking-wider mb-3">Consultation Details</h4>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <DataRow label="Case ID" value={activeCase.case_id || activeCase.id} />
            <DataRow label="Status" value={activeCase.status || activeCase.case_status} />
            <DataRow label="Source" value={activeCase.source_type} />
            <DataRow label="Chart type" value={activeCase.chart_type} />
            <DataRow label="Preferred date" value={consultation?.preferred_date || request.preferred_date} />
            <DataRow label="Preferred time" value={consultation?.preferred_time || request.preferred_time} />
            <DataRow label="Mode" value={consultation?.consultation_mode || request.consultation_mode} />
            <DataRow label="Created" value={formatDateTime(activeCase.created_at)} />
          </dl>
        </section>
      </div>

      <section className="mb-6">
        <h4 className="font-bold text-sm text-gray-400 uppercase tracking-wider mb-3">Question</h4>
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 whitespace-pre-wrap">
          {consultation?.question || request.question}
        </div>
        {(consultation?.additional_message || request.additional_message) && (
          <div className="mt-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 whitespace-pre-wrap text-sm">
            {consultation?.additional_message || request.additional_message}
          </div>
        )}
      </section>

      <section className="mb-6">
        <h4 className="font-bold text-sm text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Eye size={16} /> Attached Kundali Snapshot
        </h4>
        {snapshot ? (
          <div className="space-y-4">
            {d1 && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                <h5 className="mb-3 text-sm font-bold">Main Lagna / D1 Chart</h5>
                <KundaliChartWrapper data={d1} className="max-w-[420px]" />
              </div>
            )}
            <DivisionalCharts charts={snapshot.divisional_charts || chart?.divisional_charts} />
            <PlanetTable planets={planets} />
            {interpretation && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                <h5 className="mb-2 text-sm font-bold">Generated Interpretation</h5>
                <div className="max-h-72 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                  {interpretation}
                </div>
              </div>
            )}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <JsonDetails title="Dasha Details" data={dashas} />
              <JsonDetails title="KP System" data={kpSystem} />
              <JsonDetails title="Question / Birth Context" data={questionContext} />
              <JsonDetails title="Calculation Metadata" data={meta} />
              <JsonDetails title="Houses" data={snapshot.house_positions || chart?.houses} />
              <JsonDetails title="Aspects / Yogas" data={{ aspects: snapshot.aspects || chart?.aspects, yogas: snapshot.yogas || chart?.yogas }} />
            </div>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 p-8 rounded-xl border border-gray-200 dark:border-gray-700 text-center text-gray-500 italic text-sm">
            No chart snapshot was attached to this request.
          </div>
        )}
      </section>
    </div>
  );
};

const AdminDashboardPage: React.FC = () => {
  const [requests, setRequests] = useState<ConsultationRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [caseDetails, setCaseDetails] = useState<Record<string, ConsultationCase>>({});
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      const data = await adminApi.getConsultationRequests();
      if (data && data.requests) {
        setRequests(data.requests);
      }
    } catch (err) {
      console.error('Failed to load requests', err);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (id: string, status: string, link?: string) => {
    try {
      await adminApi.updateConsultationStatus(id, { status, meeting_link: link });
      fetchRequests();
    } catch (err) {
      console.error('Failed to update status', err);
      alert('Error updating status');
    }
  };

  const handleAccept = (id: string) => {
    const link = prompt('Enter Google Meet / Zoom link for this consultation (Optional):');
    updateStatus(id, 'accepted', link || undefined);
  };

  const toggleRequest = async (request: ConsultationRequest) => {
    const nextId = expandedId === request.id ? null : request.id;
    setExpandedId(nextId);
    if (!nextId || caseDetails[request.id]) return;

    setDetailLoadingId(request.id);
    try {
      const data = await adminApi.getConsultationCase(request.case_id || request.id);
      if (data.case) {
        setCaseDetails(prev => ({ ...prev, [request.id]: data.case }));
      }
    } catch (err) {
      console.warn('Using list row because full case detail could not be loaded', err);
    } finally {
      setDetailLoadingId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage your consultation requests.</p>
        </div>
        <button 
          onClick={fetchRequests}
          className="bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition"
        >
          Refresh Data
        </button>
      </div>

      <div className="space-y-6">
        <h2 className="text-xl font-bold border-b border-gray-200 dark:border-gray-700 pb-2">Consultation Requests</h2>
        
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading requests...</div>
        ) : requests.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700">
            <p className="text-gray-500">No consultation requests found.</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {requests.map(req => {
              const isExpanded = expandedId === req.id;
              
              const statusColors: Record<string, string> = {
                pending: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800',
                accepted: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800',
                completed: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800',
                rejected: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
                in_progress: 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800',
              };

              return (
                <div key={req.id} className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm transition-all">
                  <div 
                    className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    onClick={() => toggleRequest(req)}
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-bold text-lg">{req.name}</h3>
                        <span className={`text-xs px-2.5 py-0.5 rounded-full border uppercase tracking-wider font-bold ${statusColors[req.status] || 'bg-gray-100 text-gray-800 border-gray-200'}`}>
                          {req.status.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-500">
                        <span className="flex items-center gap-1"><FileText size={14}/> {req.topic}</span>
                        <span className="flex items-center gap-1"><Calendar size={14}/> {req.date_of_birth}</span>
                        <span className="flex items-center gap-1"><Clock size={14}/> {req.time_of_birth}</span>
                        <span className="flex items-center gap-1"><MapPin size={14}/> {req.place_of_birth}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <div className="text-right hidden md:block">
                        <div className="text-gray-400">Created</div>
                        <div className="font-medium">{new Date(req.created_at).toLocaleDateString()}</div>
                      </div>
                      {isExpanded ? <ChevronUp className="text-gray-400" /> : <ChevronDown className="text-gray-400" />}
                    </div>
                  </div>

                  {isExpanded && (
                    <>
                      <CaseDetail request={req} detail={caseDetails[req.id]} loading={detailLoadingId === req.id} />
                      <div className="px-5 pb-5 flex flex-wrap gap-3">
                        {req.status === 'pending' && (
                          <>
                            <button onClick={(event) => { event.stopPropagation(); handleAccept(req.id); }} className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition">
                              <CheckCircle size={18} /> Accept
                            </button>
                            <button onClick={(event) => { event.stopPropagation(); updateStatus(req.id, 'rejected'); }} className="flex items-center gap-2 bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-900/30 dark:text-red-400 px-4 py-2 rounded-lg font-medium transition">
                              <XCircle size={18} /> Reject
                            </button>
                          </>
                        )}
                        {req.status === 'accepted' && (
                          <>
                            <button onClick={(event) => { event.stopPropagation(); updateStatus(req.id, 'in_progress'); }} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition">
                              <PlayCircle size={18} /> Start Progress
                            </button>
                            <button onClick={(event) => { event.stopPropagation(); updateStatus(req.id, 'completed'); }} className="flex items-center gap-2 bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-4 py-2 rounded-lg font-medium transition">
                              <CheckCircle size={18} /> Mark Completed
                            </button>
                          </>
                        )}
                        {req.status === 'in_progress' && (
                          <button onClick={(event) => { event.stopPropagation(); updateStatus(req.id, 'completed'); }} className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition">
                            <CheckCircle size={18} /> Complete Consultation
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
    </div>
  );
};

export default AdminDashboardPage;
