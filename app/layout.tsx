import type { Metadata } from "next";
import { Barlow_Condensed, Source_Serif_4, JetBrains_Mono } from "next/font/google";

import "./globals.css";

const signage = Barlow_Condensed({
  variable: "--font-barlow-condensed",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const reading = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  display: "swap",
});

const code = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "GitRun — generated wikis for department codebases",
    template: "%s · GitRun",
  },
  description:
    "GitRun compiles an undocumented repository into a browsable wiki with a hierarchical tree index, so every answer names the section it came from.",
};

const themeScript = `(function(){try{var s=localStorage.getItem("gitrun-theme");var d=window.matchMedia("(prefers-color-scheme: dark)").matches;if(s==="dark"||(!s&&d)){document.documentElement.classList.add("dark")}}catch(e){}})();`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${signage.variable} ${reading.variable} ${code.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full flex flex-col bg-paper text-ink">{children}</body>
    </html>
  );
}
