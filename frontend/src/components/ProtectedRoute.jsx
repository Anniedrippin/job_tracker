import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth.jsx";

export function ProtectedRoute({ children }) {
  const { accessToken, loadingUser } = useAuth();

  if (loadingUser) return <div className="container">Loading...</div>;
  if (!accessToken) return <Navigate to="/login" replace />;

  return children;
}

