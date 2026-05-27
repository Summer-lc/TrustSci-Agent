import "./globals.css";

export const metadata = {
  title: "TrustSci Agent",
  description: "Evidence-grounded multi-agent AI Scientist workbench"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

