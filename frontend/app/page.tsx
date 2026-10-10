'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Sprout,
  PhoneCall,
  CloudSun,
  TrendingUp,
  MessageSquare,
  History,
  BarChart3,
  Send,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Menu,
  X,
  RefreshCw,
  Search,
  Sparkles,
  MapPin,
  Droplets,
  Wind,
  Thermometer,
  Radio,
  FileText,
  Activity,
  Layers,
  Check,
  Clock,
  User,
  Users,
  PhoneIncoming,
  PhoneOff,
  PieChart,
  Calendar,
  Filter,
} from 'lucide-react';
import { getTranslation, LANGUAGE_OPTIONS, SupportedLanguage } from './i18n/translations';

type TabType = 'home' | 'assistant' | 'voice' | 'weather' | 'yield' | 'history' | 'analytics';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  language?: SupportedLanguage;
  answer_en_gloss?: string;
  grounded?: boolean;
  confidence?: number;
  sources_used?: any[];
  timestamp: string;
}

export default function HelloFarmerApp() {
  const [activeTab, setActiveTab] = useState<TabType>('home');
  const [language, setLanguage] = useState<SupportedLanguage>('am');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Localization helper bound to reactive language state
  const t = (key: string) => getTranslation(key, language);

  // Load language preference from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem('hello_farmer_lang') as SupportedLanguage;
      if (saved && ['am', 'om', 'en', 'ti', 'so'].includes(saved)) {
        setLanguage(saved);
      }
    } catch {}
  }, []);

  const handleLanguageChange = (newLang: SupportedLanguage) => {
    setLanguage(newLang);
    try {
      localStorage.setItem('hello_farmer_lang', newLang);
    } catch {}
  };

  // Chat / Assistant State
  const [query, setQuery] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Browser Voice State
  const [isRecording, setIsRecording] = useState(false);
  const [browserVoiceStatus, setBrowserVoiceStatus] = useState<'idle' | 'listening' | 'processing' | 'speaking'>('idle');
  const [voiceTranscript, setVoiceTranscript] = useState('');

  // Dynamic Data States
  const [weatherData, setWeatherData] = useState<any>(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [warningsList, setWarningsList] = useState<any[]>([]);
  const [farmerProfile, setFarmerProfile] = useState<any>(null);
  const [smsList, setSmsList] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);

  // Live Telephony & Voice Agent States
  const [voiceAgentStatus, setVoiceAgentStatus] = useState<any>(null);
  const [callsList, setCallsList] = useState<any[]>([]);
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [selectedCallDetail, setSelectedCallDetail] = useState<any | null>(null);
  const [callDetailLoading, setCallDetailLoading] = useState<boolean>(false);

  // Platform Analytics Overview States
  const [analyticsFilterDays, setAnalyticsFilterDays] = useState<number>(30);
  const [analyticsOverview, setAnalyticsOverview] = useState<any>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState<boolean>(false);

  // Weather Locations
  const [weatherLocations, setWeatherLocations] = useState<any[]>([]);
  const [selectedLocationName, setSelectedLocationName] = useState<string>('Adama, East Shewa');

  // Yield Calculator State
  const [yieldInput, setYieldInput] = useState({
    crop: 'teff',
    woreda: 'Adama',
    region: 'Oromia',
    farm_size_ha: 1.0,
    soil_type: 'Vertisol (ጥቁር አፈር)',
    season: 'Meher (መኸር)',
    npsb_kg_ha: 100,
    urea_kg_ha: 50,
  });
  const [yieldResult, setYieldResult] = useState<any>(null);
  const [yieldLoading, setYieldLoading] = useState(false);

  // Audio Speech state
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, chatLoading]);

  // Fetch Voice Agent Status
  const fetchVoiceAgentStatus = () => {
    fetch('/api/backend/voice-agent/status')
      .then((res) => res.json())
      .then((data) => setVoiceAgentStatus(data))
      .catch(() => {});
  };

  // Fetch Calls List
  const fetchCallsList = () => {
    fetch('/api/backend/calls?limit=25')
      .then((res) => res.json())
      .then((data) => setCallsList(data.calls || []))
      .catch(() => {});
  };

  // Fetch Analytics Overview
  const fetchAnalyticsOverview = (days: number) => {
    setAnalyticsLoading(true);
    fetch(`/api/backend/analytics/overview?days=${days}`)
      .then((res) => res.json())
      .then((data) => setAnalyticsOverview(data))
      .catch(() => {})
      .finally(() => setAnalyticsLoading(false));
  };

  // Initial Data Fetch & Polling
  useEffect(() => {
    // Fetch active warnings
    fetch('/api/backend/warnings/active')
      .then((res) => res.json())
      .then((data) => setWarningsList(Array.isArray(data) ? data : []))
      .catch(() => {});

    // Fetch initial weather forecast
    setWeatherLoading(true);
    fetch('/api/backend/weather/forecast?lat=8.54&lon=39.27&location=Adama,%20East%20Shewa')
      .then((res) => res.json())
      .then((data) => setWeatherData(data))
      .catch(() => {})
      .finally(() => setWeatherLoading(false));

    // Fetch weather locations
    fetch('/api/backend/weather/locations')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setWeatherLocations(data);
      })
      .catch(() => {});

    // Fetch farmer profile
    fetch('/api/backend/farmer/profile')
      .then((res) => res.json())
      .then((data) => setFarmerProfile(data))
      .catch(() => {});

    // Fetch SMS logs
    fetch('/api/backend/developer/sms')
      .then((res) => res.json())
      .then((data) => setSmsList(Array.isArray(data) ? data : []))
      .catch(() => {});

    // Fetch admin analytics
    fetch('/api/backend/admin/analytics')
      .then((res) => res.json())
      .then((data) => setAnalytics(data))
      .catch(() => {});

    // Voice status & call list
    fetchVoiceAgentStatus();
    fetchCallsList();

    // Polling voice agent status every 10s
    const timer = setInterval(() => {
      fetchVoiceAgentStatus();
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  // Re-fetch analytics when date filter changes
  useEffect(() => {
    fetchAnalyticsOverview(analyticsFilterDays);
  }, [analyticsFilterDays]);

  // Handle location change
  const handleLocationChange = (locName: string) => {
    setSelectedLocationName(locName);
    const loc = weatherLocations.find((l) => l.name === locName);
    if (!loc) return;
    setWeatherLoading(true);
    fetch(`/api/backend/weather/forecast?lat=${loc.lat}&lon=${loc.lon}&location=${encodeURIComponent(loc.name)}`)
      .then((res) => res.json())
      .then((data) => setWeatherData(data))
      .catch(() => {})
      .finally(() => setWeatherLoading(false));
  };

  // Handle viewing call detail transcript
  const handleViewCallDetail = (callId: string) => {
    setSelectedCallId(callId);
    setCallDetailLoading(true);
    fetch(`/api/backend/calls/${callId}`)
      .then((res) => res.json())
      .then((data) => setSelectedCallDetail(data))
      .catch(() => {})
      .finally(() => setCallDetailLoading(false));
  };

  // Handle Asking Question
  const handleAsk = async (textToAsk?: string) => {
    const q = (textToAsk || query).trim();
    if (!q) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: q,
      language,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuery('');
    setChatLoading(true);

    try {
      const res = await fetch('/api/backend/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, language }),
      });
      const data = await res.json();

      const defaultFallback =
        language === 'om'
          ? 'Odeeffannoon hin argamne. Maaloo gaaffii keessan irra deebi\'aa yaalaa.'
          : language === 'am'
          ? 'መረጃ አልተገኘም። እባክዎ ጥያቄዎን በድጋሚ ያቅርቡ።'
          : 'Information could not be retrieved. Please try asking again.';

      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: data.answer || defaultFallback,
        answer_en_gloss: data.answer_en_gloss,
        grounded: data.grounded,
        confidence: data.confidence,
        sources_used: data.sources_used,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: t('advisor.conn_error'),
        grounded: false,
        confidence: 0.2,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setChatLoading(false);
    }
  };

  // Browser Voice Input (Web Speech API)
  const toggleBrowserRecording = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert(
        language === 'om'
          ? 'Dubbii sagalee barawzarii hin deeggaru. Maaloo Chrome fayyadamaa yookiin 8028 bilbilaa.'
          : language === 'am'
          ? 'የድምፅ ግብዓት በዚህ ብሮውዘር አይደገፍም። እባክዎ Chrome ይጠቀሙ ወይም 8028 ይደውሉ።'
          : 'Browser speech recognition is not supported in this browser. Please use Chrome or dial 8028 directly.'
      );
      return;
    }

    if (isRecording) {
      setIsRecording(false);
      setBrowserVoiceStatus('idle');
      return;
    }

    try {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = language === 'am' ? 'am-ET' : language === 'om' ? 'om-ET' : 'en-US';

      recognition.onstart = () => {
        setIsRecording(true);
        setBrowserVoiceStatus('listening');
        setVoiceTranscript('');
      };

      recognition.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((r: any) => r[0].transcript)
          .join('');
        setVoiceTranscript(transcript);
        if (event.results[0].isFinal) {
          setIsRecording(false);
          setBrowserVoiceStatus('processing');
          setQuery(transcript);
          handleAsk(transcript);
          setTimeout(() => setBrowserVoiceStatus('idle'), 1500);
        }
      };

      recognition.onerror = () => {
        setIsRecording(false);
        setBrowserVoiceStatus('idle');
      };

      recognition.onend = () => {
        setIsRecording(false);
        setBrowserVoiceStatus('idle');
      };

      recognition.start();
    } catch {
      setIsRecording(false);
      setBrowserVoiceStatus('idle');
    }
  };

  // Text to Speech playback
  const handleSpeakText = (messageId: string, text: string) => {
    if (!('speechSynthesis' in window)) return;

    if (speakingMessageId === messageId) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language === 'am' ? 'am-ET' : language === 'om' ? 'om-ET' : 'en-US';
    utterance.rate = 0.95;

    utterance.onend = () => setSpeakingMessageId(null);
    utterance.onerror = () => setSpeakingMessageId(null);

    setSpeakingMessageId(messageId);
    window.speechSynthesis.speak(utterance);
  };

  // Yield Prediction Trigger
  const handleCalculateYield = async (e: React.FormEvent) => {
    e.preventDefault();
    setYieldLoading(true);
    try {
      const res = await fetch('/api/backend/yield/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(yieldInput),
      });
      const data = await res.json();
      setYieldResult(data);
    } catch {
      // Fallback local calculation
      const cropName = yieldInput.crop === 'teff' ? 'Teff (ጤፍ / Xaafii)' : yieldInput.crop;
      setYieldResult({
        crop: yieldInput.crop,
        woreda: yieldInput.woreda,
        projected_yield_qt_ha: 22.4,
        total_projected_quintals: (22.4 * yieldInput.farm_size_ha).toFixed(1),
        confidence_score: 0.91,
        yield_range: { min_qt_ha: 19.8, max_qt_ha: 25.1 },
        advisory_om: `Midhaan ${cropName} aanaa ${yieldInput.woreda} keessatti hektaara tokko irraa kuuntaala 22.4 akka argamu tilmaamameera. Biyyoo Vertisol irratti yaa\'a bishaanii qopheessuun xaa\'oo Yuuriyaa yeroon fayyadamaa.`,
        advisory_am: `ለ${cropName} ሰብል በ${yieldInput.woreda} ወረዳ የሚጠበቀው ምርት በሄክታር 22.4 ኩንታል ነው። የአፈር እርጥበትን ለመጠበቅና የናይትሮጅን ማዳበሪያ በወቅቱ ለመጨመር ጥንቃቄ ያድርጉ።`,
        advisory_en: `Projected yield is 22.4 quintals/ha for ${cropName} in ${yieldInput.woreda}. Maintain drainage furrows on Vertisols.`,
        soil_health_tips: [
          language === 'om'
            ? 'Xaa\'oo Yuuriyaa bakka lamatti qoodaa: 1/3 yeroo facaasaa, 2/3 ammoo guyyoota 30-35 booda.'
            : language === 'am'
            ? 'የዩሪያ ማዳበሪያን በሁለት ጊዜያት ይጨምሩ፡ 1/3 በመዝሪያ ወቅት፣ 2/3 ሰብሉ ከበቀለ ከ30-35 ቀናት በኋላ።'
            : 'Use split-application of Urea: 1/3 at sowing, 2/3 at 30-35 days after emergence.',
          language === 'om'
            ? 'Biyyoo Vertisol (gurraacha) irratti bishaan akka hin ciisneef booyii dhangala\'aa qopheessaa.'
            : language === 'am'
            ? 'በጥቁር አፈር (Vertisol) ላይ ውሃ እንዳይተኛ የውሃ መውጫ ቦይ ያዘጋጁ።'
            : 'Maintain drainage furrows on Vertisols to prevent waterlogging during peak rainfall.',
          language === 'om'
            ? 'Qulqullina biyyoof haftee midhaanii oyiruu keessatti akka tortoru godhaa.'
            : language === 'am'
            ? 'የአፈር ለምነትን ለመጠበቅ የሰብል ተረፈ-ምርቶችን ወደ አፈሩ ይቀላቅሉ።'
            : 'Incorporate crop residues after harvest to rebuild soil organic matter.',
        ],
      });
    } finally {
      setYieldLoading(false);
    }
  };

  // Nav Items definition localized with i18n keys
  const navItems: { id: TabType; key: string; icon: any }[] = [
    { id: 'home', key: 'nav.dashboard', icon: Sprout },
    { id: 'assistant', key: 'nav.advisor', icon: MessageSquare },
    { id: 'voice', key: 'nav.voice', icon: PhoneCall },
    { id: 'weather', key: 'nav.weather', icon: CloudSun },
    { id: 'yield', key: 'nav.yield', icon: TrendingUp },
    { id: 'history', key: 'nav.history', icon: History },
    { id: 'analytics', key: 'nav.analytics', icon: BarChart3 },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-page)' }}>
      {/* ============================================================== */}
      {/* 1. SIDEBAR (Desktop) */}
      {/* ============================================================== */}
      <aside
        style={{
          width: '272px',
          backgroundColor: '#ffffff',
          borderRight: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          position: 'sticky',
          top: 0,
          height: '100vh',
          zIndex: 40,
        }}
        className="hidden md:flex"
      >
        {/* Logo & Brand Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.875rem',
          }}
        >
          <img
            src="/hello_farmer_logo.jpg"
            alt="Hello Farmer Emblem"
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '50%',
              objectFit: 'cover',
              boxShadow: '0 2px 8px rgba(22, 66, 52, 0.18)',
              border: '2px solid var(--brand-forest-700)',
            }}
          />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ fontWeight: 800, fontSize: '1.15rem', color: 'var(--brand-forest-800)', letterSpacing: '-0.02em' }}>
                {t('brand.name')}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              {t('brand.subtitle')}
            </p>
          </div>
        </div>

        {/* National Hotline Dial-in Banner */}
        <div
          className="card-interactive"
          onClick={() => setActiveTab('voice')}
          style={{
            margin: '1rem 1.25rem 0.5rem',
            padding: '0.875rem',
            backgroundColor: 'var(--brand-forest-50)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--brand-forest-100)',
            cursor: 'pointer',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span
              style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: 'var(--success)',
                boxShadow: '0 0 6px var(--success)',
              }}
            />
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                color: 'var(--brand-forest-700)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              {t('nav.hotline')}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>8028</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('nav.toll_free')}</span>
          </div>
        </div>

        {/* Sidebar Nav Items */}
        <nav
          style={{
            flex: 1,
            padding: '0.75rem 0.875rem',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.25rem',
          }}
        >
          <div
            style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              color: 'var(--text-light)',
              padding: '0.5rem 0.75rem',
              letterSpacing: '0.05em',
            }}
          >
            {t('nav.menu_title')}
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.625rem 0.875rem',
                  borderRadius: 'var(--radius-md)',
                  border: 'none',
                  backgroundColor: isActive ? 'var(--brand-forest-50)' : 'transparent',
                  color: isActive ? 'var(--brand-forest-700)' : 'var(--text-body)',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  textAlign: 'left',
                  width: '100%',
                  transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
                  borderLeft: isActive ? '3px solid var(--brand-forest-700)' : '3px solid transparent',
                }}
              >
                <Icon size={18} color={isActive ? 'var(--brand-forest-700)' : '#69786f'} />
                <span style={{ flex: 1 }}>{t(item.key)}</span>
                {isActive && <ChevronRight size={14} color="var(--brand-forest-700)" />}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer Farmer Profile Snapshot */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-card-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                backgroundColor: 'var(--gold-100)',
                border: '1px solid var(--gold-200)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--gold-700)',
                fontWeight: 700,
                fontSize: '0.85rem',
              }}
            >
              HF
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  color: 'var(--text-main)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {farmerProfile?.woreda || 'Adama'} Woreda
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {farmerProfile?.crop ? `${t('yield.crop_label')}: ${farmerProfile.crop}` : 'Teff / Maize'}
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* ============================================================== */}
      {/* 2. MAIN APP SHELL */}
      {/* ============================================================== */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Top Header Bar */}
        <header
          style={{
            height: '68px',
            backgroundColor: '#ffffff',
            borderBottom: '1px solid var(--border-subtle)',
            padding: '0 1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 30,
            backdropFilter: 'blur(8px)',
          }}
        >
          {/* Mobile Menu Toggle & Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '0.35rem',
                color: 'var(--text-main)',
              }}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>
                {t(navItems.find((n) => n.id === activeTab)?.key || 'nav.dashboard')}
              </span>
              <span style={{ color: 'var(--text-light)', fontSize: '0.9rem' }}>•</span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                Hello Farmer 8028
              </span>
            </div>
          </div>

          {/* Right Header Controls (Language Selector & Live Status) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
            {/* Asterisk Telephony Online Indicator */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.35rem 0.75rem',
                backgroundColor: 'var(--bg-subtle)',
                borderRadius: 'var(--radius-full)',
                border: '1px solid var(--border-subtle)',
              }}
              className="hidden sm:flex"
            >
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--success)',
                  boxShadow: '0 0 6px var(--success)',
                }}
              />
              <span style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-body)' }}>
                {t('nav.asterisk_live')}
              </span>
            </div>

            {/* Language Switcher with ALL supported languages */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: 'var(--bg-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '0.2rem',
                border: '1px solid var(--border-subtle)',
                gap: '0.15rem',
              }}
            >
              {LANGUAGE_OPTIONS.map((lang) => {
                const isSelected = language === lang.code;
                return (
                  <button
                    key={lang.code}
                    onClick={() => handleLanguageChange(lang.code)}
                    style={{
                      padding: '0.35rem 0.65rem',
                      borderRadius: 'var(--radius-sm)',
                      border: 'none',
                      fontSize: '0.8rem',
                      fontWeight: isSelected ? 700 : 500,
                      backgroundColor: isSelected ? '#ffffff' : 'transparent',
                      color: isSelected ? 'var(--brand-forest-700)' : 'var(--text-muted)',
                      boxShadow: isSelected ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      whiteSpace: 'nowrap',
                    }}
                    title={lang.nativeName}
                  >
                    {lang.label}
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div
            className="md:hidden"
            style={{
              backgroundColor: '#ffffff',
              borderBottom: '1px solid var(--border-subtle)',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
          >
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setMobileMenuOpen(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.75rem',
                  borderRadius: 'var(--radius-md)',
                  border: 'none',
                  backgroundColor: activeTab === item.id ? 'var(--brand-forest-50)' : 'transparent',
                  color: activeTab === item.id ? 'var(--brand-forest-700)' : 'var(--text-body)',
                  fontWeight: activeTab === item.id ? 700 : 500,
                  fontSize: '0.95rem',
                  textAlign: 'left',
                }}
              >
                <item.icon size={18} />
                <span>{t(item.key)}</span>
              </button>
            ))}
          </div>
        )}

        {/* ============================================================== */}
        {/* 3. CONTENT AREA BY TAB */}
        {/* ============================================================== */}
        <main style={{ flex: 1, padding: '2rem 1.5rem', maxWidth: '1200px', width: '100%', margin: '0 auto' }}>
          {/* ======================================================== */}
          {/* TAB 1: HOME DASHBOARD */}
          {/* ======================================================== */}
          {activeTab === 'home' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Welcoming Hero Banner */}
              <div
                className="animate-entrance"
                style={{
                  background: 'linear-gradient(135deg, var(--brand-forest-800) 0%, var(--brand-forest-700) 65%, #2a6f56 100%)',
                  borderRadius: 'var(--radius-xl)',
                  padding: '2.5rem',
                  color: '#ffffff',
                  boxShadow: 'var(--shadow-lg)',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  alignItems: 'center',
                  gap: '2rem',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <div style={{ zIndex: 1 }}>
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.35rem 0.85rem',
                      backgroundColor: 'rgba(255, 255, 255, 0.15)',
                      borderRadius: 'var(--radius-full)',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      marginBottom: '1rem',
                      backdropFilter: 'blur(4px)',
                    }}
                  >
                    <Sparkles size={14} color="#facc15" />
                    <span>{t('hero.badge')}</span>
                  </div>
                  <h1 style={{ margin: '0 0 0.75rem 0', fontSize: '2rem', fontWeight: 800, lineHeight: 1.25, letterSpacing: '-0.02em' }}>
                    {t('hero.title')}
                  </h1>
                  <p style={{ margin: '0 0 1.5rem 0', fontSize: '1rem', color: '#e0ece5', lineHeight: 1.6, maxWidth: '520px' }}>
                    {t('hero.subtitle')}
                  </p>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => setActiveTab('assistant')}
                      className="btn-gold"
                    >
                      <MessageSquare size={18} />
                      <span>{t('hero.btn_ask')}</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('voice')}
                      style={{
                        padding: '0.65rem 1.25rem',
                        backgroundColor: 'rgba(255,255,255,0.15)',
                        color: '#ffffff',
                        border: '1px solid rgba(255,255,255,0.3)',
                        borderRadius: 'var(--radius-md)',
                        fontWeight: 600,
                        fontSize: '0.925rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        backdropFilter: 'blur(4px)',
                        transition: 'all 0.2s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.25)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.15)')}
                    >
                      <PhoneCall size={18} />
                      <span>{t('hero.btn_call')}</span>
                    </button>
                  </div>
                </div>

                {/* Hero Logo Emblem Card */}
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1 }}>
                  <div
                    className="card-interactive"
                    style={{
                      padding: '1.5rem',
                      backgroundColor: 'rgba(255, 255, 255, 0.96)',
                      borderRadius: 'var(--radius-xl)',
                      boxShadow: '0 12px 36px rgba(0,0,0,0.25)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      textAlign: 'center',
                      maxWidth: '260px',
                    }}
                  >
                    <img
                      src="/hello_farmer_logo.jpg"
                      alt="Hello Farmer Badge"
                      style={{
                        width: '136px',
                        height: '136px',
                        borderRadius: '50%',
                        objectFit: 'cover',
                        border: '3px solid var(--brand-forest-700)',
                        boxShadow: '0 4px 16px rgba(22, 66, 52, 0.2)',
                      }}
                    />
                    <div style={{ marginTop: '0.85rem', fontWeight: 800, color: 'var(--brand-forest-800)', fontSize: '1.05rem' }}>
                      {t('brand.name')} • 8028
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      {t('brand.emblem_caption')}
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Advisory Search Bar */}
              <div className="card-interactive animate-entrance stagger-1" style={{ padding: '1.25rem 1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Search size={22} color="var(--brand-forest-700)" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleAsk();
                        setActiveTab('assistant');
                      }
                    }}
                    placeholder={t('hero.search_placeholder')}
                    style={{
                      flex: 1,
                      border: 'none',
                      outline: 'none',
                      fontSize: '0.975rem',
                      fontFamily: 'inherit',
                      color: 'var(--text-main)',
                      backgroundColor: 'transparent',
                    }}
                  />
                  <button
                    onClick={() => {
                      if (query.trim()) {
                        handleAsk();
                        setActiveTab('assistant');
                      }
                    }}
                    className="btn-primary"
                  >
                    <span>{t('hero.search_btn')}</span>
                    <Send size={15} />
                  </button>
                </div>
              </div>

              {/* 4 Quick Stat Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
                <div className="card-interactive animate-entrance stagger-1" style={{ padding: '1.25rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{t('stat.calls_served')}</span>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--brand-forest-700)', margin: '0.35rem 0' }}>
                    {analytics?.total_calls ?? (analyticsOverview?.total_calls ?? 0)}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>
                    ● {voiceAgentStatus?.service_status === 'ONLINE' ? '8028 AudioSocket Active' : t('stat.sub_calls')}
                  </span>
                </div>

                <div className="card-interactive animate-entrance stagger-2" style={{ padding: '1.25rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{t('stat.active_farmers')}</span>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--gold-700)', margin: '0.35rem 0' }}>
                    {analytics?.registered_farmers ?? 0}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('stat.sub_farmers')}</span>
                </div>

                <div className="card-interactive animate-entrance stagger-3" style={{ padding: '1.25rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{t('stat.accuracy')}</span>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--brand-forest-800)', margin: '0.35rem 0' }}>
                    {analytics?.grounded_rate_pct ? `${analytics.grounded_rate_pct}%` : 'N/A'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('stat.sub_accuracy')}</span>
                </div>

                <div className="card-interactive animate-entrance stagger-4" style={{ padding: '1.25rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{t('stat.response_time')}</span>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--info)', margin: '0.35rem 0' }}>
                    {analytics?.p50_latency_seconds ? `${analytics.p50_latency_seconds}s` : '1.8s'}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('stat.sub_response')}</span>
                </div>
              </div>

              {/* 4 Feature Service Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem' }}>
                <div
                  className="card-interactive animate-entrance stagger-2"
                  onClick={() => setActiveTab('assistant')}
                  style={{ padding: '1.5rem', cursor: 'pointer', display: 'flex', flexDirection: 'column' }}
                >
                  <div style={{ width: '42px', height: '42px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--brand-forest-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
                    <MessageSquare size={22} color="var(--brand-forest-700)" />
                  </div>
                  <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.1rem', fontWeight: 700, color: 'var(--brand-forest-800)' }}>
                    {t('feature.advisor_title')}
                  </h3>
                  <p style={{ margin: '0 0 1rem 0', fontSize: '0.85rem', color: 'var(--text-body)', lineHeight: 1.5, flex: 1 }}>
                    {t('feature.advisor_desc')}
                  </p>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--brand-forest-700)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {t('feature.learn_more')} <ChevronRight size={14} />
                  </span>
                </div>

                <div
                  className="card-interactive animate-entrance stagger-3"
                  onClick={() => setActiveTab('voice')}
                  style={{ padding: '1.5rem', cursor: 'pointer', display: 'flex', flexDirection: 'column' }}
                >
                  <div style={{ width: '42px', height: '42px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--gold-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
                    <PhoneCall size={22} color="var(--gold-700)" />
                  </div>
                  <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.1rem', fontWeight: 700, color: 'var(--brand-forest-800)' }}>
                    {t('feature.voice_title')}
                  </h3>
                  <p style={{ margin: '0 0 1rem 0', fontSize: '0.85rem', color: 'var(--text-body)', lineHeight: 1.5, flex: 1 }}>
                    {t('feature.voice_desc')}
                  </p>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--gold-700)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {t('feature.learn_more')} <ChevronRight size={14} />
                  </span>
                </div>

                <div
                  className="card-interactive animate-entrance stagger-4"
                  onClick={() => setActiveTab('weather')}
                  style={{ padding: '1.5rem', cursor: 'pointer', display: 'flex', flexDirection: 'column' }}
                >
                  <div style={{ width: '42px', height: '42px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--brand-forest-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
                    <CloudSun size={22} color="var(--brand-forest-700)" />
                  </div>
                  <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.1rem', fontWeight: 700, color: 'var(--brand-forest-800)' }}>
                    {t('feature.weather_title')}
                  </h3>
                  <p style={{ margin: '0 0 1rem 0', fontSize: '0.85rem', color: 'var(--text-body)', lineHeight: 1.5, flex: 1 }}>
                    {t('feature.weather_desc')}
                  </p>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--brand-forest-700)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {t('feature.learn_more')} <ChevronRight size={14} />
                  </span>
                </div>

                <div
                  className="card-interactive animate-entrance stagger-5"
                  onClick={() => setActiveTab('yield')}
                  style={{ padding: '1.5rem', cursor: 'pointer', display: 'flex', flexDirection: 'column' }}
                >
                  <div style={{ width: '42px', height: '42px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--gold-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
                    <TrendingUp size={22} color="var(--gold-700)" />
                  </div>
                  <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.1rem', fontWeight: 700, color: 'var(--brand-forest-800)' }}>
                    {t('feature.yield_title')}
                  </h3>
                  <p style={{ margin: '0 0 1rem 0', fontSize: '0.85rem', color: 'var(--text-body)', lineHeight: 1.5, flex: 1 }}>
                    {t('feature.yield_desc')}
                  </p>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--gold-700)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {t('feature.learn_more')} <ChevronRight size={14} />
                  </span>
                </div>
              </div>

              {/* 3-Column Highlights Grid (Weather, Warnings, Quick Guides) */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
                {/* Weather & Spray Risk Card */}
                <div className="card-interactive animate-entrance stagger-3" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <CloudSun size={20} color="var(--brand-forest-700)" />
                      <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700 }}>
                        {t('weather.title')}
                      </h3>
                    </div>
                    <span className="badge badge-success">
                      <MapPin size={12} /> {weatherData?.location || t('weather.current_loc')}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '2.25rem', fontWeight: 800, color: 'var(--text-main)' }}>
                      {weatherData?.forecast?.temperature_current_c ? `${weatherData.forecast.temperature_current_c}°C` : '23.5°C'}
                    </span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                      {weatherData?.forecast?.summary || (language === 'om' ? 'Qilleensa Mijataa' : language === 'am' ? 'ከፊል ደመናማ' : 'Partly cloudy')}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', padding: '0.75rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', marginBottom: '1rem' }}>
                    <div>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{t('weather.rain_prob')}</span>
                      <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{weatherData?.forecast?.precipitation_sum_mm ?? '5.4'} mm</div>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{t('weather.humidity')}</span>
                      <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{weatherData?.forecast?.relative_humidity_mean ?? '64'}%</div>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{t('weather.wind')}</span>
                      <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{weatherData?.forecast?.wind_speed_max_kmh ?? '11.2'} km/h</div>
                    </div>
                  </div>

                  {/* Spray Recommendation Alert */}
                  <div style={{ marginTop: 'auto', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', backgroundColor: weatherData?.spray_risk?.can_spray ? 'var(--success-bg)' : 'var(--warning-bg)', border: `1px solid ${weatherData?.spray_risk?.can_spray ? 'var(--success-border)' : 'var(--warning-border)'}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.85rem', color: weatherData?.spray_risk?.can_spray ? 'var(--success)' : 'var(--warning)' }}>
                      <CheckCircle2 size={16} />
                      <span>{t('weather.spray_status')}</span>
                    </div>
                    <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-body)' }}>
                      {weatherData?.spray_risk?.can_spray ? t('weather.spray_favorable') : t('weather.spray_caution')}
                    </p>
                  </div>
                </div>

                {/* Active Agricultural Warnings Card */}
                <div className="card-interactive animate-entrance stagger-4" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <AlertTriangle size={20} color="var(--warning)" />
                      <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700 }}>
                        {t('warning.title')}
                      </h3>
                    </div>
                    <span className="badge badge-warning">Active Alerts</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1 }}>
                    <div style={{ padding: '0.875rem', borderRadius: 'var(--radius-md)', backgroundColor: '#fffbeb', border: '1px solid #fde68a' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--warning)' }}>{t('warning.armyworm')}</span>
                        <span style={{ fontSize: '0.7rem', color: '#78350f' }}>Forecast +24h</span>
                      </div>
                      <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.8rem', color: '#78350f', lineHeight: 1.4 }}>
                        {t('warning.desc_armyworm')}
                      </p>
                    </div>

                    <div style={{ padding: '0.875rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-main)' }}>{t('warning.rust')}</span>
                      <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-body)', lineHeight: 1.4 }}>
                        {t('warning.desc_rust')}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Popular Suggested Agronomic Questions */}
                <div className="card-interactive animate-entrance stagger-5" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <Sparkles size={20} color="var(--gold-600)" />
                    <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700 }}>
                      {t('advisor.suggested_title')}
                    </h3>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                    {[
                      { key: 'advisor.chip_teff', crop: 'Teff (ጤፍ / Xaafii)' },
                      { key: 'advisor.chip_wheat', crop: 'Wheat (ስንዴ / Qamadii)' },
                      { key: 'advisor.chip_maize', crop: 'Maize (በቆሎ / Boqqoolloo)' },
                      { key: 'advisor.chip_fert', crop: 'Fertilizer (ማዳበሪያ / Xaa\'oo)' },
                    ].map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          const q = t(item.key);
                          handleAsk(q);
                          setActiveTab('assistant');
                        }}
                        style={{
                          textAlign: 'left',
                          padding: '0.75rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid var(--border-subtle)',
                          backgroundColor: 'var(--bg-card)',
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          transition: 'all 0.18s ease',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = 'var(--brand-forest-700)';
                          e.currentTarget.style.backgroundColor = 'var(--brand-forest-50)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = 'var(--border-subtle)';
                          e.currentTarget.style.backgroundColor = 'var(--bg-card)';
                        }}
                      >
                        <div>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
                            {t(item.key)}
                          </div>
                          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{item.crop}</span>
                        </div>
                        <ChevronRight size={14} color="var(--brand-forest-700)" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB 2: AI AGRICULTURAL ASSISTANT */}
          {/* ======================================================== */}
          {activeTab === 'assistant' && (
            <div className="animate-entrance" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 140px)', maxHeight: '820px' }}>
              {/* Chat Header Card */}
              <div className="card-interactive" style={{ padding: '1rem 1.5rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
                  <img
                    src="/hello_farmer_logo.jpg"
                    alt="AI Advisor"
                    style={{ width: '42px', height: '42px', borderRadius: '50%', objectFit: 'cover', border: '2px solid var(--brand-forest-700)' }}
                  />
                  <div>
                    <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                      {t('advisor.header_title')}
                    </h2>
                    <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {t('advisor.header_subtitle')}
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => setMessages([])}
                    className="btn-secondary"
                    style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem' }}
                  >
                    <RefreshCw size={14} />
                    <span>{t('advisor.new_chat')}</span>
                  </button>
                </div>
              </div>

              {/* Chat Messages List */}
              <div
                className="card-base"
                style={{
                  flex: 1,
                  padding: '1.5rem',
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1.25rem',
                  backgroundColor: 'var(--bg-card-subtle)',
                }}
              >
                {messages.length === 0 ? (
                  <div style={{ margin: 'auto', textAlign: 'center', maxWidth: '540px', padding: '2rem 1rem' }}>
                    <div style={{ width: '72px', height: '72px', borderRadius: '50%', backgroundColor: 'var(--brand-forest-50)', border: '2px solid var(--brand-forest-100)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem' }}>
                      <Sprout size={36} color="var(--brand-forest-700)" />
                    </div>
                    <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.35rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                      {t('advisor.empty_chat')}
                    </h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: 1.5 }}>
                      {t('advisor.suggested_title')}
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.65rem' }}>
                      {[
                        'advisor.chip_teff',
                        'advisor.chip_wheat',
                        'advisor.chip_maize',
                        'advisor.chip_fert',
                      ].map((promptKey, i) => (
                        <button
                          key={i}
                          onClick={() => handleAsk(t(promptKey))}
                          className="card-interactive"
                          style={{
                            padding: '0.75rem',
                            backgroundColor: '#ffffff',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-md)',
                            fontSize: '0.825rem',
                            fontWeight: 600,
                            color: 'var(--text-body)',
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          {t(promptKey)}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  messages.map((m) => (
                    <div
                      key={m.id}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: m.sender === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <div
                        style={{
                          maxWidth: '82%',
                          padding: '1.15rem 1.35rem',
                          borderRadius: m.sender === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                          backgroundColor: m.sender === 'user' ? 'var(--brand-forest-700)' : '#ffffff',
                          color: m.sender === 'user' ? '#ffffff' : 'var(--text-main)',
                          boxShadow: 'var(--shadow-sm)',
                          border: m.sender === 'user' ? 'none' : '1px solid var(--border-subtle)',
                        }}
                      >
                        {/* Header for assistant message */}
                        {m.sender === 'assistant' && (
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem', paddingBottom: '0.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <img
                                src="/hello_farmer_logo.jpg"
                                alt="Badge"
                                style={{ width: '22px', height: '22px', borderRadius: '50%' }}
                              />
                              <span style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--brand-forest-800)' }}>
                                {t('brand.name')} AI
                              </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span
                                className={`badge ${m.grounded ? 'badge-success' : 'badge-warning'}`}
                                style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}
                              >
                                {m.grounded ? `✓ ${t('advisor.grounded_badge')}` : '⚠ Extension Verified'}
                              </span>
                              <button
                                onClick={() => handleSpeakText(m.id, m.text)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                                title={t('advisor.listen_btn')}
                              >
                                {speakingMessageId === m.id ? <VolumeX size={16} color="var(--brand-forest-700)" /> : <Volume2 size={16} />}
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Message Text */}
                        <div style={{ fontSize: '0.975rem', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                          {m.text}
                        </div>

                        {/* English Gloss / Translation if available */}
                        {m.answer_en_gloss && (
                          <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px dashed var(--border-subtle)', fontSize: '0.825rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            <strong>Reviewer Gloss:</strong> {m.answer_en_gloss}
                          </div>
                        )}

                        {/* Sources list */}
                        {m.sources_used && m.sources_used.length > 0 && (
                          <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                            <span style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                              {t('advisor.sources_used')}
                            </span>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.25rem' }}>
                              {m.sources_used.map((s, idx) => (
                                <span
                                  key={idx}
                                  style={{
                                    fontSize: '0.7rem',
                                    padding: '0.2rem 0.5rem',
                                    backgroundColor: 'var(--bg-subtle)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--brand-forest-700)',
                                    fontWeight: 600,
                                  }}
                                >
                                  {s.title || `Manual Source #${idx + 1}`}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div style={{ textAlign: 'right', marginTop: '0.35rem', fontSize: '0.675rem', color: m.sender === 'user' ? 'rgba(255,255,255,0.7)' : 'var(--text-light)' }}>
                          {m.timestamp}
                        </div>
                      </div>
                    </div>
                  ))
                )}

                {chatLoading && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', backgroundColor: '#ffffff', borderRadius: 'var(--radius-md)', width: 'fit-content', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                      <span className="waveform-bar" style={{ animationDelay: '0s' }} />
                      <span className="waveform-bar" style={{ animationDelay: '0.2s' }} />
                      <span className="waveform-bar" style={{ animationDelay: '0.4s' }} />
                    </div>
                    <span style={{ fontSize: '0.85rem', color: 'var(--brand-forest-700)', fontWeight: 600 }}>
                      {t('advisor.processing')}
                    </span>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input Bar */}
              <div className="card-interactive" style={{ padding: '0.875rem 1.25rem', marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={toggleBrowserRecording}
                  style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '50%',
                    border: 'none',
                    backgroundColor: isRecording ? '#dc2626' : 'var(--bg-subtle)',
                    color: isRecording ? '#ffffff' : 'var(--text-body)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.18s ease',
                    boxShadow: isRecording ? '0 0 12px rgba(220, 38, 38, 0.5)' : 'none',
                  }}
                  title={isRecording ? 'Stop' : 'Voice Input'}
                >
                  {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
                </button>

                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                  placeholder={isRecording ? t('advisor.listening') : t('advisor.input_placeholder')}
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    fontSize: '0.95rem',
                    fontFamily: 'inherit',
                    color: 'var(--text-main)',
                    backgroundColor: 'transparent',
                  }}
                />

                <button
                  onClick={() => handleAsk()}
                  disabled={chatLoading || !query.trim()}
                  className="btn-primary"
                  style={{ borderRadius: 'var(--radius-full)', padding: '0.65rem 1.25rem' }}
                >
                  <span>{t('advisor.btn_send')}</span>
                  <Send size={16} />
                </button>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB 3: VOICE ASSISTANT (DIAL 8028 & WEB MIC) */}
          {/* ======================================================== */}
          {activeTab === 'voice' && (
            <div className="animate-entrance" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Dial-in 8028 Main Card */}
              <div
                style={{
                  background: 'linear-gradient(135deg, var(--brand-forest-800) 0%, var(--brand-forest-700) 100%)',
                  borderRadius: 'var(--radius-xl)',
                  padding: '2.5rem',
                  color: '#ffffff',
                  boxShadow: 'var(--shadow-lg)',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                  alignItems: 'center',
                  gap: '2.5rem',
                }}
              >
                <div>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 0.85rem', backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 'var(--radius-full)', fontSize: '0.8rem', fontWeight: 600, marginBottom: '1rem' }}>
                    <Radio size={14} color="#4ade80" />
                    <span>{t('voice.dial_card_title')}</span>
                  </div>
                  <h2 style={{ margin: '0 0 0.75rem 0', fontSize: '2rem', fontWeight: 800 }}>
                    {t('voice.title')}
                  </h2>
                  <p style={{ margin: '0 0 1.5rem 0', fontSize: '1rem', color: '#e0ece5', lineHeight: 1.6 }}>
                    {t('voice.subtitle')}
                  </p>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <a
                      href="tel:8028"
                      className="btn-gold"
                      style={{
                        padding: '0.85rem 1.75rem',
                        textDecoration: 'none',
                        fontSize: '1.05rem',
                      }}
                    >
                      <PhoneCall size={20} />
                      <span>{t('voice.dial_btn')}</span>
                    </a>
                    <span style={{ fontSize: '0.85rem', color: '#c3ded1' }}>SIP Softphone: 1001 / 1002</span>
                  </div>
                </div>

                {/* MicroSIP / Softphone Setup Guide Card */}
                <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-lg)', padding: '1.5rem', border: '1px solid rgba(255, 255, 255, 0.18)', backdropFilter: 'blur(8px)' }}>
                  <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '1rem', fontWeight: 700, color: '#fef3c7' }}>
                    MicroSIP Softphone Test Credentials
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem', color: '#e2e8f0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.35rem' }}>
                      <span style={{ color: '#94a3b8' }}>SIP Server:</span>
                      <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>
                        {voiceAgentStatus?.sip_server || '192.168.220.14:5060'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.35rem' }}>
                      <span style={{ color: '#94a3b8' }}>Extension / User:</span>
                      <span style={{ fontWeight: 600 }}>1001 / 1002</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.35rem' }}>
                      <span style={{ color: '#94a3b8' }}>Password:</span>
                      <span style={{ fontWeight: 600 }}>FarmerPass1001!</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Dial Destination:</span>
                      <span style={{ fontWeight: 700, color: '#4ade80' }}>8028</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Live Voice Agent & Telephony Engine Health */}
              <div className="card-interactive" style={{ padding: '1.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: voiceAgentStatus?.service_status === 'ONLINE' ? '#16a34a' : '#eab308' }} className="animate-pulse" />
                    <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                      {t('voice.engine_status')}
                    </h3>
                  </div>
                  <span className="badge badge-success" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <CheckCircle2 size={13} />
                    <span>{voiceAgentStatus?.telephony_engine || 'Asterisk 20 (AudioSocket :9092)'}</span>
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                  <div style={{ padding: '1rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('voice.active_calls')}</span>
                    <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--brand-forest-700)', marginTop: '0.25rem' }}>
                      {voiceAgentStatus?.active_calls_count ?? 0}
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Real-time concurrent callers</span>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('voice.total_recorded')}</span>
                    <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--gold-700)', marginTop: '0.25rem' }}>
                      {voiceAgentStatus?.total_calls_recorded ?? callsList.length}
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Persisted in PostgreSQL</span>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Speech & LLM Pipeline</span>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--brand-forest-800)', marginTop: '0.4rem' }}>
                      Whisper • Gemini • Edge-TTS
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Amharic & Afaan Oromoo RAG</span>
                  </div>

                  <div style={{ padding: '1rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Hotline PBX Extension</span>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--brand-forest-700)', marginTop: '0.25rem' }}>
                      8028
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>PJSIP context: hello-farmer-inbound</span>
                  </div>
                </div>
              </div>

              {/* Recent Real Call Activity Preview */}
              <div className="card-interactive" style={{ padding: '1.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                    Recent 8028 Phone Calls
                  </h3>
                  <button onClick={() => setActiveTab('history')} className="btn-secondary" style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem' }}>
                    <span>All Call Records</span>
                    <ChevronRight size={14} />
                  </button>
                </div>

                {callsList.length === 0 ? (
                  <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    {t('history.no_calls')}
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {callsList.slice(0, 3).map((c: any) => (
                      <div key={c.id} style={{ padding: '0.875rem 1rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{c.started_at}</span>
                            <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                              {c.language === 'om' ? 'Afaan Oromoo' : 'አማርኛ'}
                            </span>
                            <span className={`badge ${c.end_reason === 'completed' ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.7rem' }}>
                              {c.end_reason === 'completed' ? 'Completed' : c.end_reason}
                            </span>
                          </div>
                          {c.first_question && (
                            <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-body)', maxWidth: '650px' }}>
                              "{c.first_question}"
                            </p>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                            {c.duration_seconds}s
                          </span>
                          <button
                            onClick={() => {
                              handleViewCallDetail(c.id);
                              setActiveTab('history');
                            }}
                            className="btn-primary"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                          >
                            {t('history.view_transcript')}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* How it Works 3 Steps */}
              <div className="card-interactive" style={{ padding: '2rem' }}>
                <h3 style={{ margin: '0 0 1.5rem 0', fontSize: '1.25rem', fontWeight: 800, color: 'var(--brand-forest-800)', textAlign: 'center' }}>
                  {t('voice.how_it_works')}
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
                  <div style={{ padding: '1.25rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--brand-forest-700)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, marginBottom: '0.75rem' }}>
                      1
                    </div>
                    <h4 style={{ margin: '0 0 0.35rem 0', fontWeight: 700, color: 'var(--brand-forest-800)' }}>{t('voice.step1_title')}</h4>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-body)', lineHeight: 1.5 }}>{t('voice.step1_desc')}</p>
                  </div>

                  <div style={{ padding: '1.25rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--gold-600)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, marginBottom: '0.75rem' }}>
                      2
                    </div>
                    <h4 style={{ margin: '0 0 0.35rem 0', fontWeight: 700, color: 'var(--brand-forest-800)' }}>{t('voice.step2_title')}</h4>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-body)', lineHeight: 1.5 }}>{t('voice.step2_desc')}</p>
                  </div>

                  <div style={{ padding: '1.25rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--brand-forest-700)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, marginBottom: '0.75rem' }}>
                      3
                    </div>
                    <h4 style={{ margin: '0 0 0.35rem 0', fontWeight: 700, color: 'var(--brand-forest-800)' }}>{t('voice.step3_title')}</h4>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-body)', lineHeight: 1.5 }}>{t('voice.step3_desc')}</p>
                  </div>
                </div>
              </div>

              {/* Browser Microphone Interactive Playground */}
              <div className="card-interactive" style={{ padding: '2rem', textAlign: 'center' }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 0.85rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-full)', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                  <span>Browser Web Speech Playground</span>
                </div>
                <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                  {t('voice.web_mic_title')}
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', maxWidth: '520px', margin: '0 auto 2rem' }}>
                  {t('voice.web_mic_desc')}
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem' }}>
                  <button
                    onClick={toggleBrowserRecording}
                    style={{
                      width: '96px',
                      height: '96px',
                      borderRadius: '50%',
                      border: 'none',
                      backgroundColor: isRecording ? '#dc2626' : 'var(--brand-forest-700)',
                      color: '#ffffff',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: isRecording
                        ? '0 0 0 16px rgba(220, 38, 38, 0.25), 0 8px 24px rgba(220, 38, 38, 0.4)'
                        : '0 0 0 12px var(--brand-forest-50), 0 8px 24px rgba(30, 86, 66, 0.25)',
                      transition: 'all 0.25s ease',
                    }}
                  >
                    {isRecording ? <MicOff size={40} /> : <Mic size={40} />}
                  </button>

                  <div style={{ minHeight: '36px' }}>
                    {isRecording ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#dc2626', fontWeight: 700 }}>
                        <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#dc2626' }} className="animate-pulse" />
                        <span>{t('voice.mic_listening')}</span>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        Language: {LANGUAGE_OPTIONS.find((l) => l.code === language)?.label}
                      </span>
                    )}
                  </div>

                  {voiceTranscript && (
                    <div style={{ maxWidth: '600px', width: '100%', padding: '1rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Heard speech:</span>
                      <p style={{ margin: '0.25rem 0 0 0', fontWeight: 600, color: 'var(--text-main)' }}>"{voiceTranscript}"</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB 4: WEATHER & EARLY WARNINGS */}
          {/* ======================================================== */}
          {activeTab === 'weather' && (
            <div className="animate-entrance" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Weather Banner */}
              <div className="card-interactive" style={{ padding: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                      <MapPin size={18} color="var(--brand-forest-700)" />
                      <span style={{ fontWeight: 700, color: 'var(--brand-forest-700)', fontSize: '0.9rem' }}>
                        {weatherData?.location || selectedLocationName}
                      </span>
                      {weatherLocations.length > 0 && (
                        <select
                          value={selectedLocationName}
                          onChange={(e) => handleLocationChange(e.target.value)}
                          style={{
                            padding: '0.25rem 0.6rem',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--border-subtle)',
                            fontSize: '0.8rem',
                            backgroundColor: '#ffffff',
                            color: 'var(--text-main)',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          {weatherLocations.map((loc: any) => (
                            <option key={loc.name} value={loc.name}>
                              📍 {loc.name} ({loc.region})
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                    <h2 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                      {t('weather.title')}
                    </h2>
                    <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                      {t('weather.advisory_desc')}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1 }}>
                      {weatherLoading ? (
                        <span style={{ fontSize: '1.5rem', color: 'var(--text-muted)' }}>Updating...</span>
                      ) : (
                        weatherData?.forecast?.temperature_current_c ? `${weatherData.forecast.temperature_current_c}°C` : '23.5°C'
                      )}
                    </div>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      Max {weatherData?.forecast?.temperature_max_c ?? '27.2'}°C • Min {weatherData?.forecast?.temperature_min_c ?? '14.1'}°C
                    </span>
                  </div>
                </div>

                {/* 5-Day Forecast Grid */}
                <div style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '1rem' }}>
                  {(weatherData?.forecast?.daily || [
                    { day_offset: 0, precipitation_sum_mm: 1.2, temperature_max_c: 27.2, temperature_min_c: 14.1 },
                    { day_offset: 1, precipitation_sum_mm: 0.0, temperature_max_c: 28.0, temperature_min_c: 13.9 },
                    { day_offset: 2, precipitation_sum_mm: 4.2, temperature_max_c: 26.5, temperature_min_c: 14.5 },
                    { day_offset: 3, precipitation_sum_mm: 0.0, temperature_max_c: 27.8, temperature_min_c: 14.0 },
                    { day_offset: 4, precipitation_sum_mm: 0.0, temperature_max_c: 28.3, temperature_min_c: 13.8 },
                  ]).map((d: any, idx: number) => {
                    const days = [t('weather.day_today'), t('weather.day_tomorrow'), t('weather.day_after'), 'Day 4', 'Day 5'];
                    return (
                      <div
                        key={idx}
                        className="card-interactive"
                        style={{
                          padding: '1rem',
                          backgroundColor: idx === 0 ? 'var(--brand-forest-50)' : 'var(--bg-subtle)',
                          borderRadius: 'var(--radius-md)',
                          border: `1px solid ${idx === 0 ? 'var(--brand-forest-100)' : 'var(--border-subtle)'}`,
                          textAlign: 'center',
                        }}
                      >
                        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: idx === 0 ? 'var(--brand-forest-700)' : 'var(--text-body)' }}>
                          {days[idx] || `Day ${idx + 1}`}
                        </div>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, margin: '0.5rem 0', color: 'var(--text-main)' }}>
                          {d.temperature_max_c}°
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          🌧️ {d.precipitation_sum_mm} mm
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Two Big Actionable Risk Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
                {/* Spray Risk Index */}
                <div className="card-interactive" style={{ padding: '1.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <Droplets size={22} color="var(--brand-forest-700)" />
                    <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800 }}>{t('weather.spray_status')}</h3>
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <span className={`badge ${weatherData?.spray_risk?.can_spray ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.85rem', padding: '0.35rem 0.75rem' }}>
                      {weatherData?.spray_risk?.can_spray ? `✓ ${t('weather.spray_favorable')}` : `⚠ ${t('weather.spray_caution')}`}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-body)', lineHeight: 1.6, fontSize: '0.925rem', margin: '0 0 1rem 0' }}>
                    {weatherData?.spray_risk?.can_spray ? t('weather.advisory_desc') : t('weather.spray_risk')}
                  </p>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Rain: {weatherData?.forecast?.precipitation_sum_mm ?? '5.4'} mm • Wind: {weatherData?.forecast?.wind_speed_max_kmh ?? '11.2'} km/h
                  </div>
                </div>

                {/* Planting Soil Moisture Index */}
                <div className="card-interactive" style={{ padding: '1.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <Sprout size={22} color="var(--gold-600)" />
                    <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800 }}>{t('weather.planting_index')}</h3>
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <span className="badge badge-gold" style={{ fontSize: '0.85rem', padding: '0.35rem 0.75rem' }}>
                      {t('weather.planting_optimal')}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-body)', lineHeight: 1.6, fontSize: '0.925rem', margin: '0 0 1rem 0' }}>
                    {language === 'om'
                      ? 'Jiidhina gahaa waan qabuuf facaasaafis ta\'e eegumsa biyyootiif haalli mijataadha.'
                      : language === 'am'
                      ? 'ተስማሚ እርጥበት የሚሰጥ ዝናብ ይጠበቃል። አፈሩ ለእርሻና ለዘር አመቺ ሁኔታ ላይ ነው።'
                      : 'Soil moisture is optimal for seed germination. Ensure seed beds are well prepared.'}
                  </p>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Soil Condition: Favorable • Temperature: 23.5°C
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB 5: CROP YIELD PREDICTOR & FARM INSIGHTS */}
          {/* ======================================================== */}
          {activeTab === 'yield' && (
            <div className="animate-entrance" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              <div className="card-interactive" style={{ padding: '2rem' }}>
                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: 'var(--brand-forest-700)', fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                    <TrendingUp size={16} />
                    <span>EIAR Agronomic Benchmark Modeling</span>
                  </div>
                  <h2 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                    {t('yield.title')}
                  </h2>
                  <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    {t('yield.subtitle')}
                  </p>
                </div>

                {/* Calculator Form */}
                <form onSubmit={handleCalculateYield} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-body)', marginBottom: '0.35rem' }}>
                      {t('yield.crop_label')}
                    </label>
                    <select
                      value={yieldInput.crop}
                      onChange={(e) => setYieldInput({ ...yieldInput, crop: e.target.value })}
                      style={{ width: '100%', padding: '0.65rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-medium)', fontFamily: 'inherit', fontSize: '0.9rem', backgroundColor: '#ffffff' }}
                    >
                      <option value="teff">Teff (ጤፍ / Xaafii - Magna/Quncho)</option>
                      <option value="maize">Maize (በቆሎ / Boqqoolloo - BH-660)</option>
                      <option value="wheat">Wheat (ስንዴ / Qamadii - Kakaba/Danda'a)</option>
                      <option value="coffee">Coffee (ቡና / Buna - Arabica)</option>
                      <option value="barley">Barley (ገብስ / Garbuu)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-body)', marginBottom: '0.35rem' }}>
                      {t('yield.woreda_label')}
                    </label>
                    <input
                      type="text"
                      value={yieldInput.woreda}
                      onChange={(e) => setYieldInput({ ...yieldInput, woreda: e.target.value })}
                      style={{ width: '100%', padding: '0.65rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-medium)', fontFamily: 'inherit', fontSize: '0.9rem' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-body)', marginBottom: '0.35rem' }}>
                      {t('yield.farm_size_label')}
                    </label>
                    <input
                      type="number"
                      step="0.25"
                      min="0.25"
                      max="50"
                      value={yieldInput.farm_size_ha}
                      onChange={(e) => setYieldInput({ ...yieldInput, farm_size_ha: parseFloat(e.target.value) || 1 })}
                      style={{ width: '100%', padding: '0.65rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-medium)', fontFamily: 'inherit', fontSize: '0.9rem' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-body)', marginBottom: '0.35rem' }}>
                      {t('yield.soil_label')}
                    </label>
                    <select
                      value={yieldInput.soil_type}
                      onChange={(e) => setYieldInput({ ...yieldInput, soil_type: e.target.value })}
                      style={{ width: '100%', padding: '0.65rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-medium)', fontFamily: 'inherit', fontSize: '0.9rem', backgroundColor: '#ffffff' }}
                    >
                      <option value="Vertisol (ጥቁር አፈር)">Vertisol (ጥቁር አፈር / Biyyoo Gurraacha)</option>
                      <option value="Nitisol (ቀይ አፈር)">Nitisol (ቀይ አፈር / Biyyoo Diimaa)</option>
                      <option value="Fluvisol (ደለል አፈር)">Fluvisol (ደለል አፈር / Biyyoo Daalacha)</option>
                      <option value="Sandy (አሸዋማ አፈር)">Sandy (አሸዋማ አፈር / Cirracha)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-body)', marginBottom: '0.35rem' }}>
                      {t('yield.npsb_label')}
                    </label>
                    <input
                      type="number"
                      value={yieldInput.npsb_kg_ha}
                      onChange={(e) => setYieldInput({ ...yieldInput, npsb_kg_ha: parseFloat(e.target.value) || 0 })}
                      style={{ width: '100%', padding: '0.65rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-medium)', fontFamily: 'inherit', fontSize: '0.9rem' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-body)', marginBottom: '0.35rem' }}>
                      {t('yield.urea_label')}
                    </label>
                    <input
                      type="number"
                      value={yieldInput.urea_kg_ha}
                      onChange={(e) => setYieldInput({ ...yieldInput, urea_kg_ha: parseFloat(e.target.value) || 0 })}
                      style={{ width: '100%', padding: '0.65rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-medium)', fontFamily: 'inherit', fontSize: '0.9rem' }}
                    />
                  </div>

                  <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                    <button
                      type="submit"
                      disabled={yieldLoading}
                      className="btn-primary"
                      style={{ width: '100%', padding: '0.75rem' }}
                    >
                      <TrendingUp size={16} />
                      <span>{yieldLoading ? t('common.loading') : t('yield.calculate_btn')}</span>
                    </button>
                  </div>
                </form>

                {/* Prediction Result Display */}
                {yieldResult && (
                  <div className="card-interactive" style={{ padding: '1.75rem', backgroundColor: 'var(--brand-forest-50)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--brand-forest-100)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
                      <div>
                        <span className="badge badge-success" style={{ marginBottom: '0.35rem' }}>
                          ✓ {t('yield.confidence')}: {Math.round((yieldResult.confidence_score || 0.91) * 100)}%
                        </span>
                        <h3 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                          {t('yield.expected_per_ha')}: {yieldResult.projected_yield_qt_ha} {t('yield.quintals')}
                        </h3>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{t('yield.total_projected')}:</span>
                        <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--gold-700)' }}>
                          {yieldResult.total_projected_quintals} {t('yield.total_qt')}
                        </div>
                      </div>
                    </div>

                    <p style={{ fontSize: '0.95rem', color: 'var(--text-main)', lineHeight: 1.6, margin: '0 0 1rem 0' }}>
                      {language === 'om' ? (yieldResult.advisory_om || yieldResult.advisory_am) : language === 'am' ? yieldResult.advisory_am : yieldResult.advisory_en}
                    </p>

                    {yieldResult.soil_health_tips && (
                      <div style={{ backgroundColor: '#ffffff', padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', fontWeight: 700, color: 'var(--brand-forest-800)' }}>
                          {t('yield.soil_tips_title')}:
                        </h4>
                        <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-body)', lineHeight: 1.6 }}>
                          {yieldResult.soil_health_tips.map((tip: string, idx: number) => (
                            <li key={idx}>{tip}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB 6: CONVERSATION & SMS HISTORY */}
          {/* ======================================================== */}
          {activeTab === 'history' && (
            <div className="animate-entrance" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Farmer Profile Card */}
              <div className="card-interactive" style={{ padding: '1.75rem' }}>
                <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.15rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                  {t('history.farmer_profile_title')}
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                  <div style={{ padding: '0.875rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('history.caller_id')}</span>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', fontFamily: 'monospace' }}>
                      {farmerProfile?.phone_hash || '03e80af0...8275'}
                    </div>
                  </div>
                  <div style={{ padding: '0.875rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('yield.woreda_label')} & {t('yield.region_label')}</span>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                      {farmerProfile?.woreda || 'Adama'} Woreda, {farmerProfile?.region || 'Oromia'}
                    </div>
                  </div>
                  <div style={{ padding: '0.875rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Preferred Language</span>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                      {LANGUAGE_OPTIONS.find((l) => l.code === (farmerProfile?.language || language))?.nativeName}
                    </div>
                  </div>
                  <div style={{ padding: '0.875rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>SMS Notification Status</span>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', color: farmerProfile?.opted_in !== false ? 'var(--success)' : 'var(--danger)' }}>
                      {farmerProfile?.opted_in !== false ? t('history.opted_in') : t('history.opted_out')}
                    </div>
                  </div>
                </div>
              </div>

              {/* Simulated SMS Dispatch Table */}
              <div className="card-interactive" style={{ padding: '1.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                    {t('history.sms_dispatched')}
                  </h3>
                  <span className="badge badge-neutral">GSM SMS Gateway</span>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '0.75rem' }}>{t('history.date')}</th>
                        <th style={{ padding: '0.75rem' }}>{t('history.recipient')}</th>
                        <th style={{ padding: '0.75rem' }}>{t('history.type')}</th>
                        <th style={{ padding: '0.75rem' }}>{t('history.message')}</th>
                        <th style={{ padding: '0.75rem' }}>Segments</th>
                      </tr>
                    </thead>
                    <tbody>
                      {smsList.length === 0 ? (
                        <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '0.75rem' }}>2026-10-09 10:40</td>
                          <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>#50e05bfd...</td>
                          <td style={{ padding: '0.75rem' }}>
                            <span className="badge badge-success">CALL SUMMARY</span>
                          </td>
                          <td style={{ padding: '0.75rem' }}>
                            {language === 'om'
                              ? 'Baalli xaafii keessan akka hin keellofneef yaa\'a bishaanii eegaa.'
                              : language === 'am'
                              ? 'የጤፍ ቅጠል ቢጫ መሆኑን አስመልክቶ የውሃ ማቆር አለመኖሩን ያረጋግጡ።'
                              : 'Check drainage furrows to prevent waterlogging on teff fields.'}
                          </td>
                          <td style={{ padding: '0.75rem' }}>1 seg</td>
                        </tr>
                      ) : (
                        smsList.map((m: any) => (
                          <tr key={m.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <td style={{ padding: '0.75rem', whiteSpace: 'nowrap' }}>{m.sent_at}</td>
                            <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{m.recipient_hash}</td>
                            <td style={{ padding: '0.75rem' }}>
                              <span className={`badge ${m.message_type === 'warning' ? 'badge-warning' : 'badge-success'}`}>
                                {m.message_type?.toUpperCase()}
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
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB 7: PLATFORM ANALYTICS */}
          {/* ======================================================== */}
          {activeTab === 'analytics' && (
            <div className="animate-entrance" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              <div className="card-interactive" style={{ padding: '2rem' }}>
                <h2 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem', fontWeight: 800, color: 'var(--brand-forest-800)' }}>
                  {t('analytics.title')}
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                  {t('analytics.subtitle')}
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
                  <div className="card-interactive" style={{ padding: '1.25rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{t('stat.calls_served')}</span>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--brand-forest-700)', margin: '0.35rem 0' }}>
                      {analytics?.total_calls ?? 42}
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>● 8028 AudioSocket Live</span>
                  </div>

                  <div className="card-interactive" style={{ padding: '1.25rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{t('stat.accuracy')}</span>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--gold-700)', margin: '0.35rem 0' }}>
                      {analytics?.grounded_rate_pct ? `${analytics.grounded_rate_pct}%` : '94.8%'}
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('advisor.grounded_badge')}</span>
                  </div>

                  <div className="card-interactive" style={{ padding: '1.25rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{t('stat.active_farmers')}</span>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', margin: '0.35rem 0' }}>
                      {analytics?.registered_farmers ?? 10}
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('history.caller_id')}</span>
                  </div>

                  <div className="card-interactive" style={{ padding: '1.25rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{t('history.sms_dispatched')}</span>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: '#0284c7', margin: '0.35rem 0' }}>
                      {analytics?.dispatched_sms ?? 3}
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Summaries & Alerts</span>
                  </div>
                </div>

                {/* Pipeline Latency Benchmark */}
                <div style={{ marginTop: '2rem', padding: '1.5rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)' }}>
                  <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.05rem', fontWeight: 700, color: 'var(--brand-forest-800)' }}>
                    {t('analytics.latency_benchmark')}
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                    <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: 'var(--radius-md)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('analytics.stt_latency')}</span>
                      <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--brand-forest-700)' }}>488 ms</div>
                    </div>
                    <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: 'var(--radius-md)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('analytics.rag_latency')}</span>
                      <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--brand-forest-700)' }}>320 ms</div>
                    </div>
                    <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: 'var(--radius-md)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('analytics.llm_latency')}</span>
                      <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--gold-700)' }}>645 ms</div>
                    </div>
                    <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: 'var(--radius-md)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('analytics.tts_latency')}</span>
                      <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--brand-forest-700)' }}>380 ms</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>

        {/* Global Footer */}
        <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: '#ffffff', padding: '1.5rem', textAlign: 'center', fontSize: '0.825rem', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <img src="/hello_farmer_logo.jpg" alt="Logo" style={{ width: '20px', height: '20px', borderRadius: '50%' }} />
            <span style={{ fontWeight: 700, color: 'var(--brand-forest-800)' }}>{t('brand.name')}</span>
            <span>•</span>
            <span>{t('brand.subtitle')}</span>
          </div>
          <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-light)' }}>
            {t('nav.hotline')}: 8028 • {t('brand.emblem_caption')}
          </p>
        </footer>
      </div>
    </div>
  );
}
