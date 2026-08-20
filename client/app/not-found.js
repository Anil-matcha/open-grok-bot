import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex h-screen w-screen flex-col items-center justify-center bg-[#09090b] text-zinc-100 font-sans p-6 text-center space-y-4">
      <h1 className="text-4xl font-extrabold text-blue-500">404</h1>
      <h2 className="text-lg font-bold text-zinc-200">Page Not Found</h2>
      <p className="text-xs text-zinc-400 max-w-sm">
        The requested agent route or thread does not exist.
      </p>
      <Link
        href="/"
        className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/30 transition"
      >
        Return to Dashboard
      </Link>
    </div>
  );
}


