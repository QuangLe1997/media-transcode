import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Upload from './components/Upload';
import Results from './components/Results';
import TaskDetails from './components/TaskDetails';

function Navigation() {
  const location = useLocation();
  
  return (
    <div className="header">
      <h1>🎬 Media Transcoding Service</h1>
      <p style={{ 
        margin: '8px 0 0 0', 
        fontSize: '0.9rem', 
        opacity: 0.8,
        textAlign: 'center'
      }}>
        Transform your media with professional transcoding and AI-powered face detection
      </p>
      <nav className="nav">
        <Link 
          to="/upload" 
          className={`nav-link ${location.pathname === '/upload' ? 'active' : ''}`}
        >
          📤 Upload
        </Link>
        <Link 
          to="/results" 
          className={`nav-link ${location.pathname === '/results' ? 'active' : ''}`}
        >
          📊 Results
        </Link>
      </nav>
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="container">
        <Navigation />
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/results" element={<Results />} />
          <Route path="/task/:taskId" element={<TaskDetails />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;