import React from 'react';
import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Hello Farmer (ሄሎ ፋርመር) | Ethiopian Agricultural AI Platform',
  description: 'AI agricultural assistant for Ethiopian farmers in Amharic, Afaan Oromo, and English. Accessible via national voice line 8028 and web portal.',
  icons: {
    icon: '/hello_farmer_logo.jpg',
    apple: '/hello_farmer_logo.jpg',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/hello_farmer_logo.jpg" type="image/jpeg" />
      </head>
      <body>{children}</body>
    </html>
  );
}
