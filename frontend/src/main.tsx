import { Shield } from "lucide-react";
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { api, setCsrf, type User } from "./api";

import Shell from "./Layout";
import Login from "./pages/Login";
import { Auth, ErrorMessage, Loading } from "./shared";
import "./styles.css";
function App() {
  const [user, setUser] = useState<User | null>(null);
  const [demo, setDemo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/auth/me")
      .then((r) => {
        setUser(r.user);
        setDemo(r.demo_enabled);
        setCsrf(r.csrf_token);
      })
      .catch((e) => {
        if (e.status !== 401) setError(e.message);
      })
      .finally(() => setLoading(false));
    const expired = () => {
      setUser(null);
      setCsrf("");
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  if (loading) return <Loading />;
  if (error)
    return (
      <div className="startup-error">
        <Shield size={40} />
        <h1>Workspace unavailable</h1>
        <ErrorMessage error={error} />
        <button
          className="button primary"
          onClick={() => window.location.reload()}
        >
          Try again
        </button>
      </div>
    );
  return (
    <Auth.Provider value={{ user, setUser, demo, setDemo }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<Shell />} />
        </Routes>
      </BrowserRouter>
    </Auth.Provider>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
