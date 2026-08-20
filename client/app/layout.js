import './globals.css';

export const metadata = {
  title: 'Open Grok Bot — Local-First AI Agent Chat (MUAPI)',
  description: 'Local-first AI agent chat app built with Next.js, FastAPI, and MUAPI LLM endpoints.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning={true}>
      <body className="bg-background text-foreground antialiased select-none" suppressHydrationWarning={true}>
        {children}
      </body>
    </html>
  );
}
