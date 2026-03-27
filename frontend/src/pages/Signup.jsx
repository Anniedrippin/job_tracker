import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client.js";
import { useAuth } from "../auth/useAuth.jsx";

export function Signup() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await api.post("/api/auth/signup", {
        email,
        username: username || null,
        password,
      });
      login(res.data.access_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.detail || "Signup failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container">
      <h2>Sign up</h2>
      <div className="card">
        <form onSubmit={onSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label>Username (optional)</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} type="text" />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label>Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required minLength={8} />
          </div>
          <button className="primary" disabled={submitting} type="submit">
            {submitting ? "Creating..." : "Create account"}
          </button>
        </form>
        {error ? <div className="error">{error}</div> : null}
        <div className="muted" style={{ marginTop: 14 }}>
          Already have an account? <a href="/login">Login</a>
        </div>
      </div>
    </div>
  );
}

