import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client.js";
import { useAuth } from "../auth/useAuth.jsx";

export function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await api.post("/api/auth/login", { email, password });
      login(res.data.access_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container">
      <h2>Login</h2>
      <div className="card">
        <form onSubmit={onSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label>Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          </div>
          <button className="primary" disabled={submitting} type="submit">
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {error ? <div className="error">{error}</div> : null}
        <div className="muted" style={{ marginTop: 14 }}>
          New here? <a href="/signup">Create account</a>
        </div>
      </div>
    </div>
  );
}

