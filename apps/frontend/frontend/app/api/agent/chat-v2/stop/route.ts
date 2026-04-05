/**
 * Proxy: POST /api/agent/chat-v2/stop
 * Forwards to: POST http://backend:8000/agent/chat-v2/stop
 */

export async function POST(request: Request) {
  try {
    const body = await request.json();

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const url = new URL("/agent/chat-v2/stop", backendUrl);

    // Add query parameter
    url.searchParams.append("session_id", body.session_id);

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      console.error(`Backend error: ${response.status} ${response.statusText}`);
      return Response.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Chat stop error:", error);
    return Response.json(
      { error: error instanceof Error ? error.message : "Internal server error" },
      { status: 500 }
    );
  }
}
