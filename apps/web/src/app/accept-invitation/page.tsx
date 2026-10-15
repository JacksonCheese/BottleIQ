"use client";
import { Suspense, useState, type FormEvent } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Logo, ErrorState } from "@/components/ui";

function InvitationForm() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await api("/auth/invitations/accept", {
        method: "POST",
        body: JSON.stringify({
          token: params.get("token"),
          name: data.get("name"),
          password: data.get("password"),
        }),
      });
      router.push("/dashboard");
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
        <h1>Join your team</h1>
        <form onSubmit={submit}>
          <label>
            Your name
            <input name="name" required maxLength={120} autoComplete="name" />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              required
              minLength={12}
              maxLength={128}
              autoComplete="new-password"
            />
          </label>
          <button className="button" disabled={!params.get("token")}>
            Accept invitation
          </button>
        </form>
        {error && <ErrorState message={error} />}
      </div>
    </main>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<main className="auth-page">Loading…</main>}>
      <InvitationForm />
    </Suspense>
  );
}
