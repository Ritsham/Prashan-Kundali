import React, { useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { CalendarClock, ChevronLeft, ChevronRight, ClipboardList, Compass, Sparkles } from 'lucide-react';
import KundaliChartWrapper from '../components/charts/KundaliChartWrapper';

const PrashnaResultPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'interpretation' | 'charts'>('interpretation');
  const [activeChartSlide, setActiveChartSlide] = useState(0);
  const chartTouchStartX = useRef<number | null>(null);

  // result and formData are passed via router state from the PrashnaForm
  const { result, formData } = (location.state as any) || {};

  if (!result) {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center">
        <h2 className="text-2xl font-bold mb-4">No Result Found</h2>
        <p className="text-gray-600 mb-6">It looks like you haven't generated a Prashna Kundli yet.</p>
        <button 
          onClick={() => navigate('/prashna')}
          className="bg-purple-600 text-white px-6 py-2 rounded-lg"
        >
          Go Back
        </button>
      </div>
    );
  }

  const { chart, interpretation } = result;
  const planetEntries = useMemo<[string, any][]>(() => Object.entries(chart?.planets || {}) as [string, any][], [chart?.planets]);
  const interpretationText = (() => {
    if (!interpretation) return '';
    if (typeof interpretation === 'string') return interpretation;
    if (typeof interpretation === 'object') {
      return interpretation.answer?.text || interpretation.verdict?.summary || JSON.stringify(interpretation, null, 2);
    }
    return String(interpretation);
  })();

  const handleBookConsultation = () => {
    window.location.href = '/consultation';
  };

  const jumpTo = (target: 'interpretation' | 'charts') => {
    setActiveTab(target);
    window.requestAnimationFrame(() => {
      document.getElementById(target === 'interpretation' ? 'reading-section' : 'charts-section')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  };

  const mobileChartSlides = [
    { key: 'lagna', label: 'Lagna', icon: Compass },
    { key: 'positions', label: 'Positions', icon: ClipboardList },
    { key: 'dasha', label: 'Dashas', icon: CalendarClock },
  ];

  const moveSlide = (direction: -1 | 1) => {
    setActiveChartSlide((current) => {
      const next = current + direction;
      return Math.max(0, Math.min(mobileChartSlides.length - 1, next));
    });
  };

  const handleChartTouchEnd = (event: React.TouchEvent<HTMLDivElement>) => {
    if (chartTouchStartX.current === null) return;
    const deltaX = chartTouchStartX.current - event.changedTouches[0].clientX;
    chartTouchStartX.current = null;
    if (Math.abs(deltaX) < 44) return;
    moveSlide(deltaX > 0 ? 1 : -1);
  };

  return (
    <main className="prashna-result-page">
      <section className="result-hero-panel">
        <div>
          <p className="result-eyebrow">Personalized Prashna Reading</p>
          <h1>Prashna Kundli Result</h1>
          <p className="result-question">
          Question: <span className="font-medium text-gray-900 dark:text-gray-100">{formData?.question || 'N/A'}</span>
          </p>
        </div>
        <button type="button" onClick={handleBookConsultation} className="result-consult-btn">
          <Sparkles size={18} />
          Consult
        </button>
      </section>

      <nav className="result-quick-nav" aria-label="Result sections">
        <button type="button" className={activeTab === 'interpretation' ? 'active' : ''} onClick={() => jumpTo('interpretation')}>
          Reading
        </button>
        <button type="button" className={activeTab === 'charts' ? 'active' : ''} onClick={() => jumpTo('charts')}>
          Charts
        </button>
        <button type="button" onClick={() => { setActiveTab('charts'); setActiveChartSlide(1); }}>
          Positions
        </button>
        <button type="button" onClick={() => { setActiveTab('charts'); setActiveChartSlide(2); }}>
          Dashas
        </button>
      </nav>

      {/* Tabs Navigation */}
      <div className="result-desktop-tabs">
        <button
          onClick={() => setActiveTab('interpretation')}
          className={activeTab === 'interpretation' ? 'active' : ''}
        >
          Interpretation
        </button>
        <button
          onClick={() => setActiveTab('charts')}
          className={activeTab === 'charts' ? 'active' : ''}
        >
          Charts & Positions
        </button>
      </div>

      {/* Tab Content */}
      <div className="result-content-card">
        
        {/* Interpretation Tab */}
        {activeTab === 'interpretation' && (
          <section className="result-reading-stack" id="reading-section">
            <div className="result-reading-copy">
              {interpretationText ? (
                <div>
                  {interpretationText}
                </div>
              ) : (
                <p>No interpretation available.</p>
              )}
            </div>

            <div className="result-cta-panel">
              <h3>Need Deeper Insights?</h3>
              <p>
                Consult an Astrologer for a detailed and personalized analysis of this chart.
              </p>
              <button 
                onClick={handleBookConsultation}
                className="btn-primary"
              >
                Book Consultation
              </button>
            </div>
          </section>
        )}

        {/* Charts & Positions Tab */}
        {activeTab === 'charts' && (
          <section className="result-chart-workspace" id="charts-section">
            <div className="chart-mobile-toolbar" aria-label="Chart carousel controls">
              <button type="button" onClick={() => moveSlide(-1)} disabled={activeChartSlide === 0} aria-label="Previous chart panel">
                <ChevronLeft size={18} />
              </button>
              <div className="chart-slide-tabs">
                {mobileChartSlides.map((slide, index) => {
                  const Icon = slide.icon;
                  return (
                    <button
                      key={slide.key}
                      type="button"
                      className={activeChartSlide === index ? 'active' : ''}
                      onClick={() => setActiveChartSlide(index)}
                    >
                      <Icon size={16} />
                      <span>{slide.label}</span>
                    </button>
                  );
                })}
              </div>
              <button type="button" onClick={() => moveSlide(1)} disabled={activeChartSlide === mobileChartSlides.length - 1} aria-label="Next chart panel">
                <ChevronRight size={18} />
              </button>
            </div>

            <div
              className="chart-snap-track"
              style={{ transform: `translateX(-${activeChartSlide * 100}%)` }}
              onTouchStart={(event) => { chartTouchStartX.current = event.touches[0].clientX; }}
              onTouchEnd={handleChartTouchEnd}
            >
              <article className="result-panel result-panel--chart">
                <h3>Prashna Kundli (Lagna)</h3>
              {chart?.signs ? (
                <KundaliChartWrapper data={chart.signs} />
              ) : (
                  <div className="chart-empty-state">
                  Chart Data Unavailable
                </div>
              )}
              </article>

              <article className="result-panel result-panel--positions">
              <div>
                  <h3>Planetary Positions</h3>
                  {planetEntries.length ? (
                    <div className="result-table-wrap">
                      <table className="result-data-table">
                        <thead>
                        <tr>
                            <th>Planet</th>
                            <th>Sign</th>
                            <th>Degree</th>
                        </tr>
                      </thead>
                        <tbody>
                          {planetEntries.map(([planet, details]: [string, any]) => (
                          <tr key={planet}>
                              <td data-label="Planet">{planet}</td>
                              <td data-label="Sign">{details.sign || '-'}</td>
                              <td data-label="Degree">{details.normDegree?.toFixed(2) || '-'} deg</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                    <p className="result-muted">No planetary data available.</p>
                )}
              </div>

              {chart?.ascendant && (
                  <div className="result-stat-box">
                    <h4>Ascendant (Lagna)</h4>
                  <p className="text-lg font-medium">{chart.ascendant.sign} ({chart.ascendant.normDegree?.toFixed(2)}°)</p>
                </div>
              )}
              </article>

              <article className="result-panel result-panel--dashas">
                <h3>Dasha Tools</h3>
                <div className="dasha-mobile-grid">
                  <div>
                    <strong>Vimshottari</strong>
                    <span>Ready for personalized dasha timelines when returned by the engine.</span>
                  </div>
                  <div>
                    <strong>Daily Transit</strong>
                    <span>Designed as a quick mobile section for upcoming transit data.</span>
                  </div>
                  <div>
                    <strong>Yogas</strong>
                    <span>Space reserved for chart combinations and highlights.</span>
                  </div>
                </div>
                <p className="result-muted">No dasha timeline was included in this generated result.</p>
              </article>
            </div>
          </section>
        )}

      </div>
    </main>
  );
};

export default PrashnaResultPage;
