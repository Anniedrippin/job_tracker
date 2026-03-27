import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import { api } from "../api/client.js";

const AuthContext = createContext(null);

function readToken() {
  try {
    return localStorage.getItem("sj_token");
  } catch {
    return null;
  }
}

function writeToken(token) {
  localStorage.setItem("sj_token", token);
}

function clearToken() {
  localStorage.removeItem("sj_token");
}

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => readToken());
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(false);

  const value = useMemo(
    () => ({
      accessToken,
      user,
      loadingUser,

      login: async (token) => {
        writeToken(token);
        setAccessToken(token);
      },

      logout: () => {
        clearToken();
        setAccessToken(null);
        setUser(null);
      },

      refreshUser: async () => {
        if (!accessToken) return;

        setLoadingUser(true);
        try {
          const res = await api.get("/api/users/me");
          setUser(res.data);
        } catch (err) {
          // Token invalid/expired
          clearToken();
          setAccessToken(null);
          setUser(null);
        } finally {
          setLoadingUser(false);
        }
      },
    }),
    [accessToken, user]
  );

  useEffect(() => {
    if (!accessToken) return;

    value.refreshUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}