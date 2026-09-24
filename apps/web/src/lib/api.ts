export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      credentials: "same-origin",
      headers: {
        ...(init?.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...init?.headers,
      },
    });
  } catch {
    throw new Error(
      "Cannot reach BottleIQ. Check your connection and try again.",
    );
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail
              .map(
                (e: { msg: string; loc: string[] }) =>
                  `${e.loc.at(-1)}: ${e.msg}`,
              )
              .join("; ")
          : "We couldn't complete that request. Please try again.";
    const requestId = data.request_id || response.headers?.get("X-Request-ID");
    throw new Error(
      response.status >= 500 && requestId
        ? `${message} If this keeps happening, report code ${requestId}.`
        : message,
    );
  }
  return response.json();
}
export const money = (n: number | null | undefined, precise = false) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: precise ? 2 : 0,
      }).format(n);
export const decimal = (n: number | null | undefined, digits = 1) =>
  n == null
    ? "—"
    : n.toLocaleString("en-US", { maximumFractionDigits: digits });
