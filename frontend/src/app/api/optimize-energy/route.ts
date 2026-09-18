export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  let scenario: unknown;
  try {
    scenario = await request.json();
  } catch {
    return Response.json(
      { error: { code: "invalid_request", message: "Send a scenario as a JSON request body." } },
      { status: 422 },
    );
  }

  const baseUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL ||
    (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");
  if (!baseUrl) {
    return Response.json(
      { error: { code: "backend_not_configured", message: "The optimization service is not configured." } },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/optimize-energy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scenario),
      cache: "no-store",
      signal: AbortSignal.timeout(45000),
    });
    const data: unknown = await response.json();
    return Response.json(data, { status: response.status });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    return Response.json(
      { error: {
        code: timedOut ? "backend_timeout" : "backend_unavailable",
        message: timedOut
          ? "Optimization took too long. Please try again."
          : "Cannot reach the optimization service. Check that the backend is running.",
      } },
      { status: timedOut ? 504 : 502 },
    );
  }
}
