import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { NotificationSystem } from "@/components/ToastNotification";
import { Navigation } from "@/components/layout/Navigation";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Thalas Trader - Multi-LLM Consensus Trading Bot",
  description: "Real-time trading dashboard powered by multi-LLM consensus mechanism",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-neutral-950 text-neutral-100`}
      >
        <Navigation />
        <NotificationSystem />
        <main className="min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
