import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const path = request.nextUrl.pathname.replace("/api/proxy", "");
  
  try {
    const body = await request.json();
    const response = await fetch(`${BACKEND_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Proxy failed" }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  const path = request.nextUrl.pathname.replace("/api/proxy", "");
  
  try {
    const response = await fetch(`${BACKEND_URL}${path}`);
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Proxy failed" }, { status: 500 });
  }
}