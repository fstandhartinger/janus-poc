import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Janus - The Open Intelligence Rodeo",
  description: "Compete to build the best AI agent on the decentralized intelligence network powered by Bittensor Subnet 64. Anything In, Anything Out.",
  keywords: ["AI", "Bittensor", "Subnet 64", "OpenAI", "Competition", "Decentralized AI"],
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
