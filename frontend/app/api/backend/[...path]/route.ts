import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || 'http://backend:8000';

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  const subpath = params.path ? params.path.join('/') : '';
  const search = request.nextUrl.search;
  const targetUrl = `${BACKEND_URL}/api/v1/${subpath}${search}`;

  try {
    const headers: Record<string, string> = {
      Accept: 'application/json, audio/*',
    };
    const incomingAuth = request.headers.get('authorization') || request.headers.get('x-admin-key');
    if (incomingAuth) {
      headers['authorization'] = incomingAuth;
    } else {
      headers['x-admin-key'] = process.env.ADMIN_API_KEY || 'dev_admin_key_hello_farmer_2026';
    }

    const res = await fetch(targetUrl, {
      cache: 'no-store',
      headers,
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
  const search = request.nextUrl.search;
  const targetUrl = `${BACKEND_URL}/api/v1/${subpath}${search}`;
  const contentType = request.headers.get('content-type') || '';

  try {
    let fetchOptions: RequestInit = {
      method: 'POST',
    };

    const authHeader = request.headers.get('authorization') || request.headers.get('x-admin-key') || process.env.ADMIN_API_KEY || 'dev_admin_key_hello_farmer_2026';
    let baseHeaders: Record<string, string> = {
      'x-admin-key': authHeader,
    };
    if (request.headers.get('authorization')) {
      baseHeaders['authorization'] = request.headers.get('authorization')!;
    }

    if (contentType.includes('multipart/form-data')) {
      const formData = await request.formData();
      fetchOptions.body = formData;
      fetchOptions.headers = baseHeaders;
    } else if (contentType.includes('application/json')) {
      const body = await request.json();
      fetchOptions.headers = { ...baseHeaders, 'Content-Type': 'application/json' };
      fetchOptions.body = JSON.stringify(body);
    } else {
      const arrayBuffer = await request.arrayBuffer();
      fetchOptions.headers = contentType ? { ...baseHeaders, 'Content-Type': contentType } : baseHeaders;
      fetchOptions.body = arrayBuffer;
    }

    const res = await fetch(targetUrl, fetchOptions);
    const resContentType = res.headers.get('content-type') || '';

    if (resContentType.includes('audio/')) {
      const buffer = await res.arrayBuffer();
      return new NextResponse(buffer, {
        status: res.status,
        headers: {
          'Content-Type': resContentType,
          'Content-Length': buffer.byteLength.toString(),
        },
      });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 502 });
  }
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  const subpath = params.path ? params.path.join('/') : '';
  const search = request.nextUrl.search;
  const targetUrl = `${BACKEND_URL}/api/v1/${subpath}${search}`;

  try {
    const headers: Record<string, string> = {
      Accept: 'application/json',
    };
    const incomingAuth = request.headers.get('authorization') || request.headers.get('x-admin-key');
    if (incomingAuth) {
      headers['authorization'] = incomingAuth;
    } else {
      headers['x-admin-key'] = process.env.ADMIN_API_KEY || 'dev_admin_key_hello_farmer_2026';
    }

    const res = await fetch(targetUrl, {
      method: 'DELETE',
      headers,
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 502 });
  }
}
