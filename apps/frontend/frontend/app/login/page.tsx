"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "../services/auth.api";
import "./login.css";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const session = localStorage.getItem("scheduler_auth_session");
    if (session) {
      router.replace("/");
    }
  }, [router]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await login({ username, password });
      localStorage.setItem("scheduler_auth_session", JSON.stringify(result));
      router.push("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-bg-shape login-bg-shape-left" />
      <div className="login-bg-shape login-bg-shape-right" />

      <section className="login-card" aria-label="Login form">
        <p className="login-kicker">Schedule Assistant</p>
        <h1 className="login-title">Welcome back</h1>
        <p className="login-subtitle">Sign in with your username and password.</p>

        <form onSubmit={onSubmit} className="login-form">
          <label className="login-label" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            className="login-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
            autoComplete="username"
            required
          />

          <label className="login-label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className="login-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            autoComplete="current-password"
            required
          />

          {error && <div className="login-error">{error}</div>}

          <button className="login-button" type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>

        <div className="login-hint">
          Demo account: <strong>demo</strong> / <strong>demo1234</strong>
        </div>
      </section>
    </main>
  );
}
