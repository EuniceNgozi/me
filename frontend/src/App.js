import React, { useState, useEffect, useCallback } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";
import axios from "axios";
import { 
  TrendingUp, 
  Users, 
  Target, 
  BarChart3, 
  Search,
  Zap,
  ExternalLink,
  ArrowUp,
  ArrowDown,
  Loader2,
  PlusCircle,
  LogOut,
  User,
  Crown,
  Link as LinkIcon,
  CheckCircle,
  AlertCircle,
  Settings
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = React.createContext();

// Auth Provider
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      // Check for session_id in URL fragment first
      const hash = window.location.hash;
      if (hash && hash.includes('session_id=')) {
        const sessionId = hash.split('session_id=')[1].split('&')[0];
        await processSessionId(sessionId);
        return;
      }

      // Check existing session
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true
      });
      
      setUser(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const processSessionId = async (sessionId) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/auth/process-session`, {
        session_id: sessionId
      }, {
        withCredentials: true
      });

      if (response.data.success) {
        setUser(response.data.user);
        setIsAuthenticated(true);
        
        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    } catch (error) {
      console.error('Session processing failed:', error);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    const redirectUrl = encodeURIComponent(`${window.location.origin}/dashboard`);
    window.location.href = `https://auth.emergentagent.com/?redirect=${redirectUrl}`;
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, {
        withCredentials: true
      });
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setUser(null);
      setIsAuthenticated(false);
      window.location.href = '/';
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      loading,
      login,
      logout,
      checkAuth
    }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Landing Page Component
const LandingPage = () => {
  const { login } = useAuth();

  return (
    <div className="landing-page">
      <div className="landing-header">
        <div className="logo">
          <div className="logo-icon">
            <Zap />
          </div>
          Viral Leads
        </div>
        <button className="btn btn-primary" onClick={login}>
          Get Started Free
        </button>
      </div>
      
      <div className="landing-hero">
        <div className="hero-content">
          <h1>AI-Powered Social Media Lead Generation</h1>
          <p>Discover potential customers interested in digital products across Facebook, Instagram, Pinterest, and TikTok with advanced AI analysis.</p>
          
          <div className="hero-features">
            <div className="feature-item">
              <Target className="feature-icon" />
              <span>Smart Lead Discovery</span>
            </div>
            <div className="feature-item">
              <BarChart3 className="feature-icon" />
              <span>AI Content Analysis</span>
            </div>
            <div className="feature-item">
              <TrendingUp className="feature-icon" />
              <span>Trending Topics</span>
            </div>
          </div>
          
          <button className="btn btn-primary hero-cta" onClick={login}>
            Start Discovering Leads
            <ArrowUp className="rotate-45" size={18} />
          </button>
          
          <p className="hero-subtitle">Free tier includes 50 leads per month • No credit card required</p>
        </div>
      </div>
      
      <div className="landing-stats">
        <div className="stat-item">
          <div className="stat-number">10K+</div>
          <div className="stat-label">Leads Discovered</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">4</div>
          <div className="stat-label">Platforms</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">95%</div>
          <div className="stat-label">Accuracy</div>
        </div>
      </div>
    </div>
  );
};

