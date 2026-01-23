import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Janus - The Open Intelligence Rodeo",
  description: "Build the intelligence engine on the decentralized intelligence network powered by Bittensor Subnet 64. Anything In, Anything Out.",
  keywords: ["AI", "Bittensor", "Subnet 64", "OpenAI", "Competition", "Decentralized AI"],
  icons: {
    icon: [
      { url: "/favicon-16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
