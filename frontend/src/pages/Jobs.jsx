import React, { useEffect, useMemo, useState } from "react";

import { api } from "../api/client.js";
import { useAuth } from "../auth/useAuth.jsx";

function statusLabel(status) {
  switch (status) {
    case "applied":
      return "Applied";
    case "interview":
      return "Interview";
    case "rejected":
      return "Rejected";
    case "offer":
      return "Offer";
    default:
      return status;
  }
}

export function Jobs() {
  const { logout, user } = useAuth();

  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [manual, setManual] = useState({ title: "", company: "", location: "" });
  const [byUrl, setByUrl] = useState({ url: "" });

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [jobsRes, appsRes] = await Promise.all([api.get("/api/jobs"), api.get("/api/applications")]);
      setJobs(jobsRes.data);
      setApplications(appsRes.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const appsByJobId = useMemo(() => {
    const map = new Map();
    for (const a of applications) map.set(a.job_id, a);
    return map;
  }, [applications]);

  async function createManualJob(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/api/jobs/manual", {
        title: manual.title,
        company: manual.company,
        location: manual.location || null,
      });
      setManual({ title: "", company: "", location: "" });
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create job");
    }
  }

  async function createByUrl(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/api/jobs/by-url", { url: byUrl.url });
      setByUrl({ url: "" });
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to enqueue scrape");
    }
  }

  async function apply(jobId, status) {
    setError("");
    try {
      await api.post(`/api/jobs/${jobId}/apply`, { status });
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to update status");
    }
  }

  async function updateExistingApplication(applicationId, status) {
    setError("");
    try {
      await api.patch(`/api/applications/${applicationId}`, { status });
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to update status");
    }
  }

  async function deleteJob(jobId) {
    const confirmDelete = window.confirm("Are you sure you want to delete this job?");
    if (!confirmDelete) return;
  
    setError("");
    try {
      await api.delete(`/api/jobs/${jobId}`);
      await load(); // refresh list
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to delete job");
    }
  }

  return (
    <div className="container">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>Jobs</h2>
        <div className="row">
          <div className="muted" style={{ fontSize: 14 }}>
            {user?.username || user?.email}
          </div>
          <button onClick={logout}>Logout</button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Add job</h3>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <form onSubmit={createManualJob} style={{ flex: 1, minWidth: 280 }}>
            <h4>Manual</h4>
            <div style={{ marginBottom: 10 }}>
              <label>Title</label>
              <input value={manual.title} onChange={(e) => setManual({ ...manual, title: e.target.value })} required />
            </div>
            <div style={{ marginBottom: 10 }}>
              <label>Company</label>
              <input value={manual.company} onChange={(e) => setManual({ ...manual, company: e.target.value })} required />
            </div>
            <div style={{ marginBottom: 10 }}>
              <label>Location (optional)</label>
              <input
                value={manual.location}
                onChange={(e) => setManual({ ...manual, location: e.target.value })}
                placeholder="Remote / City"
              />
            </div>
            <button className="primary" type="submit">
              Add manual job
            </button>
          </form>

          <form onSubmit={createByUrl} style={{ flex: 1, minWidth: 280 }}>
            <h4>URL</h4>
            <div style={{ marginBottom: 10 }}>
              <label>Job URL</label>
              <input
                value={byUrl.url}
                onChange={(e) => setByUrl({ url: e.target.value })}
                placeholder="LinkedIn URL"
                required
              />
            </div>
            <button className="primary" type="submit">
              Add job from URL
            </button>
          </form>
        </div>
        {error ? <div className="error">{error}</div> : null}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Your jobs</h3>
        {loading ? <div className="muted">Loading...</div> : null}
        {!loading && jobs.length === 0 ? <div className="muted">No jobs yet.</div> : null}

        <div>
          {jobs.map((job) => {
            const appRow = appsByJobId.get(job.id);
            const currentStatus = appRow?.status || null;
            return (
              <div key={job.id} style={{ borderTop: "1px solid rgba(255,255,255,0.12)", paddingTop: 12, marginTop: 12 }}>
                <div style={{ fontWeight: 700 }}>{job.title || "Untitled job"}</div>
                <div className="muted">
                  {job.company || "Unknown company"} {job.location ? `• ${job.location}` : ""}
                </div>
                {job.url ? (
                  <div style={{ marginTop: 8 }}>
                    <a href={job.url} target="_blank" rel="noreferrer">
                      Open source
                    </a>
                  </div>
                ) : null}

                <div className="row" style={{ marginTop: 10, justifyContent: "space-between" }}>
                  <div>
                    <div className="muted">Scrape</div>
                    <div>{job.scrape_status}</div>
                    {job.scrape_error && job.scrape_status !== "scraped" ? (
                      <div className="muted" style={{ fontSize: 12, marginTop: 6, color: "#ff8a8a" }}>
                        {job.scrape_error}
                      </div>
                    ) : null}
                  </div>
                  <div>
                    <div className="muted">Application</div>
                    <div>{currentStatus ? statusLabel(currentStatus) : "Not applied yet"}</div>
                  </div>
                  <div className="row">
                    <button
                      type="button"
                      onClick={() => apply(job.id, "applied")}
                      className="primary"
                      style={{ opacity: currentStatus === "applied" ? 0.7 : 1 }}
                    >
                      Apply
                    </button>
                    <select
                      value={currentStatus || ""}
                      onChange={(e) => {
                        const next = e.target.value;
                        if (!next) return;
                        if (appRow?.id) updateExistingApplication(appRow.id, next);
                        else apply(job.id, next);
                      }}
                    >
                      <option value="">Update status...</option>
                      <option value="interview">Interview</option>
                      <option value="rejected">Rejected</option>
                      <option value="offer">Offer</option>
                    </select>
                    {/* 🔴 Delete Button */}
  <button
    type="button"
    onClick={() => deleteJob(job.id)}
    style={{
      background: "#ff4d4f",
      color: "white",
      border: "none",
      padding: "6px 10px",
      borderRadius: "4px",
      cursor: "pointer",
    }}
  >
    Delete
  </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

