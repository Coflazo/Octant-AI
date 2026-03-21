export default function DownloadPDF({ url }: { url: string | null }) {
  if (!url) return null;

  return (
    <div className="animate-in fade-in zoom-in duration-500">
      <a 
        href={url}
        target="_blank"
        rel="noreferrer"
        className="flex mb-4 items-center justify-center gap-2 w-full py-4 bg-octNavy text-white hover:bg-[#255294] text-sm font-bold tracking-widest uppercase rounded-md transition-all shadow-[0_0_20px_rgba(27,61,110,0.6)] hover:shadow-[0_0_30px_rgba(27,61,110,0.8)]"
      >
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" className="w-5 h-5" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
        Download Academic PDF
      </a>
      <div className="text-center text-[10px] text-gray-500 mt-2">Document compiled securely via pdflatex.</div>
    </div>
  );
}
