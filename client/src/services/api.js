import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

console.log('API Base URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log('API Request:', config.method?.toUpperCase(), config.url, config.data);
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url, response.data);
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.status, error.config?.url, error.response?.data);
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: async (credentials) => {
    const response = await api.post('/auth/login', {
      username_or_email: credentials.username,
      password: credentials.password
    });
    return response.data;
  },
  
  register: async (userData) => {
    console.log('Registration data received:', userData);
    
    if (userData.user_type === 'call_center') {
      // Only send call center specific fields
      const requestData = {
        name: userData.name,
        username: userData.username,
        password: userData.password,
        email: userData.email,
        domain: userData.domain,
        country: userData.country,
        number: userData.number
      };
      console.log('Call center registration request:', requestData);
      
      const response = await api.post('/auth/register/call-center', requestData);
      return response.data;
    } else {
      // Only send client specific fields
      const callCenterId = parseInt(userData.call_center_id);
      if (isNaN(callCenterId)) {
        throw new Error('Invalid call center ID');
      }
      
      const requestData = {
        call_center_id: callCenterId,
        first_name: userData.name.split(' ')[0] || userData.name,
        last_name: userData.name.split(' ')[1] || 'User',
        username: userData.username,
        password: userData.password,
        email: userData.email,
        country: userData.country,
        number: userData.number
      };
      console.log('Client registration request:', requestData);
      
      const response = await api.post('/auth/register/client', requestData);
      return response.data;
    }
  },

  getCallCenters: async () => {
    const response = await api.get('/auth/call-centers');
    return response.data;
  }
};

export const messagingAPI = {
  sendMessage: async (message) => {
    const response = await api.post('/messages', {
      text: message.message
    });
    return response.data;
  },

  getConversation: async (userId) => {
    // Use the new client conversation endpoint
    const response = await api.get('/messages/me/conversation');
    return response.data;
  }
};

export const callCenterAPI = {
  getUsers: async (callCenterId) => {
    const response = await api.get(`/call-centers/me/clients`);
    // Transform the response to match frontend expectations
    return {
      users: response.data.map(client => ({
        id: client.client_id,
        name: `${client.first_name} ${client.last_name}`,
        email: client.email,
        username: client.username
      }))
    };
  },
  
  getConversation: async (userId) => {
    const response = await api.get(`/call-centers/me/clients/${userId}/messages`);
    console.log('Raw conversation response:', response.data);
    return response.data;
  },
  
  uploadPDF: async (formData) => {
    const response = await api.post('/call-center/upload-pdf', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }
};

export default api;
