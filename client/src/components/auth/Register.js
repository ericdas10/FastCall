import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { authAPI } from '../../services/api';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

const Register = () => {
  const [formData, setFormData] = useState({
    username: '',
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    call_center_id: '',
    domain: 'technology',
    country: 'RO',
    number: '+4000000000',
    description: '',
    knowledge_base_path: '',
    database_uri: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [userType, setUserType] = useState('client');
  const [callCenters, setCallCenters] = useState([]);
  
  const domainOptions = [
    { value: 'finance', label: 'Finance' },
    { value: 'healthcare', label: 'Healthcare' },
    { value: 'retail', label: 'Retail' },
    { value: 'technology', label: 'Technology' },
    { value: 'telecom', label: 'Telecom' }
  ];

  const countryOptions = [
    { value: 'RO', label: 'Romania' },
    { value: 'US', label: 'United States' },
    { value: 'GB', label: 'United Kingdom' },
    { value: 'DE', label: 'Germany' },
    { value: 'FR', label: 'France' }
  ];

  const { register, loading, error } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (userType === 'client') {
      fetchCallCenters();
    }
  }, [userType]);

  const fetchCallCenters = async () => {
    try {
      console.log('Fetching call centers...');
      const response = await authAPI.getCallCenters();
      console.log('Call centers response:', response);
      setCallCenters(response);
    } catch (error) {
      console.error('Failed to fetch call centers:', error);
      console.error('Error details:', error.response?.data);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match');
      return;
    }

    // Validate required fields based on user type
    if (userType === 'call_center') {
      if (!formData.email || !formData.domain || !formData.country || !formData.number) {
        alert('Please fill in all required fields');
        return;
      }
    } else {
      if (!formData.call_center_id) {
        alert('Please select a call center');
        return;
      }
    }

    // Only send the fields that are needed for each user type
    const submitData = {
      name: formData.name,
      username: formData.username,
      password: formData.password,
      user_type: userType,
      email: formData.email,
      domain: formData.domain,
      country: formData.country,
      number: formData.number,
      description: formData.description,
      knowledge_base_path: formData.knowledge_base_path,
      database_uri: formData.database_uri,
    };

    if (userType === 'client') {
      submitData.call_center_id = parseInt(formData.call_center_id);
      if (isNaN(submitData.call_center_id)) {
        alert('Please select a call center');
        return;
      }
    }

    console.log('Submitting registration data:', submitData);

    try {
      await register(submitData);
      navigate('/login');
    } catch (error) {
      console.error('Registration failed:', error.response?.data);
      alert(`Registration failed: ${error.response?.data?.detail || 'Unknown error'}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-secondary-50 flex items-center justify-center p-4">
      <div className="glass-effect rounded-2xl p-8 w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-secondary-800 mb-2">FastCall</h1>
          <p className="text-secondary-600">Create your account</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex space-x-4 mb-6">
            <button
              type="button"
              onClick={() => setUserType('client')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all duration-200 ${
                userType === 'client'
                  ? 'bg-primary-600 text-white'
                  : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
              }`}
            >
              Client
            </button>
            <button
              type="button"
              onClick={() => setUserType('call_center')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all duration-200 ${
                userType === 'call_center'
                  ? 'bg-primary-600 text-white'
                  : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
              }`}
            >
              Call Center
            </button>
          </div>

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-secondary-700 mb-2">
              Username
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className="input-field"
              placeholder="Enter your username"
              required
            />
          </div>

          <div>
            <label htmlFor="name" className="block text-sm font-medium text-secondary-700 mb-2">
              Full Name
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              className="input-field"
              placeholder="Enter your full name"
              required
            />
          </div>

          {userType === 'client' && (
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-secondary-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="input-field"
                placeholder="Enter your email"
                required
              />
            </div>
          )}

          {userType === 'call_center' && (
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-secondary-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="input-field"
                placeholder="Enter your email"
                required
              />
            </div>
          )}

          {userType === 'client' && (
            <div>
              <label htmlFor="call_center_id" className="block text-sm font-medium text-secondary-700 mb-2">
                Call Center
              </label>
              <select
                id="call_center_id"
                name="call_center_id"
                value={formData.call_center_id}
                onChange={handleChange}
                className="input-field"
                required
              >
                <option value="">Select a call center</option>
                {callCenters.map((center) => (
                  <option key={center.id} value={center.id}>
                    {center.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {userType === 'call_center' && (
            <>
              <div>
                <label htmlFor="domain" className="block text-sm font-medium text-secondary-700 mb-2">
                  Domain
                </label>
                <select
                  id="domain"
                  name="domain"
                  value={formData.domain}
                  onChange={handleChange}
                  className="input-field"
                  required
                >
                  {domainOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="country" className="block text-sm font-medium text-secondary-700 mb-2">
                  Country
                </label>
                <select
                  id="country"
                  name="country"
                  value={formData.country}
                  onChange={handleChange}
                  className="input-field"
                  required
                >
                  {countryOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="number" className="block text-sm font-medium text-secondary-700 mb-2">
                  Phone Number
                </label>
                <input
                  type="tel"
                  id="number"
                  name="number"
                  value={formData.number}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="Enter phone number"
                  required
                />
              </div>
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-secondary-700 mb-2">
                  Description
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="Tell us about this call center..."
                  rows={4}
                />
              </div>

              <div>
                <label htmlFor="knowledge_base_path" className="block text-sm font-medium text-secondary-700 mb-2">
                  Knowledge base path
                </label>
                <input
                  type="text"
                  id="knowledge_base_path"
                  name="knowledge_base_path"
                  value={formData.knowledge_base_path}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="e.g. /data/cc_42/docs"
                />
              </div>

              <div>
                <label htmlFor="database_uri" className="block text-sm font-medium text-secondary-700 mb-2">
                  Database URI
                </label>
                <input
                  type="text"
                  id="database_uri"
                  name="database_uri"
                  value={formData.database_uri}
                  onChange={handleChange}
                  className="input-field"
                  placeholder="postgresql://user:pass@host:5432/db"
                />
              </div>
            </>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-secondary-700 mb-2">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="input-field pr-10"
                placeholder="Enter your password"
                required
                minLength="6"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-secondary-400 hover:text-secondary-600"
              >
                {showPassword ? (
                  <EyeSlashIcon className="h-5 w-5" />
                ) : (
                  <EyeIcon className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-secondary-700 mb-2">
              Confirm Password
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                className="input-field pr-10"
                placeholder="Confirm your password"
                required
                minLength="6"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-secondary-400 hover:text-secondary-600"
              >
                {showConfirmPassword ? (
                  <EyeSlashIcon className="h-5 w-5" />
                ) : (
                  <EyeIcon className="h-5 w-5" />
                )}
              </button>
            </div>
            {formData.confirmPassword && formData.password !== formData.confirmPassword && (
              <p className="text-red-500 text-sm mt-1">Passwords do not match</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || (formData.password !== formData.confirmPassword)}
            className="btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Creating account...
              </span>
            ) : (
              'Sign Up'
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-secondary-600">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
