// Auth store: holds tokens + current user, and the login/refresh/logout logic.
// Tokens persist in localStorage so a page refresh keeps you signed in, and so
// every open tab shares the same session (D12).

import { defineStore } from 'pinia'
import { api, setAccessToken, setRefreshHandler } from '../api'
import { resetActivity } from '../session'

const ACCESS_KEY = 'rtp_access'
const REFRESH_KEY = 'rtp_refresh'
const END_KEY = 'rtp_session_end'      // absolute end of the session (ms)
const IDLE_KEY = 'rtp_idle_ms'         // idle window (ms)
const RENEWED_KEY = 'rtp_renewed'      // last refresh, from any tab (ms)

const get = (k) => { try { return localStorage.getItem(k) } catch { return null } }
const set = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, String(v)) } catch { /* private mode */ } }

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: get(ACCESS_KEY) || null,
    refreshToken: get(REFRESH_KEY) || null,
    sessionEnd: Number(get(END_KEY)) || 0,
    idleMs: Number(get(IDLE_KEY)) || 15 * 60 * 1000,
    user: null,
  }),
  getters: {
    isAuthenticated: (s) => !!s.accessToken,
  },
  actions: {
    _persist() {
      set(ACCESS_KEY, this.accessToken)
      set(REFRESH_KEY, this.refreshToken)
      set(END_KEY, this.accessToken ? this.sessionEnd : null)
      set(IDLE_KEY, this.accessToken ? this.idleMs : null)
      setAccessToken(this.accessToken)
    },
    _take(tokens) {
      this.accessToken = tokens.access_token
      this.refreshToken = tokens.refresh_token
      this.sessionEnd = new Date(tokens.session_expires_at).getTime()
      this.idleMs = tokens.idle_timeout_seconds * 1000
      set(RENEWED_KEY, Date.now())
      this._persist()
    },
    // Another tab may have renewed (or ended) the session: pick up its tokens.
    syncFromStorage() {
      const access = get(ACCESS_KEY) || null
      if (access === this.accessToken) return
      this.accessToken = access
      this.refreshToken = get(REFRESH_KEY) || null
      this.sessionEnd = Number(get(END_KEY)) || 0
      setAccessToken(this.accessToken)
    },
    lastRenewed() { return Number(get(RENEWED_KEY)) || 0 },

    async login(username, password) {
      const tokens = await api('/auth/login', {
        method: 'POST',
        auth: false,
        body: { username, password },
      })
      resetActivity()
      this._take(tokens)
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

    // Renews the session (new tokens, idle window restarts; the 1 h end stays).
    // Returns true on success. A failure means the session is over; the
    // SessionGuard decides what the user sees, so nothing is cleared here.
    async refresh() {
      this.syncFromStorage()
      if (!this.refreshToken) return false
      try {
        this._take(await api('/auth/refresh', {
          method: 'POST', auth: false, body: { refresh_token: this.refreshToken },
        }))
        return true
      } catch {
        return false
      }
    },

    // Drops the tokens. keepUser leaves the page as it is (menus, role) while
    // the user signs in again to save their edits.
    logout({ keepUser = false } = {}) {
      this.accessToken = null
      this.refreshToken = null
      this.sessionEnd = 0
      if (!keepUser) this.user = null
      this._persist()
    },

    // Called once on app start to wire the stored token into the api client
    // and confirm it's still valid.
    async init() {
      setAccessToken(this.accessToken)
      setRefreshHandler(() => this.refresh())
      if (this.accessToken && this.sessionEnd && this.sessionEnd <= Date.now()) this.logout()
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
