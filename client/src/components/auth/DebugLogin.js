import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';

const DebugLogin = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [userType, setUserType] = useState('client');
  const [debugInfo, setDebugInfo] = useState('');
  
  const { login, loading, error } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setDebugInfo('Attempting login...');
    
    const credentials = { username, password, user_type: userType };
    console.log('Login credentials:', credentials);
    
    try {
      console.log('Sending login request...');
      const result = await login(credentials);
      console.log('Login result:', result);
      setDebugInfo(`Login successful: ${JSON.stringify(result, null, 2)}`);
    } catch (error) {
      console.error('Login error:', error);
      console.error('Error response:', error.response);
      console.error('Error status:', error.response?.status);
      console.error('Error data:', error.response?.data);
      setDebugInfo(`Login failed: ${error.response?.status} - ${JSON.stringify(error.response?.data, null, 2)}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6">Debug Login</h1>
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex space-x-4 mb-4">
            <button
              type="button"
              onClick={() => setUserType('client')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium ${
                userType === 'client' ? 'bg-blue-600 text-white' : 'bg-gray-200'
              }`}
            >
              Client
            </button>
            <button
              type="button"
              onClick={() => setUserType('call_center')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium ${
                userType === 'call_center' ? 'bg-blue-600 text-white' : 'bg-gray-200'
              }`}
            >
              Call Center
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="Enter username"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="Enter password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg disabled:opacity-50"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        {debugInfo && (
          <div className="mt-6 p-4 bg-gray-100 rounded-lg">
            <h3 className="font-semibold mb-2">Debug Info:</h3>
            <pre className="text-xs overflow-auto">{debugInfo}</pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default DebugLogin;
