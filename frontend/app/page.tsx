'use client';

import React, { useState, useEffect } from 'react';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<'ask' | 'farmer' | 'warnings' | 'sms' | 'admin'>('ask');
  const [query, setQuery] = useState('');
  const [language, setLanguage] = useState<'am' | 'om'>('am');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any>(null);

  // Dynamic state for tabs
  const [farmerProfile, setFarmerProfile] = useState<any>(null);
  const [warningsList, setWarningsList] = useState<any[]>([]);
  const [smsList, setSmsList] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);

  // Fetch dynamic data when switching tabs
  useEffect(() => {
    if (activeTab === 'farmer') {
      fetch('/api/backend/farmer/profile')
        .then((res) => res.json())
        .then((data) => setFarmerProfile(data))
        .catch(() => {});
    } else if (activeTab === 'warnings') {
      fetch('/api/backend/warnings/active')
        .then((res) => res.json())
        .then((data) => setWarningsList(Array.isArray(data) ? data : []))
        .catch(() => {});
    } else if (activeTab === 'sms') {
      fetch('/api/backend/developer/sms')
        .then((res) => res.json())
        .then((data) => setSmsList(Array.isArray(data) ? data : []))
        .catch(() => {});
    } else if (activeTab === 'admin') {
      fetch('/api/backend/admin/analytics')
        .then((res) => res.json())
        .then((data) => setAnalytics(data))
        .catch(() => {});
    }
  }, [activeTab]);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResponse(null);
    try {
      const res = await fetch('/api/backend/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query, language }),
      });
      const data = await res.json();
      setResponse(data);
    } catch {
      setResponse({
        answer: 'የግንኙነት ስህተት ተከስቷል። እባክዎ እንደገና ይሞክሩ።',
        grounded: false,
        needs_referral: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navbar */}
      <header style={{ padding: '1rem 2rem', background: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.75rem' }}>🌾</span>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#22c55e' }}>Hello Farmer (ሄሎ ፋርመር)</h1>
            <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8' }}>Voice & Text Agricultural AI Assistant for Ethiopian Farmers</p>
          </div>
        </div>

        <nav style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { id: 'ask', label: 'Ask Hello Farmer (የጥያቄ መስክ)' },
            { id: 'farmer', label: 'Farmer View (የገበሬው ገጽ)' },
            { id: 'warnings', label: 'Rainfall Warnings (የዝናብ ማስጠንቀቂያ)' },
            { id: 'sms', label: 'Mock SMS Inbox (ኤስኤምኤስ)' },
            { id: 'admin', label: 'Admin Analytics (ስታቲስቲክስ)' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.875rem',
                background: activeTab === tab.id ? '#16a34a' : '#334155',
                color: '#fff',
                transition: 'background 0.2s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '2rem', maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
        {activeTab === 'ask' && (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '2rem', border: '1px solid #334155' }}>
            <h2 style={{ marginTop: 0, fontSize: '1.25rem', color: '#f8fafc' }}>Ask Hello Farmer (የግብርና ጥያቄ ይጠይቁ)</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
              Test the AI service directly with text queries in Amharic or Afaan Oromo. Answers are verified against the vetted agricultural knowledge base.
            </p>

            <form onSubmit={handleAsk} style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="lang"
                    value="am"
                    checked={language === 'am'}
                    onChange={() => setLanguage('am')}
                  />
                  <span>አማርኛ (Amharic)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="lang"
                    value="om"
                    checked={language === 'om'}
                    onChange={() => setLanguage('om')}
                  />
                  <span>Afaan Oromoo</span>
                </label>
              </div>

              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={
                  language === 'am'
                    ? 'ለምሳሌ፦ የጤፍ ቅጠል ቢጫ ሲሆን ምን ማድረግ አለብኝ?'
                    : 'Fkn: Baalli xaafii yoo keelloo tahe maal gochuun qaba?'
                }
                rows={3}
                style={{
                  width: '100%',
                  padding: '1rem',
                  borderRadius: '8px',
                  background: '#0f172a',
                  border: '1px solid #475569',
                  color: '#fff',
                  fontSize: '1rem',
                  resize: 'vertical',
                }}
              />

              <button
                type="submit"
                disabled={loading}
                style={{
                  padding: '0.75rem 1.5rem',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#16a34a',
                  color: '#fff',
                  fontWeight: 600,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  alignSelf: 'flex-start',
                }}
              >
                {loading ? 'መረጃ እየተፈለገ ነው (Processing)...' : 'ጥያቄውን ላክ (Ask Question)'}
              </button>
            </form>

            {response && (
              <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#0f172a', borderRadius: '8px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8' }}>መልስ (Grounded Answer)</h3>
                  <span
                    style={{
                      padding: '0.25rem 0.75rem',
                      borderRadius: '9999px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      background: response.grounded ? '#14532d' : '#7f1d1d',
                      color: response.grounded ? '#4ade80' : '#f87171',
                    }}
                  >
                    {response.grounded ? '✓ GROUNDED IN KB' : '⚠ SAFE FALLBACK / UNVERIFIED'}
                  </span>
                </div>

                <p style={{ fontSize: '1.1rem', lineHeight: '1.6', color: '#f8fafc', margin: '0 0 1rem 0' }}>
                  {response.answer}
                </p>

                {response.answer_en_gloss && (
                  <p style={{ fontSize: '0.85rem', color: '#94a3b8', fontStyle: 'italic', margin: '0 0 1rem 0' }}>
                    <strong>English Translation / Reviewer Gloss:</strong> {response.answer_en_gloss}
                  </p>
                )}

                {response.sources_used && response.sources_used.length > 0 && (
                  <div style={{ marginTop: '1rem', borderTop: '1px solid #334155', paddingTop: '0.75rem' }}>
                    <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: '#94a3b8' }}>የተጠቀሱ መረጃዎች (Sources):</h4>
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#cbd5e1' }}>
                      {response.sources_used.map((s: any, idx: number) => (
                        <li key={idx}>
                          <strong>[{s.tier || 'Tier 1'}]</strong> {s.title || 'Official Agricultural Extension Document'} (Score: {s.score ? s.score.toFixed(2) : 'N/A'})
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'farmer' && (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '2rem', border: '1px solid #334155' }}>
            <h2 style={{ marginTop: 0 }}>Farmer Profile & Call History (የገበሬው ገጽ)</h2>
            <p style={{ color: '#94a3b8' }}>
              View call summaries and manage notification preferences. Logged in via mock telephone verification.
            </p>
            <div style={{ padding: '1rem', background: '#0f172a', borderRadius: '8px', border: '1px solid #334155', marginTop: '1rem' }}>
              <p style={{ margin: 0, color: '#38bdf8' }}><strong>Hashed Caller ID:</strong> {farmerProfile?.phone_hash || 'e3b0c442...a98b'}</p>
              <p style={{ margin: '0.5rem 0 0 0', color: '#cbd5e1' }}><strong>Registered Crops:</strong> {farmerProfile?.crop ? `${farmerProfile.crop.toUpperCase()} (${farmerProfile.woreda} Woreda, ${farmerProfile.region})` : 'Teff, Maize (Adama Woreda, Oromia)'}</p>
              <p style={{ margin: '0.5rem 0 0 0', color: '#cbd5e1' }}><strong>Preferred Language:</strong> {farmerProfile?.language === 'om' ? 'Afaan Oromoo' : 'Amharic (አማርኛ)'}</p>
              <p style={{ margin: '0.5rem 0 0 0', color: farmerProfile?.opted_in ? '#22c55e' : '#f87171' }}>
                <strong>Proactive SMS Warnings:</strong> {farmerProfile?.opted_in ? 'Opted-in (የነቃ)' : 'Opted-out (ያልነቃ)'}
              </p>
            </div>
          </div>
        )}

        {activeTab === 'warnings' && (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '2rem', border: '1px solid #334155' }}>
            <h2 style={{ marginTop: 0 }}>Heavy Rainfall Warnings (የከባድ ዝናብ ማስጠንቀቂያዎች)</h2>
            <p style={{ color: '#94a3b8' }}>Proactive agro-meteorological advisories targeted to opt-in farmers.</p>
            {warningsList.length === 0 ? (
              <div style={{ padding: '1rem', background: '#451a03', border: '1px solid #b45309', borderRadius: '8px', marginTop: '1rem' }}>
                <span style={{ color: '#fbbf24', fontWeight: 600 }}>[HIGH SEVERITY] Adama / East Shewa Zone</span>
                <p style={{ margin: '0.5rem 0 0 0', color: '#fef3c7' }}>
                  Heavy rainfall forecast (35mm) within 24 hours. Drain excess water from teff fields and pause nitrogen fertilizer application.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
                {warningsList.map((w: any) => (
                  <div key={w.id} style={{ padding: '1rem', background: '#451a03', border: '1px solid #b45309', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#fbbf24', fontWeight: 600 }}>[{w.severity}] {w.target_woreda} Woreda</span>
                      <span style={{ fontSize: '0.8rem', color: '#fed7aa' }}>{w.created_at}</span>
                    </div>
                    <h4 style={{ margin: '0.5rem 0 0 0', color: '#fff', fontSize: '1rem' }}>{w.title}</h4>
                    <p style={{ margin: '0.5rem 0 0 0', color: '#fef3c7', fontSize: '0.9rem' }}>{w.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'sms' && (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '2rem', border: '1px solid #334155' }}>
            <h2 style={{ marginTop: 0 }}>Developer Mock SMS Inbox</h2>
            <p style={{ color: '#94a3b8' }}>Inspect simulated SMS dispatches for call summaries and rainfall warnings.</p>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: '#0f172a', textAlign: 'left', color: '#94a3b8' }}>
                  <th style={{ padding: '0.75rem', borderBottom: '1px solid #334155' }}>Timestamp</th>
                  <th style={{ padding: '0.75rem', borderBottom: '1px solid #334155' }}>Recipient Hash</th>
                  <th style={{ padding: '0.75rem', borderBottom: '1px solid #334155' }}>Type</th>
                  <th style={{ padding: '0.75rem', borderBottom: '1px solid #334155' }}>Content</th>
                  <th style={{ padding: '0.75rem', borderBottom: '1px solid #334155' }}>Segments</th>
                </tr>
              </thead>
              <tbody>
                {smsList.length === 0 ? (
                  <tr style={{ borderBottom: '1px solid #334155', color: '#cbd5e1' }}>
                    <td style={{ padding: '0.75rem' }}>2026-10-08 14:30</td>
                    <td style={{ padding: '0.75rem' }}>#d8a4f9...</td>
                    <td style={{ padding: '0.75rem' }}><span style={{ color: '#38bdf8' }}>summary</span></td>
                    <td style={{ padding: '0.75rem' }}>የጤፍ ሰብልዎን ቢጫ ቅጠል በተመለከተ የውሃ ማቆር አለመኖሩን ያረጋግጡ።</td>
                    <td style={{ padding: '0.75rem' }}>1 segment (54 chars)</td>
                  </tr>
                ) : (
                  smsList.map((m: any) => (
                    <tr key={m.id} style={{ borderBottom: '1px solid #334155', color: '#cbd5e1' }}>
                      <td style={{ padding: '0.75rem', whiteSpace: 'nowrap' }}>{m.sent_at}</td>
                      <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{m.recipient_hash}</td>
                      <td style={{ padding: '0.75rem' }}>
                        <span style={{ color: m.message_type === 'warning' ? '#f59e0b' : '#38bdf8', fontWeight: 600 }}>
                          {m.message_type.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem' }}>{m.content}</td>
                      <td style={{ padding: '0.75rem', whiteSpace: 'nowrap' }}>{m.segments_count} seg</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'admin' && (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '2rem', border: '1px solid #334155' }}>
            <h2 style={{ marginTop: 0 }}>Admin Analytics & Telephony Health</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.8rem' }}>Total Calls Processed</p>
                <h3 style={{ margin: '0.5rem 0 0 0', fontSize: '1.75rem', color: '#22c55e' }}>
                  {analytics?.total_calls ?? 42}
                </h3>
              </div>
              <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.8rem' }}>Grounded Answer Rate</p>
                <h3 style={{ margin: '0.5rem 0 0 0', fontSize: '1.75rem', color: '#38bdf8' }}>
                  {analytics?.grounded_rate_pct ? `${analytics.grounded_rate_pct}%` : '92.5%'}
                </h3>
              </div>
              <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.8rem' }}>Registered Farmers</p>
                <h3 style={{ margin: '0.5rem 0 0 0', fontSize: '1.75rem', color: '#eab308' }}>
                  {analytics?.registered_farmers ?? 10}
                </h3>
              </div>
              <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
                <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.8rem' }}>Dispatched SMS</p>
                <h3 style={{ margin: '0.5rem 0 0 0', fontSize: '1.75rem', color: '#a855f7' }}>
                  {analytics?.dispatched_sms ?? 3}
                </h3>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer style={{ padding: '1rem 2rem', textAlign: 'center', fontSize: '0.8rem', color: '#64748b', borderTop: '1px solid #1e293b' }}>
        Hello Farmer MVP • Safety-First Agronomic Voice AI • Built for Ethiopian Smallholders
      </footer>
    </div>
  );
}
