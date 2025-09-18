import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
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
  PlusCircle
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Dashboard Component
const Dashboard = () => {
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
        axios.get(`${API}/analytics`),
        axios.get(`${API}/leads?limit=6`),
        axios.get(`${API}/trending`)
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
          <p className="page-subtitle">AI-powered social media lead generation insights</p>
        </div>
        <button className="btn btn-primary">
          <PlusCircle size={18} />
          Discover New Leads
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon leads">
            <Users />
          </div>
          <div className="stat-value">{analytics?.total_leads || 0}</div>
          <div className="stat-label">Total Leads</div>
          <div className="stat-change positive">
            <ArrowUp size={16} />
            +12% this week
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
            +2 new sources
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
            +8.5% improvement
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
            +15 new trends
          </div>
        </div>
      </div>

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Recent Leads</h2>
          <button className="btn btn-secondary">View All</button>
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
          </div>
        )}
      </div>

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Trending Topics</h2>
          <button className="btn btn-secondary">Explore All</button>
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
  const [keywords, setKeywords] = useState("");
  const [platforms, setPlatforms] = useState(["facebook", "instagram"]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleDiscoverLeads = async () => {
    if (!keywords.trim()) return;
    
    try {
      setLoading(true);
      const response = await axios.post(`${API}/leads/discover`, {
        platforms: platforms,
        keywords: keywords.split(',').map(k => k.trim()),
        max_leads: 50,
        min_followers: 1000,
        days_back: 30
      });
      
      setLeads(response.data);
    } catch (error) {
      console.error('Failed to discover leads:', error);
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
      </div>

      <div className="content-section">
        <div className="section-header">
          <h2 className="section-title">Search Parameters</h2>
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
                  <span style={{ textTransform: 'capitalize' }}>{platform}</span>
                </label>
              ))}
            </div>
          </div>
          
          <button 
            className="btn btn-primary" 
            onClick={handleDiscoverLeads}
            disabled={loading || !keywords.trim()}
            style={{ alignSelf: 'start' }}
          >
            {loading ? (
              <>
                <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                Discovering...
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

// Trending Topics Component
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
      const response = await axios.get(url);
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
        
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
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

// Lead Card Component
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
        <span className={`platform-badge ${lead.platform}`}>
          {lead.platform}
        </span>
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

// Sidebar Component
const Sidebar = () => {
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
      
      <nav>
        <ul className="nav-menu">
          <li className="nav-item">
            <NavLink to="/" className="nav-link" end>
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
        </ul>
      </nav>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <div className="app-container">
      <BrowserRouter>
        <div className="dashboard-layout">
          <Sidebar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/discover" element={<LeadDiscovery />} />
              <Route path="/trending" element={<TrendingTopics />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </div>
  );
}

export default App;