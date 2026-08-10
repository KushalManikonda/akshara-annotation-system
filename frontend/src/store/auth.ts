// frontend/src/store/auth.ts
//
// Global auth state using Zustand.
//
// Token strategy:
//   - access_token  → stored in Zustand memory (lost on page refresh, intentional)
//   - refresh_token → lives in an HttpOnly cookie managed by the server
//
// On page refresh, `restoreSession()` is called from App.tsx.
// It calls /auth/refresh using the cookie, then /users/me to restore state.

import { create } from 'zustand';
import type { User } from '../types';
import { authApi } from '../services/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isRestoringSession: boolean;  // True while the startup session check runs
  error: string | null;

  // Actions
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
  setToken: (token: string) => void;   // Used by the 401 interceptor
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, _get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  isRestoringSession: true,  // Start true so App shows a spinner before checking
  error: null,

  setToken: (token) => set({ token }),

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      // 1. Exchange credentials for access token (refresh token set as HttpOnly cookie by server)
      const res = await authApi.login(username, password);
      const token = res.access_token;
      set({ token });

      // 2. Fetch user profile
      const user = await authApi.me();
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err: any) {
      const message =
        err.response?.data?.detail || 'Login failed. Please check your credentials.';
      set({ error: message, isLoading: false, isAuthenticated: false, token: null });
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      // Tell the server to revoke the session and clear the cookie
      await authApi.logout();
    } catch {
      // Even if the server call fails, clear client state
    } finally {
      set({ user: null, token: null, isAuthenticated: false, isLoading: false, error: null });
    }
  },

  restoreSession: async () => {
    set({ isRestoringSession: true });
    try {
      const timeout = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Session restore timeout')), 3000)
      );

      const sessionTask = (async () => {
        const newToken = await authApi.refresh();
        set({ token: newToken });
        const user = await authApi.me();
        set({ user, isAuthenticated: true });
      })();

      await Promise.race([sessionTask, timeout]);
    } catch {
      // No valid session or timeout — stay logged out (normal for first visit / expired cookie)
      set({ user: null, token: null, isAuthenticated: false });
    } finally {
      set({ isRestoringSession: false });
    }
  },

  clearError: () => set({ error: null }),
}));

