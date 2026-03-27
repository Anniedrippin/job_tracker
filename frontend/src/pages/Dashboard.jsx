import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import { ResponsiveContainer } from "recharts";

import { api } from "../api/client.js";
import { useAuth } from "../auth/useAuth.jsx";

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042"];

export function Dashboard() {
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/api/analytics/dashboard");
        setStats(res.data);
      } catch (err) {
        setError(err?.response?.data?.detail || "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const chartData = stats
    ? [
        { name: "Applied", value: stats.total_applied },
        { name: "Interviews", value: stats.interviews },
        { name: "Offers", value: stats.offers },
        { name: "Rejections", value: stats.rejections },
      ]
    : [];

  return (
    <div className="container">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>Dashboard</h2>
        <div className="row">
          <div className="muted" style={{ fontSize: 14 }}>
            {user?.username || user?.email}
          </div>
          <button onClick={() => navigate("/jobs")}>Jobs</button>
          <button onClick={logout}>Logout</button>
        </div>
      </div>

      <div className="card">
        {loading && <div className="muted">Loading...</div>}
        {error && <div className="error">{error}</div>}

        {stats && (
          <>
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    dataKey="value"
                    label
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div style={{ marginTop: 20, textAlign: "center" }}>
              <div className="muted">Rejection Rate</div>
              <div style={{ fontSize: 22 }}>
                {(stats.rejection_rate * 100).toFixed(1)}%
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}