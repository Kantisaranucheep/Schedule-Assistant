/**
 * Proxy: POST /api/agent/chat-v2/start
 * Forwards to: POST http://backend:8000/agent/chat-v2/start
 */

export async function POST(request: Request) {
  try {
    const body = await request.json();
    console.log("[Chat-V2 Start] Received request:", body);

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const url = new URL("/agent/chat-v2/start", backendUrl);

    // Add query parameters
    url.searchParams.append("user_id", body.user_id);
    url.searchParams.append("calendar_id", body.calendar_id);
    if (body.title) {
      url.searchParams.append("title", body.title);
    }

    console.log("[Chat-V2 Start] Forwarding to backend:", url.toString());

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    console.log("[Chat-V2 Start] Backend response status:", response.status);

    const responseText = await response.text();
    console.log("[Chat-V2 Start] Backend response body:", responseText);

    let responseData;
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = { error: "Invalid JSON response from backend", body: responseText };
    }

    if (!response.ok) {
      console.error("[Chat-V2 Start] Backend error:", response.status, responseData);
      return Response.json(
        { error: responseData?.detail || responseData?.error || `Backend error: ${response.statusText}` },
        { status: response.status }
      );
    }

    console.log("[Chat-V2 Start] Success:", responseData);
    return Response.json(responseData);
  } catch (error) {
    console.error("[Chat-V2 Start] Error:", error);
    const errorMessage = error instanceof Error ? error.message : "Internal server error";
    return Response.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}
