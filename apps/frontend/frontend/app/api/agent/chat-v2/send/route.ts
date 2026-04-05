/**
 * Proxy: POST /api/agent/chat-v2/send
 * Forwards to: POST http://backend:8000/agent/chat-v2/send
 */

export async function POST(request: Request) {
  try {
    const body = await request.json();
    console.log("[Chat-V2 Send] Received request:", body);

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const url = new URL("/agent/chat-v2/send", backendUrl);

    // Add query parameters
    url.searchParams.append("session_id", body.session_id);
    url.searchParams.append("user_id", body.user_id);
    url.searchParams.append("calendar_id", body.calendar_id);
    url.searchParams.append("message", body.message);
    if (body.timezone) {
      url.searchParams.append("timezone", body.timezone);
    }

    console.log("[Chat-V2 Send] Forwarding to backend:", url.toString());

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    console.log("[Chat-V2 Send] Backend response status:", response.status);

    const responseText = await response.text();
    console.log("[Chat-V2 Send] Backend response body:", responseText);

    if (!response.ok) {
      console.error("[Chat-V2 Send] Backend error:", response.status, responseText);
      return Response.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      );
    }

    let data;
    try {
      data = JSON.parse(responseText);
    } catch {
      data = { error: "Invalid JSON response", body: responseText };
    }

    console.log("[Chat-V2 Send] Success:", data);
    return Response.json(data);
  } catch (error) {
    console.error("[Chat-V2 Send] Error:", error);
    return Response.json(
      { error: error instanceof Error ? error.message : "Internal server error" },
      { status: 500 }
    );
  }
}
