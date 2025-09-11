import axios from 'axios';

// API base URL - will be set by environment or default to current host
const API_BASE = process.env.REACT_APP_API_URL || 
  (window.location.hostname === 'localhost' 
    ? `${window.location.protocol}//${window.location.hostname}:8087`
    : '/api'); // Use nginx proxy when not localhost

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    // console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error(`API Error: ${error.response?.status} ${error.config?.url}`, error.response?.data);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Upload file
  uploadFile: async (file, preset = 'mobile_complete', deviceTypes = null, callbackUrl = null) => {
    const formData = new FormData();
    formData.append('video', file);
    formData.append('preset', preset);
    if (deviceTypes) formData.append('device_types', deviceTypes);
    if (callbackUrl) formData.append('callback_url', callbackUrl);

    const response = await api.post('/transcode/mobile', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Upload from URL
  uploadFromUrl: async (mediaUrl, profiles, callbackUrl = null) => {
    const response = await api.post('/transcode/url', {
      media_url: mediaUrl,
      config: { profiles },
      callback_url: callbackUrl,
    });
    return response.data;
  },

  // Get all tasks
  getTasks: async (status = null, limit = 50) => {
    const params = { limit };
    if (status) params.status = status;
    
    const response = await api.get('/tasks', { params });
    return response.data;
  },

  // Get single task
  getTask: async (taskId) => {
    const response = await api.get(`/task/${taskId}`);
    return response.data;
  },

  // Delete task
  deleteTask: async (taskId, deleteFiles = false, deleteFaces = false) => {
    const response = await api.delete(`/task/${taskId}`, {
      params: { 
        delete_files: deleteFiles,
        delete_faces: deleteFaces
      }
    });
    return response.data;
  },

  // Retry task
  retryTask: async (taskId, deleteFiles = false) => {
    const response = await api.post(`/task/${taskId}/retry`, {}, {
      params: { delete_files: deleteFiles }
    });
    return response.data;
  },

  // Get available profiles
  getProfiles: async () => {
    const response = await api.get('/profiles');
    return response.data;
  },

  // Health check
  health: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Get task result for copying/callback
  getTaskResult: async (taskId) => {
    const response = await api.get(`/task/${taskId}/result`);
    return response.data;
  },
};

export default api;