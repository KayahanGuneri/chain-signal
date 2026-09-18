import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const route = path.join("/");
  if (!/^(events(?:\/\d+)?|supply-assets(?:\/\d+(?:\/nearby-events)?)?)$/.test(route)) {
    return NextResponse.json({ message: "API route not found" }, { status: 404 });
  }
  try {
    const base = process.env.BACKEND_URL ?? "http://localhost:8080";
    const url = new URL(`/api/${route}`, base);
    url.search = request.nextUrl.search;
    const upstream = await fetch(url, { cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10000) });
    return new NextResponse(await upstream.text(), { status: upstream.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ message: "Backend unavailable. Check the backend health and connection." }, { status: 502 });
  }
}
