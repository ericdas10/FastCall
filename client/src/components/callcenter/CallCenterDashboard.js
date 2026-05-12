import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { callCenterAPI } from '../../services/api';
import {
  UsersIcon,
  DocumentArrowUpIcon,
  ArrowRightOnRectangleIcon,
  UserIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

const CallCenterDashboard = () => {
  const [dashboard, setDashboard] = useState({ clients: [], totals: { success: 0, failure: 0, total: 0 } });
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState('users');

  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    fetchDashboard();
  }, [user, navigate]);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await callCenterAPI.getDashboard();
      setDashboard({
        clients: response?.clients || [],
        totals: response?.totals || { success: 0, failure: 0, total: 0 },
      });
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.includes('pdf')) {
      alert('Please select a PDF file');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploading(true);
      const response = await callCenterAPI.uploadPDF(formData);
      console.log('Upload response:', response);
      alert(`PDF uploaded successfully! File saved to: ${response.file_path}`);
      e.target.value = '';
    } catch (error) {
      console.error('Failed to upload PDF:', error);
      alert(`Failed to upload PDF: ${error.response?.data?.detail || 'Unknown error'}`);
    } finally {
      setUploading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      return new Date(timestamp).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch (e) {
      return '';
    }
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    try {
      return new Date(timestamp).toLocaleDateString();
    } catch (e) {
      return '';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-secondary-50">
      <div className="container mx-auto px-4 py-6 h-screen flex flex-col">
        {/* Header */}
        <div className="glass-effect rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <UsersIcon className="h-8 w-8 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-secondary-800">FastCall Admin</h1>
                <p className="text-secondary-600">Call Center Management</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="btn-secondary flex items-center space-x-2"
            >
              <ArrowRightOnRectangleIcon className="h-5 w-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 glass-effect rounded-xl p-6 flex flex-col">
          {/* Tabs */}
          <div className="flex space-x-1 mb-6 bg-secondary-100 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('users')}
              className={`flex-1 py-2 px-4 rounded-md font-medium transition-all duration-200 ${
                activeTab === 'users'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-secondary-600 hover:text-secondary-800'
              }`}
            >
              <UsersIcon className="h-5 w-5 inline mr-2" />
              Users
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex-1 py-2 px-4 rounded-md font-medium transition-all duration-200 ${
                activeTab === 'upload'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-secondary-600 hover:text-secondary-800'
              }`}
            >
              <DocumentArrowUpIcon className="h-5 w-5 inline mr-2" />
              Upload PDF
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'users' && (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Totals */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="rounded-xl border border-secondary-200 bg-white p-4 flex items-center space-x-3">
                  <ChartBarIcon className="h-8 w-8 text-primary-600" />
                  <div>
                    <p className="text-sm text-secondary-500">Total tickets</p>
                    <p className="text-2xl font-bold text-secondary-800">{dashboard.totals.total}</p>
                  </div>
                </div>
                <div className="rounded-xl border border-green-200 bg-green-50 p-4 flex items-center space-x-3">
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                  <div>
                    <p className="text-sm text-green-700">Successful</p>
                    <p className="text-2xl font-bold text-green-800">{dashboard.totals.success}</p>
                  </div>
                </div>
                <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-center space-x-3">
                  <XCircleIcon className="h-8 w-8 text-red-600" />
                  <div>
                    <p className="text-sm text-red-700">Failed</p>
                    <p className="text-2xl font-bold text-red-800">{dashboard.totals.failure}</p>
                  </div>
                </div>
              </div>

              <h2 className="text-lg font-semibold text-secondary-800 mb-3">Users</h2>

              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              ) : dashboard.clients.length === 0 ? (
                <div className="text-center text-secondary-500 mt-8">
                  <UserIcon className="h-12 w-12 mx-auto mb-4 text-secondary-300" />
                  <p>No users found</p>
                </div>
              ) : (
                <div className="overflow-y-auto">
                  <table className="w-full text-left">
                    <thead className="text-xs uppercase text-secondary-500 border-b border-secondary-200">
                      <tr>
                        <th className="py-2 pr-4">User</th>
                        <th className="py-2 pr-4">Email</th>
                        <th className="py-2 pr-4 text-center">Successful</th>
                        <th className="py-2 pr-4 text-center">Failed</th>
                        <th className="py-2 pr-4 text-center">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.clients.map((c) => (
                        <tr key={c.client_id} className="border-b border-secondary-100">
                          <td className="py-3 pr-4">
                            <div className="flex items-center space-x-3">
                              <div className="w-9 h-9 bg-primary-600 rounded-full flex items-center justify-center text-white font-semibold">
                                {(c.first_name || '?').charAt(0).toUpperCase()}
                              </div>
                              <div className="font-medium text-secondary-800">
                                {c.first_name} {c.last_name}
                              </div>
                            </div>
                          </td>
                          <td className="py-3 pr-4 text-sm text-secondary-600">{c.email}</td>
                          <td className="py-3 pr-4 text-center">
                            <span className="inline-flex items-center px-2 py-1 rounded-full bg-green-100 text-green-800 text-sm font-semibold">
                              {c.success_count}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-center">
                            <span className="inline-flex items-center px-2 py-1 rounded-full bg-red-100 text-red-800 text-sm font-semibold">
                              {c.failure_count}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-center font-semibold text-secondary-800">
                            {c.total_count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeTab === 'upload' && (
            <div className="flex-1 flex items-center justify-center">
              <div className="max-w-md w-full">
                <div className="text-center mb-8">
                  <DocumentArrowUpIcon className="h-16 w-16 mx-auto mb-4 text-primary-600" />
                  <h2 className="text-2xl font-bold text-secondary-800 mb-2">Upload PDF</h2>
                  <p className="text-secondary-600">Upload PDF documents to train the AI assistant</p>
                </div>

                <div className="border-2 border-dashed border-secondary-300 rounded-lg p-8 text-center hover:border-primary-400 transition-colors duration-200">
                  <input
                    type="file"
                    id="pdf-upload"
                    accept=".pdf"
                    onChange={handleFileUpload}
                    className="hidden"
                    disabled={uploading}
                  />
                  <label
                    htmlFor="pdf-upload"
                    className={`cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {uploading ? (
                      <div className="space-y-4">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
                        <p className="text-secondary-600">Uploading PDF...</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <DocumentArrowUpIcon className="h-12 w-12 mx-auto text-secondary-400" />
                        <div>
                          <p className="text-secondary-600">Click to upload or drag and drop</p>
                          <p className="text-sm text-secondary-500">PDF files only</p>
                        </div>
                      </div>
                    )}
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CallCenterDashboard;
