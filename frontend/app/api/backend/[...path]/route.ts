import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || 'http://backend:8000';

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  const subpath = params.path ? params.path.join('/') : '';
  const search = request.nextUrl.search;
  const targetUrl = `${BACKEND_URL}/api/v1/${subpath}${search}`;

  try {
    const res = await fetch(targetUrl, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('audio/')) {
      const buffer = await res.arrayBuffer();
      return new NextResponse(buffer, {
        status: res.status,
        headers: {
          'Content-Type': contentType,
          'Content-Length': buffer.byteLength.toString(),
          'Cache-Control': 'public, max-age=3600',
        },
      });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 502 });
  }
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  const subpath = params.path ? params.path.join('/') : '';
  const targetUrl = `${BACKEND_URL}/api/v1/${subpath}`;

  try {
    const body = await request.json();
    const res = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 502 });
  }
}
