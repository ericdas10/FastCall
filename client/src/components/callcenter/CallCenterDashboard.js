import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { callCenterAPI, messagingAPI } from '../../services/api';
import { 
  UsersIcon, 
  ChatBubbleLeftRightIcon, 
  DocumentArrowUpIcon,
  ArrowRightOnRectangleIcon,
  UserIcon
} from '@heroicons/react/24/outline';

const CallCenterDashboard = () => {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [conversation, setConversation] = useState([]);
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
    fetchUsers();
  }, [user, navigate]);

  useEffect(() => {
    if (selectedUser) {
      fetchConversation(selectedUser.id);
    }
  }, [selectedUser]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await callCenterAPI.getUsers();
      console.log('Users response:', response);
      setUsers(response.users || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchConversation = async (userId) => {
    try {
      const response = await callCenterAPI.getConversation(userId);
      console.log('Conversation response:', response);
      setConversation(response || []);
    } catch (error) {
      console.error('Failed to fetch conversation:', error);
      setConversation([]);
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
            <div className="flex-1 flex space-x-6">
              {/* Users List */}
              <div className="w-1/3 border-r border-secondary-200 pr-6">
                <h2 className="text-lg font-semibold text-secondary-800 mb-4">Users</h2>
                {loading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                  </div>
                ) : users.length === 0 ? (
                  <div className="text-center text-secondary-500 mt-8">
                    <UserIcon className="h-12 w-12 mx-auto mb-4 text-secondary-300" />
                    <p>No users found</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {users.map((userItem) => (
                      <button
                        key={userItem.id}
                        onClick={() => setSelectedUser(userItem)}
                        className={`w-full text-left p-3 rounded-lg transition-all duration-200 ${
                          selectedUser?.id === userItem.id
                            ? 'bg-primary-100 border border-primary-300'
                            : 'bg-white hover:bg-secondary-50 border border-secondary-200'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center text-white font-semibold">
                            {userItem.name.charAt(0).toUpperCase()}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium text-secondary-800">{userItem.name}</p>
                            <p className="text-sm text-secondary-500">{userItem.email}</p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Conversation View */}
              <div className="flex-1 flex flex-col">
                {selectedUser ? (
                  <>
                    <div className="mb-4">
                      <h3 className="text-lg font-semibold text-secondary-800">
                        Conversation with {selectedUser.name}
                      </h3>
                      <p className="text-sm text-secondary-500">{selectedUser.email}</p>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-4">
                      {conversation.length === 0 ? (
                        <div className="text-center text-secondary-500 mt-8">
                          <ChatBubbleLeftRightIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
                          <p>No conversation yet</p>
                        </div>
                      ) : (
                        conversation.map((message, index) => (
                          <div
                            key={index}
                            className={`flex ${message.sender_type === 'user' ? 'justify-end' : 'justify-start'}`}
                          >
                            <div className={`max-w-xs lg:max-w-md ${message.sender_type === 'user' ? 'order-2' : 'order-1'}`}>
                              <div className={`${message.sender_type === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}`}>
                                <p className="text-sm">{message.content}</p>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center text-secondary-500">
                      <UsersIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
                      <p className="text-lg">Select a user to view conversation</p>
                    </div>
                  </div>
                )}
              </div>
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
