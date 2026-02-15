import type { Metadata } from "next";
import { Space_Grotesk, Pacifico } from "next/font/google";
import { LayoutShell } from "@/components/layout/LayoutShell";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const pacifico = Pacifico({
  variable: "--font-wordmark",
  subsets: ["latin"],
  weight: "400",
});


export const metadata: Metadata = {
  title: "bye! buy! — sell anything, automatically",
  description:
    "Our AI agents post your item across every major platform, filter out scammers, negotiate the best price, and guarantee instant payment. You just deliver.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${spaceGrotesk.variable} ${pacifico.variable} font-sans antialiased bg-cream min-h-screen`}>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}
