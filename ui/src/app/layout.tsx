import type { Metadata } from "next";
import "./globals.css";
import PreReleaseGate from "@/components/PreReleaseGate";

export const metadata: Metadata = {
  title: "Janus - The Open Intelligence Rodeo",
  description: "Build the intelligence engine on the decentralized intelligence network powered by Bittensor. Anything In, Anything Out.",
  keywords: ["Intelligence", "Bittensor", "OpenAI", "Competition", "Decentralized Intelligence"],
  icons: {
    icon: "/favicon-new.png",
    shortcut: "/favicon-new.png",
    apple: "/favicon-new.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#63D297" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Janus" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body className="antialiased">
        <PreReleaseGate />
        {children}
      </body>
    </html>
  );
}
