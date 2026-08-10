import axios from 'axios';
import { useAuthStore } from '../store/auth';

const _envUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const API_BASE_URL = _envUrl.endsWith('/api') ? _envUrl : `${_envUrl}/api`;

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,  // Required: sends the HttpOnly refresh_token cookie on every request
});

// ── Request interceptor: attach access token ──────────────────────────────────
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: silent token refresh on 401 ────────────────────────
let _isRefreshing = false;
let _pendingRequests: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config;
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/refresh') || 
                           originalRequest?.url?.includes('/auth/login') || 
                           originalRequest?.url?.includes('/auth/logout');

    // Only attempt refresh for 401s on non-auth endpoints that haven't been retried yet
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      // If a refresh is already in progress, queue this request
      if (_isRefreshing) {
        return new Promise((resolve) => {
          _pendingRequests.push((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(api(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      _isRefreshing = true;

      try {
        // Attempt silent refresh using HttpOnly cookie
        const res = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const newToken: string = res.data.access_token;

        // Update Zustand store
        useAuthStore.getState().setToken(newToken);

        // Flush pending requests
        _pendingRequests.forEach((cb) => cb(newToken));
        _pendingRequests = [];

        // Retry the original request
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch {
        // Refresh also failed — full logout
        _pendingRequests = [];
        useAuthStore.getState().logout();
        return Promise.reject(error);
      } finally {
        _isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ── API method groups ─────────────────────────────────────────────────────────

export const authApi = {
  login: async (username: string, password: string) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    const res = await api.post('/auth/login', formData);
    return res.data;
  },
  me: async () => {
    const res = await api.get('/users/me');
    return res.data;
  },
  refresh: async (): Promise<string> => {
    // Uses the HttpOnly cookie automatically (withCredentials: true)
    const res = await axios.post(
      `${API_BASE_URL}/auth/refresh`,
      {},
      { withCredentials: true }
    );
    return res.data.access_token;
  },
  logout: async () => {
    // Server revokes session and clears cookie
    await api.post('/auth/logout');
  },
};

export const usersApi = {
  getAll: async () => {
    const { data } = await api.get('/users');
    return data;
  },
  create: async (userData: any) => {
    const { data } = await api.post('/users/add', userData);
    return data;
  },
  update: async (userId: string, userData: any) => {
    const { data } = await api.put(`/users/${userId}`, userData);
    return data;
  },
  delete: async (userId: string) => {
    const { data } = await api.delete(`/users/${userId}`);
    return data;
  },
  changePassword: async (currentPassword: string, newPassword: string) => {
    const { data } = await api.post('/users/me/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return data;
  },
  adminSetPassword: async (userId: string, newPassword: string) => {
    const { data } = await api.post(`/users/${userId}/set-password`, {
      new_password: newPassword,
    });
    return data;
  },
};

export const datasetsApi = {
  getAll: async () => {
    const res = await api.get('/datasets/');
    return res.data;
  },
  delete: async (id: string) => {
    const res = await api.delete(`/datasets/${id}`);
    return res.data;
  },
  upload: async (formData: FormData) => {
    const res = await api.post('/datasets/upload', formData);
    return res.data;
  }
};

export const audioApi = {
  getAll: async (skip = 0, limit = 100) => {
    const res = await api.get(`/audio/?skip=${skip}&limit=${limit}`);
    return res.data;
  },
  getById: async (id: string) => {
    const res = await api.get(`/audio/${id}`);
    return res.data;
  },
  startTask: async (id: string) => {
    const res = await api.patch(`/audio/${id}/start`);
    return res.data;
  },
  updateStatus: async (id: string, status: string) => {
    const res = await api.patch(`/audio/${id}/status`, { status });
    return res.data;
  },
};

export const annotationsApi = {
  getPending: async () => {
    const res = await api.get('/annotations/pending');
    return res.data;
  },
  getByAudio: async (audioId: string) => {
    try {
      const res = await api.get(`/annotations/audio/${audioId}`);
      return res.data;
    } catch (e: any) {
      if (e.response?.status === 404) return null;
      throw e;
    }
  },
  save: async (payload: { audio_id: string; transcript: string; time_taken?: number }) => {
    const res = await api.post('/annotations/', payload);
    return res.data;
  },
  getVersions: async (audioId: string) => {
    const res = await api.get(`/annotations/${audioId}/versions`);
    return res.data;
  },
  restoreVersion: async (audioId: string, versionId: string) => {
    const res = await api.post(`/annotations/${audioId}/restore/${versionId}`);
    return res.data;
  },
  processRsml: async (transcript: string) => {
    const res = await api.post('/annotations/process-rsml', { transcript });
    return res.data;
  },
  submit: async (audioId: string) => {
    const res = await api.post(`/annotations/${audioId}/submit`);
    return res.data;
  }
};

export const analyticsApi = {
  getGlobal: async () => {
    const res = await api.get('/analytics/global');
    return res.data;
  },
  getFunnel: async () => {
    const res = await api.get('/analytics/funnel');
    return res.data;
  },
  getTrend: async (days = 30) => {
    const res = await api.get(`/analytics/trend?days=${days}`);
    return res.data;
  },
  getDatasets: async () => {
    const res = await api.get('/analytics/datasets');
    return res.data;
  },
  getLanguages: async () => {
    const res = await api.get('/analytics/languages');
    return res.data;
  },
  getAnnotatorLeaderboard: async () => {
    const res = await api.get('/analytics/leaderboard/annotators');
    return res.data;
  },
  getReviewerLeaderboard: async () => {
    const res = await api.get('/analytics/leaderboard/reviewers');
    return res.data;
  },
  getUserDetail: async (userId: string) => {
    const res = await api.get(`/analytics/users/${userId}`);
    return res.data;
  },
};

export const queueApi = {
  getStats: async () => {
    const res = await api.get('/queue/stats');
    return res.data;
  },
  assign: async (language: string) => {
    const res = await api.post('/queue/assign', { language });
    return res.data;
  },
  getMyTasks: async () => {
    const res = await api.get('/queue/my-tasks');
    return res.data;
  },
  heartbeat: async (audioId: string) => {
    const res = await api.post(`/queue/heartbeat/${audioId}`);
    return res.data;
  },
};
