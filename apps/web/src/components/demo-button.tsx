"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
export function DemoButton({ guided = false }: { guided?: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <div>
      <button
        className={`button${guided ? " secondary" : ""}`}
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            await api("/auth/demo", { method: "POST" });
            if (guided) sessionStorage.setItem("bottleiq:walkthrough", "start");
            router.push("/dashboard");
          } catch (e) {
            setError((e as Error).message);
            setBusy(false);
          }
        }}
      >
        {busy
          ? "Opening your store…"
          : guided
            ? "Guided walkthrough"
            : "Try the Demo"}
        <ArrowRight size={18} />
      </button>
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
    </div>
  );
}
