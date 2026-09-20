import Link from "next/link";
export default function NotFound() {
  return (
    <main className="empty">
      <h1>Page not found</h1>
      <Link className="button" href="/dashboard">
        Back to overview
      </Link>
    </main>
  );
}
