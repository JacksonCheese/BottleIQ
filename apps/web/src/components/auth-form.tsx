"use client";
import { useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Logo, ErrorState } from "./ui";
export function AuthForm({ signup = false }: { signup?: boolean }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api(signup ? "/auth/signup" : "/auth/login", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))),
      });
      router.push("/dashboard");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-page">
      <Link href="/">
        <Logo />
      </Link>
      <div className="panel">
        <div className="eyebrow">BETTER ORDERS START HERE</div>
        <h1>{signup ? "Make room for clarity." : "Welcome back."}</h1>
        <p>
          {signup
            ? "Create your BottleIQ workspace."
            : "Sign in to see how your shelves are doing."}
        </p>
        <form onSubmit={submit}>
          {signup && (
            <>
              <label>
                Your name
                <input
                  name="name"
                  required
                  maxLength={120}
                  autoComplete="name"
                />
              </label>
              <label>
                Business name
                <input
                  name="organization_name"
                  required
                  maxLength={160}
                  autoComplete="organization"
                />
              </label>
            </>
          )}
          <label>
            Email
            <input name="email" type="email" required autoComplete="email" />
          </label>
          <label>
            Password
            <input
              name="password"
              aria-label="Password"
              aria-describedby="password-help"
              type="password"
              required
              minLength={12}
              maxLength={128}
              autoComplete={signup ? "new-password" : "current-password"}
            />
            <small id="password-help">At least 12 characters.</small>
          </label>
          {error && <ErrorState message={error} />}
          <button className="button" disabled={busy}>
            {busy ? "Please wait…" : signup ? "Create account" : "Sign in"}
          </button>
        </form>
        <p>
          {signup ? "Already have an account?" : "New to BottleIQ?"}{" "}
          <Link href={signup ? "/login" : "/signup"}>
            {signup ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </div>
    </main>
  );
}
