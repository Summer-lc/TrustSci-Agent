import "./globals.css";

export const metadata = {
  title: "TrustSci Agent",
  description: "基于证据的多智能体 AI Scientist 工作台"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
