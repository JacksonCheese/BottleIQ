"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Logo, ErrorState } from "@/components/ui";

export default function Page() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const result = await api<{ message: string }>("/auth/recovery/request", {
        method: "POST",
        body: JSON.stringify({ email: data.get("email") }),
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
        <h1>Reset your password</h1>
        <p>
          Enter your account email. A link will be sent if the address belongs
          to an account.
        </p>
        <form onSubmit={submit}>
          <label>
            Email
            <input name="email" type="email" required autoComplete="email" />
          </label>
          <button className="button">Send reset link</button>
        </form>
        {message && (
          <div className="notice" role="status">
            {message}
          </div>
        )}
        {error && <ErrorState message={error} />}
        <p>
          <Link href="/login">Back to sign in</Link>
        </p>
      </div>
    </main>
  );
}
