import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import DebugLogin from './components/auth/DebugLogin';
import ClientDashboard from './components/client/ClientDashboard';
import CallCenterDashboard from './components/callcenter/CallCenterDashboard';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/debug-login" element={<DebugLogin />} />
            <Route path="/register" element={<Register />} />
            <Route path="/client" element={<ClientDashboard />} />
            <Route path="/call-center" element={<CallCenterDashboard />} />
            <Route path="/" element={<Navigate to="/login" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
