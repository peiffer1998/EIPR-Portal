export default function NotFound(): JSX.Element {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md grid gap-2">
        <div className="text-lg font-semibold">Page not found</div>
        <div className="text-sm text-slate-600">
          The page you’re looking for doesn’t exist or may have moved.
        </div>
        <a className="btn btn-primary w-fit" href="/staff">
          Go to staff home
        </a>
      </div>
    </div>
  );
}
