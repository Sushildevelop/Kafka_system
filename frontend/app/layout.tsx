import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata={
  title:"Study AI — Collaborative Study Groups",
  description:"Real-time study groups powered by Kafka and collaborative AI."
};

export default function RootLayout({children}:{readonly children:React.ReactNode}){
  return <html lang="en"><body>{children}</body></html>;
}