// Login Page Component
const LoginPage = () => {
  const { login } = useAuth();

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <div className="logo">
            <div className="logo-icon">
              <Zap />
            </div>
            Viral Leads
          </div>
        </div>
        
        <div className="login-content">
          <h2>Welcome Back</h2>
          <p>Sign in to continue discovering high-quality leads with AI-powered analysis.</p>
          
          <button className="btn btn-primary login-btn" onClick={login}>
            <User size={18} />
            Continue with Google
          </button>
          
          <div className="login-features">
            <div className="login-feature">
              <CheckCircle size={16} />
              <span>Secure OAuth Authentication</span>
            </div>
            <div className="login-feature">
              <CheckCircle size={16} />
              <span>Free Tier Available</span>
            </div>
            <div className="login-feature">
              <CheckCircle size={16} />
              <span>Real-time Lead Discovery</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const { user } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [leads, setLeads] = useState([]);
  const [trending, setTrending] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [analyticsRes, leadsRes, trendingRes] = await Promise.all([
        axios.get(`${API}/analytics`, { withCredentials: true }),
        axios.get(`${API}/leads?limit=6`, { withCredentials: true }),
        axios.get(`${API}/trending`, { withCredentials: true })
      ]);
      
      setAnalytics(analyticsRes.data);
      setLeads(leadsRes.data);
      setTrending(trendingRes.data.slice(0, 5));
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            Welcome back, {user?.name}! Here's your lead generation overview.
          </p>
        </div>
        <div className="header-actions">
          <div className="user-tier">
            {user?.tier === 'free' && <Crown size={16} />}
            <span>{user?.tier?.toUpperCase()} Plan</span>
          </div>
          <NavLink to="/discover" className="btn btn-primary">
            <PlusCircle size={18} />
            Discover New Leads
          </NavLink>
        </div>
      </div>

      <div className="usage-warning">
        {user?.tier === 'free' && (
          <div className="usage-bar">
            <div className="usage-info">
              <span>Monthly Usage: {user.leads_discovered || 0} / {user.monthly_limit || 50} leads</span>
              <span className="usage-percentage">
                {Math.round(((user.leads_discovered || 0) / (user.monthly_limit || 50)) * 100)}%
              </span>
            </div>
            <div className="usage-progress">
              <div 
                className="usage-fill" 
                style={{ width: `${Math.min(100, ((user.leads_discovered || 0) / (user.monthly_limit || 50)) * 100)}%` }}
              ></div>
            </div>
            {(user.leads_discovered || 0) > (user.monthly_limit || 50) * 0.8 && (
              <p className="usage-warning-text">
                <AlertCircle size={16} />
                You're approaching your monthly limit. Upgrade to Pro for unlimited access.
              </p>
            )}
          </div>
        )}
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon leads">
            <Users />
          </div>
          <div className="stat-value">{analytics?.total_leads || 0}</div>
          <div className="stat-label">Total Leads</div>
          <div className="stat-meta">
            {analytics?.user_stats?.real_api_leads || 0} from real APIs
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon platforms">
            <Target />
          </div>
          <div className="stat-value">{analytics?.platform_distribution?.length || 0}</div>
          <div className="stat-label">Active Platforms</div>
          <div className="stat-change positive">
            <ArrowUp size={16} />
            Real API integration
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon engagement">
            <BarChart3 />
          </div>
          <div className="stat-value">{analytics?.average_metrics?.interest_score || 0}%</div>
          <div className="stat-label">Avg Interest Score</div>
          <div className="stat-change positive">
            <ArrowUp size={16} />
            AI-powered analysis
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon trending">
            <TrendingUp />
          </div>
          <div className="stat-value">{trending.length}</div>
          <div className="stat-label">Trending Topics</div>
          <div className="stat-change positive">
            <ArrowUp size={16} />
            Real-time detection
          </div>
        </div>
      </div>

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Recent Leads</h2>
          <NavLink to="/discover" className="btn btn-secondary">View All</NavLink>
        </div>
        
        <div className="leads-grid">
          {leads.map((lead) => (
            <LeadCard key={lead.id} lead={lead} />
          ))}
        </div>
        
        {leads.length === 0 && (
          <div className="empty-state">
            <h3>No leads discovered yet</h3>
            <p>Start discovering leads by analyzing social media platforms</p>
            <NavLink to="/discover" className="btn btn-primary">
              Discover Your First Leads
            </NavLink>
          </div>
        )}
      </div>

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Trending Topics</h2>
          <NavLink to="/trending" className="btn btn-secondary">Explore All</NavLink>
        </div>
        
        <ul className="trending-list">
          {trending.map((topic, index) => (
            <li key={index} className="trending-item">
              <div className="trending-info">
                <h4>{topic.topic}</h4>
                <p>{topic.platform} • {topic.post_count} posts</p>
              </div>
              <div className="trending-score">
                <div className="score-value">{topic.engagement_score.toFixed(1)}</div>
                <div className="score-label">Score</div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

// Lead Discovery Component
const LeadDiscovery = () => {
  const { user } = useAuth();
  const [keywords, setKeywords] = useState("");
  const [platforms, setPlatforms] = useState(["facebook", "instagram"]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDiscoverLeads = async () => {
    if (!keywords.trim()) return;
    
    try {
      setLoading(true);
      setError("");
      
      const response = await axios.post(`${API}/leads/discover`, {
        platforms: platforms,
        keywords: keywords.split(',').map(k => k.trim()),
        max_leads: user?.tier === 'free' ? 20 : 50,
        min_followers: 1000,
        days_back: 30
      }, {
        withCredentials: true
      });
      
      setLeads(response.data);
    } catch (error) {
      console.error('Failed to discover leads:', error);
      if (error.response?.status === 429) {
        setError("You've reached your monthly limit. Upgrade to Pro for unlimited lead discovery.");
      } else if (error.response?.status === 401) {
        setError("Authentication required. Please log in again.");
      } else {
        setError("Failed to discover leads. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const togglePlatform = (platform) => {
    setPlatforms(prev => 
      prev.includes(platform) 
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Discover Leads</h1>
          <p className="page-subtitle">Find potential customers interested in digital products</p>
        </div>
        <div className="usage-display">
          {user?.tier === 'free' && (
            <span className="usage-counter">
              {user.leads_discovered || 0} / {user.monthly_limit || 50} leads used
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Search Parameters</h2>
          {!user?.has_facebook_token && (
            <div className="connection-notice">
              <LinkIcon size={16} />
              Connect Facebook for real API data
            </div>
          )}
        </div>
        
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          <div>
            <label style={{ color: 'white', display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
              Keywords (comma separated)
            </label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="e.g., digital marketing, online course, saas tools"
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                background: 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                fontSize: '1rem'
              }}
            />
          </div>
          
          <div>
            <label style={{ color: 'white', display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
              Platforms
            </label>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              {['facebook', 'instagram', 'pinterest', 'tiktok'].map(platform => (
                <label key={platform} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'white' }}>
                  <input
                    type="checkbox"
                    checked={platforms.includes(platform)}
                    onChange={() => togglePlatform(platform)}
                    style={{ marginRight: '0.5rem' }}
                  />
                  <span style={{ textTransform: 'capitalize' }}>
                    {platform}
                    {platform === 'facebook' && user?.has_facebook_token && (
                      <CheckCircle size={16} style={{ marginLeft: '0.5rem', color: '#10ac84' }} />
                    )}
                    {platform === 'instagram' && user?.has_instagram_token && (
                      <CheckCircle size={16} style={{ marginLeft: '0.5rem', color: '#10ac84' }} />
                    )}
                  </span>
                </label>
              ))}
            </div>
          </div>
          
          <button 
            className="btn btn-primary" 
            onClick={handleDiscoverLeads}
            disabled={loading || !keywords.trim() || (user?.tier === 'free' && user?.leads_discovered >= user?.monthly_limit)}
            style={{ alignSelf: 'start' }}
          >
            {loading ? (
              <>
                <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                Analyzing with AI...
              </>
            ) : (
              <>
                <Search size={18} />
                Discover Leads
              </>
            )}
          </button>
        </div>
      </div>

      {leads.length > 0 && (
        <div className="content-section">
          <div className="section-header">
            <h2 className="section-title">Discovered Leads ({leads.length})</h2>
            <div className="lead-stats">
              <span className="real-data-count">
                {leads.filter(l => l.real_data).length} from real APIs
              </span>
            </div>
          </div>
          
          <div className="leads-grid">
            {leads.map((lead) => (
              <LeadCard key={lead.id} lead={lead} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Trending Topics Component (unchanged, but with auth)
const TrendingTopics = () => {
  const [trending, setTrending] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrendingTopics();
  }, [selectedPlatform]);

  const fetchTrendingTopics = async () => {
    try {
      setLoading(true);
      const url = selectedPlatform 
        ? `${API}/trending?platform=${selectedPlatform}`
        : `${API}/trending`;
      const response = await axios.get(url, { withCredentials: true });
      setTrending(response.data);
    } catch (error) {
      console.error('Failed to fetch trending topics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Trending Topics</h1>
          <p className="page-subtitle">Viral content and emerging trends across platforms</p>
        </div>
      </div>

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Platform Filter</h2>
        </div>
        
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
          <button 
            className={`btn ${selectedPlatform === "" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setSelectedPlatform("")}
          >
            All Platforms
          </button>
          {['facebook', 'instagram', 'pinterest', 'tiktok'].map(platform => (
            <button
              key={platform}
              className={`btn ${selectedPlatform === platform ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setSelectedPlatform(platform)}
              style={{ textTransform: 'capitalize' }}
            >
              {platform}
            </button>
          ))}
        </div>
        
        {loading ? (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        ) : (
          <ul className="trending-list">
            {trending.map((topic, index) => (
              <li key={index} className="trending-item">
                <div className="trending-info">
                  <h4>{topic.topic}</h4>
                  <p>{topic.platform} • {topic.post_count} posts • +{topic.growth_rate.toFixed(1)}% growth</p>
                </div>
                <div className="trending-score">
                  <div className="score-value">{topic.engagement_score.toFixed(1)}</div>
                  <div className="score-label">Score</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

// Enhanced Lead Card Component
const LeadCard = ({ lead }) => {
  return (
    <div className="lead-card">
      <div className="lead-header">
        <div className="lead-user">
          <div className="user-avatar">
            {lead.username.charAt(0).toUpperCase()}
          </div>
          <div className="user-info">
            <h4>@{lead.username}</h4>
            <p>{lead.follower_count.toLocaleString()} followers</p>
          </div>
        </div>
        <div className="lead-badges">
          <span className={`platform-badge ${lead.platform}`}>
            {lead.platform}
          </span>
          {lead.real_data && (
            <span className="real-data-badge">
              <CheckCircle size={12} />
              Real API
            </span>
          )}
        </div>
      </div>
      
      <div className="lead-metrics">
        <div className="metric">
          <div className="metric-value">{Math.round(lead.interest_score)}</div>
          <div className="metric-label">Interest</div>
        </div>
        <div className="metric">
          <div className="metric-value">{Math.round(lead.viral_potential)}</div>
          <div className="metric-label">Viral</div>
        </div>
        <div className="metric">
          <div className="metric-value">{Math.round(lead.engagement_rate * 100)}%</div>
          <div className="metric-label">Engagement</div>
        </div>
      </div>
      
      <div className="interests-tags">
        {lead.interests.slice(0, 3).map((interest, index) => (
          <span key={index} className="interest-tag">
            {interest.replace('_', ' ')}
          </span>
        ))}
      </div>
      
      {lead.profile_url && (
        <a 
          href={lead.profile_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="btn btn-secondary"
          style={{ marginTop: '1rem', width: '100%', justifyContent: 'center' }}
        >
          <ExternalLink size={16} />
          View Profile
        </a>
      )}
    </div>
  );
};

// Enhanced Sidebar Component
const Sidebar = () => {
  const { user, logout } = useAuth();

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">
            <Zap />
          </div>
          Viral Leads
        </div>
      </div>
      
      {user && (
        <div className="user-info-sidebar">
          <div className="user-avatar-sidebar">
            {user.picture ? (
              <img src={user.picture} alt={user.name} />
            ) : (
              user.name.charAt(0).toUpperCase()
            )}
          </div>
          <div className="user-details">
            <div className="user-name">{user.name}</div>
            <div className="user-tier">{user.tier?.toUpperCase()} Plan</div>
          </div>
        </div>
      )}
      
      <nav>
        <ul className="nav-menu">
          <li className="nav-item">
            <NavLink to="/dashboard" className="nav-link">
              <BarChart3 size={20} />
              Dashboard
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/discover" className="nav-link">
              <Search size={20} />
              Discover Leads
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/trending" className="nav-link">
              <TrendingUp size={20} />
              Trending Topics
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/settings" className="nav-link">
              <Settings size={20} />
              Settings
            </NavLink>
          </li>
        </ul>
      </nav>
      
      <div className="sidebar-footer">
        <button className="btn btn-secondary logout-btn" onClick={logout}>
          <LogOut size={18} />
          Sign Out
        </button>
      </div>
    </div>
  );
};

// Settings Page Component
const SettingsPage = () => {
  const { user } = useAuth();
  const [connecting, setConnecting] = useState({});

  const connectPlatform = async (platform, token) => {
    try {
      setConnecting(prev => ({ ...prev, [platform]: true }));
      
      await axios.post(`${API}/platforms/connect`, {
        platform: platform,
        access_token: token
      }, {
        withCredentials: true
      });
      
      // Refresh user data
      window.location.reload();
    } catch (error) {
      console.error('Failed to connect platform:', error);
    } finally {
      setConnecting(prev => ({ ...prev, [platform]: false }));
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Manage your account and platform connections</p>
        </div>
      </div>

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Platform Connections</h2>
        </div>
        
        <div className="platform-connections">
          <div className="platform-connection-item">
            <div className="platform-info">
              <div className="platform-icon facebook-bg">
                <Target />
              </div>
              <div>
                <h4>Facebook</h4>
                <p>Connect your Facebook account to access real user posts and insights</p>
              </div>
            </div>
            <div className="connection-status">
              {user?.has_facebook_token ? (
                <span className="connected-badge">
                  <CheckCircle size={16} />
                  Connected
                </span>
              ) : (
                <button 
                  className="btn btn-primary"
                  disabled={connecting.facebook}
                >
                  {connecting.facebook ? (
                    <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  ) : (
                    <LinkIcon size={16} />
                  )}
                  Connect
                </button>
              )}
            </div>
          </div>

          <div className="platform-connection-item">
            <div className="platform-info">
              <div className="platform-icon instagram-bg">
                <Target />
              </div>
              <div>
                <h4>Instagram</h4>
                <p>Connect Instagram Business account for real post analysis and engagement metrics</p>
              </div>
            </div>
            <div className="connection-status">
              {user?.has_instagram_token ? (
                <span className="connected-badge">
                  <CheckCircle size={16} />
                  Connected
                </span>
              ) : (
                <button 
                  className="btn btn-primary"
                  onClick={() => window.open('https://developers.facebook.com/docs/instagram-basic-display-api/getting-started', '_blank')}
                >
                  <LinkIcon size={16} />
                  Connect Instagram
                </button>
              )}
            </div>
          </div>

          <div className="platform-connection-item">
            <div className="platform-info">
              <div className="platform-icon pinterest-bg">
                <Target />
              </div>
              <div>
                <h4>Pinterest</h4>
                <p>Connect Pinterest Business account for board analysis, pin engagement, and lead discovery</p>
              </div>
            </div>
            <div className="connection-status">
              {user?.has_pinterest_token ? (
                <span className="connected-badge">
                  <CheckCircle size={16} />
                  Connected (Mock)
                </span>
              ) : (
                <button 
                  className="btn btn-primary"
                  onClick={() => connectPlatform('pinterest')}
                  disabled={connecting.pinterest}
                >
                  {connecting.pinterest ? (
                    <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  ) : (
                    <LinkIcon size={16} />
                  )}
                  Connect Pinterest
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Subscription Plan</h2>
        </div>
        
        <div className="plan-info">
          <div className="current-plan">
            <div className="plan-header">
              <Crown size={24} />
              <div>
                <h3>{user?.tier?.toUpperCase()} Plan</h3>
                <p>
                  {user?.tier === 'free' 
                    ? `${user?.monthly_limit || 50} leads per month`
                    : 'Unlimited lead discovery'
                  }
                </p>
              </div>
            </div>
            
            {user?.tier === 'free' && (
              <div className="upgrade-section">
                <h4>Upgrade to Pro</h4>
                <ul className="upgrade-features">
                  <li><CheckCircle size={16} /> Unlimited lead discovery</li>
                  <li><CheckCircle size={16} /> Priority API access</li>
                  <li><CheckCircle size={16} /> Advanced analytics</li>
                  <li><CheckCircle size={16} /> Export capabilities</li>
                </ul>
                <button className="btn btn-primary">
                  Upgrade Now - $29/month
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <AuthProvider>
      <div className="app-container">
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPageWrapper />} />
            <Route path="/login" element={<LoginPage />} />
            
            {/* Protected routes */}
            <Route path="/dashboard" element={<ProtectedRoute><DashboardLayout><Dashboard /></DashboardLayout></ProtectedRoute>} />
            <Route path="/discover" element={<ProtectedRoute><DashboardLayout><LeadDiscovery /></DashboardLayout></ProtectedRoute>} />
            <Route path="/trending" element={<ProtectedRoute><DashboardLayout><TrendingTopics /></DashboardLayout></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><DashboardLayout><SettingsPage /></DashboardLayout></ProtectedRoute>} />
          </Routes>
        </BrowserRouter>
      </div>
    </AuthProvider>
  );
}

// Landing Page Wrapper
const LandingPageWrapper = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <LandingPage />;
};

// Dashboard Layout
const DashboardLayout = ({ children }) => {
  return (
    <div className="dashboard-layout">
      <Sidebar />
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

export default App;