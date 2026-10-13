import "./globals.css";

export const metadata = {
  title: "ULTRON",
  description: "Ultron AI Agent",
};

export default function RootLayout({ children }) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
