"use client";
import { Suspense, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Logo, ErrorState } from "@/components/ui";

function ResetForm() {
  const params = useSearchParams();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const result = await api<{ message: string }>("/auth/recovery/reset", {
        method: "POST",
        body: JSON.stringify({
          token: params.get("token"),
          password: data.get("password"),
        }),
      });
      setMessage(result.message);
    } catch (cause) {
      setError((cause as Error).message);
    }
  }
  return (
    <main className="auth-page">
      <Link href="/">
        <Logo />
      </Link>
      <div className="panel">
        <h1>Choose a new password</h1>
        <form onSubmit={submit}>
          <label>
            New password
            <input
              name="password"
              type="password"
              minLength={12}
              maxLength={128}
              required
              autoComplete="new-password"
            />
          </label>
          <button className="button" disabled={!params.get("token")}>
            Change password
          </button>
        </form>
        {message && (
          <div className="notice" role="status">
            {message}
          </div>
        )}
        {error && <ErrorState message={error} />}
        <p>
          <Link href="/login">Sign in</Link>
        </p>
      </div>
    </main>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<main className="auth-page">Loading…</main>}>
      <ResetForm />
    </Suspense>
  );
}
