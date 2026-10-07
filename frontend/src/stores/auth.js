// Auth store: holds tokens + current user, and the login/refresh/logout logic.
// Tokens persist in localStorage so a page refresh keeps you signed in.

import { defineStore } from 'pinia'
import { api, setAccessToken, setRefreshHandler } from '../api'

const ACCESS_KEY = 'rtp_access'
const REFRESH_KEY = 'rtp_refresh'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem(ACCESS_KEY) || null,
    refreshToken: localStorage.getItem(REFRESH_KEY) || null,
    user: null,
  }),
  getters: {
    isAuthenticated: (s) => !!s.accessToken,
  },
  actions: {
    _persist() {
      if (this.accessToken) localStorage.setItem(ACCESS_KEY, this.accessToken)
      else localStorage.removeItem(ACCESS_KEY)
      if (this.refreshToken) localStorage.setItem(REFRESH_KEY, this.refreshToken)
      else localStorage.removeItem(REFRESH_KEY)
      setAccessToken(this.accessToken)
    },

    async login(username, password) {
      const tokens = await api('/auth/login', {
        method: 'POST',
        auth: false,
        body: { username, password },
      })
      this.accessToken = tokens.access_token
      this.refreshToken = tokens.refresh_token
      this._persist()
      await this.fetchMe()
    },

    async fetchMe() {
      this.user = await api('/auth/me')
      return this.user
    },

    async changePassword(currentPassword, newPassword) {
      await api('/auth/change-password', {
        method: 'POST',
        body: { current_password: currentPassword, new_password: newPassword },
      })
      if (this.user) this.user.must_change_password = false
    },

    // Exchanges the refresh token for a new access token. Returns true on
    // success; on failure the session is cleared and false is returned.
    async refresh() {
      if (!this.refreshToken) return false
      try {
        const res = await api('/auth/refresh', {
          method: 'POST', auth: false, body: { refresh_token: this.refreshToken },
        })
        this.accessToken = res.access_token
        this._persist()
        return true
      } catch {
        this.logout()
        return false
      }
    },

    logout() {
      this.accessToken = null
      this.refreshToken = null
      this.user = null
      this._persist()
    },

    // Called once on app start to wire the stored token into the api client
    // and confirm it's still valid.
    async init() {
      setAccessToken(this.accessToken)
      setRefreshHandler(() => this.refresh())
      if (this.accessToken) {
        try {
          await this.fetchMe()
        } catch {
          this.logout()
        }
      }
    },
  },
})
