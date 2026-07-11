import React, { useState } from 'react';
import PrashnaForm from '../features/prashna/PrashnaForm';

const HomePage: React.FC = () => {
  const [mode, setMode] = useState<string | null>(null);

  return (
    <>
      {/* Today's Panchang Strip */}
      <div className="panchang-strip" aria-label="Today's Panchang Info">
        <div className="panchang-item">
          <span className="panchang-label">तिथि (Tithi)</span>
          <span className="panchang-val">Shukla Ekadashi</span>
        </div>
        <div className="panchang-divider"></div>
        <div className="panchang-item">
          <span className="panchang-label">नक्षत्र (Nakshatra)</span>
          <span className="panchang-val">Anuradha</span>
        </div>
        <div className="panchang-divider"></div>
        <div className="panchang-item">
          <span className="panchang-label">सूर्योदय/सूर्यास्त (Sunrise/Sunset)</span>
          <span className="panchang-val">05:24 AM / 07:12 PM</span>
        </div>
        <div className="panchang-divider"></div>
        <div className="panchang-item">
          <span className="panchang-label">अभिजीत मुहूर्त (Auspicious Muhurat)</span>
          <span className="panchang-val">11:45 AM - 12:35 PM</span>
        </div>
      </div>

      <section className="entry">
        {/* Celestial Background Elements */}
        <div className="celestial-bg">
          {/* Rotating Sudarshan Chakra Background */}
          <div className="chakra-bg-container">
            <svg className="chakra-svg" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="0.8" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
              <circle cx="50" cy="50" r="6" strokeWidth="1.2" />
              <circle cx="50" cy="50" r="2" fill="currentColor" />
              <circle cx="50" cy="50" r="18" strokeDasharray="2,2" />
              <circle cx="50" cy="50" r="44" strokeWidth="1.2" />
              <circle cx="50" cy="50" r="47" />
              <g strokeWidth="0.6">
                <line x1="50" y1="50" x2="50" y2="6" />
                <line x1="50" y1="50" x2="50" y2="94" />
                <line x1="50" y1="50" x2="6" y2="50" />
                <line x1="50" y1="50" x2="94" y2="50" />
                <line x1="50" y1="50" x2="19" y2="19" />
                <line x1="50" y1="50" x2="81" y2="81" />
                <line x1="50" y1="50" x2="19" y2="81" />
                <line x1="50" y1="50" x2="81" y2="19" />
                <line x1="50" y1="50" x2="61.4" y2="8.4" />
                <line x1="50" y1="50" x2="38.6" y2="91.6" />
                <line x1="50" y1="50" x2="72.1" y2="15.6" />
                <line x1="50" y1="50" x2="27.9" y2="84.4" />
                <line x1="50" y1="50" x2="84.4" y2="27.9" />
                <line x1="50" y1="50" x2="15.6" y2="72.1" />
                <line x1="50" y1="50" x2="91.6" y2="38.6" />
                <line x1="50" y1="50" x2="8.4" y2="61.4" />
                <line x1="50" y1="50" x2="61.4" y2="91.6" />
                <line x1="50" y1="50" x2="38.6" y2="8.4" />
                <line x1="50" y1="50" x2="72.1" y2="84.4" />
                <line x1="50" y1="50" x2="27.9" y2="15.6" />
                <line x1="50" y1="50" x2="84.4" y2="72.1" />
                <line x1="50" y1="50" x2="15.6" y2="27.9" />
                <line x1="50" y1="50" x2="91.6" y2="61.4" />
                <line x1="50" y1="50" x2="8.4" y2="38.6" />
              </g>
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(0 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(15 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(30 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(45 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(60 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(75 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(90 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(105 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(120 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(135 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(150 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(165 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(180 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(195 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(210 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(225 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(240 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(255 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(270 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(285 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(300 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(315 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(330 50 50)" />
              <path d="M50 2 L52 5 L48 5 Z" fill="currentColor" transform="rotate(345 50 50)" />
            </svg>
          </div>
          <div className="planet planet-1"></div>
          <div className="planet planet-2"></div>
          <div className="constellation-overlay"></div>
        </div>

        <div className="hero-container">
          <div className="hero-center-content">
            <span className="devanagari-accent">ज्योतिषं नेत्रं शास्त्रस्य</span>
            <span className={`hero-eyebrow-mark ${mode ? 'hidden' : ''}`}>✨ Luxury Spiritual Wellness</span>
            <h1 className="hero-main-title">
              Decode the Blueprint Written in the Stars.
            </h1>
            <p className="hero-lede">
              Ancient Wisdom meets Modern Precision. Generate highly accurate
              birth charts and gain profound insights into your life's journey.
            </p>

            <div className={`hero-cta-group ${mode ? 'hidden' : ''}`} id="mode-panel">
              <button type="button" className="mode-card" data-mode="lagna" onClick={() => setMode('lagna')}>
                <div className="mode-icon-box">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--saffron-gold)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                </div>
                <div className="mode-card-text">
                  <h3>Lagna Kundli</h3>
                  <p>Comprehensive life reading</p>
                </div>
              </button>

              <button type="button" className="mode-card" data-mode="prashna" onClick={() => setMode('prashna')}>
                <div className="mode-icon-box">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--saffron-gold)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                </div>
                <div className="mode-card-text">
                  <h3>Prashna Kundli</h3>
                  <p>Immediate cosmic guidance</p>
                </div>
              </button>
            </div>

            {!mode && (
              <div className="hero-stat-row">
                <div><strong>Expert</strong><span>Astrologer</span></div>
              </div>
            )}

            {mode === 'lagna' && (
              <form className="form" style={{ marginTop: '2rem', padding: '1rem', background: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--line-gold)', position: 'relative', zIndex: 20 }}>
                <div className="form-head" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', alignItems: 'center' }}>
                  <div>
                    <p className="eyebrow">Selected mode</p>
                    <h2 style={{margin: 0, color: 'var(--ink-light)'}}>Lagna Kundli</h2>
                  </div>
                  <button type="button" onClick={() => setMode(null)} style={{ color: 'var(--saffron-gold)', background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 600 }}>Change Mode</button>
                </div>
                <p style={{ color: 'var(--ink-dim)' }}>Lagna form is not yet migrated to React.</p>
              </form>
            )}

            {mode === 'prashna' && (
              <div className="form" style={{ marginTop: '2rem', position: 'relative', zIndex: 20 }}>
                <div className="form-head" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', alignItems: 'center' }}>
                  <div>
                    <p className="eyebrow" style={{ margin: 0, opacity: 0.8 }}>Selected mode</p>
                    <h2 style={{margin: 0, color: 'var(--ink-light)'}}>Prashna Kundli</h2>
                  </div>
                  <button type="button" onClick={() => setMode(null)} style={{ color: 'var(--saffron-gold)', background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 600 }}>Change Mode</button>
                </div>
                <PrashnaForm />
              </div>
            )}
          </div>
        </div>
      </section>
    </>
  );
};

export default HomePage;
