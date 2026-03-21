const EXPECTED_SECTIONS = [
  { id: 'Abstract', label: 'Abstract & Summary' },
  { id: '1_Introduction', label: '1. Introduction' },
  { id: '2_Literature_Review', label: '2. Literature Evaluation' },
  { id: '3_Methodology', label: '3. Math / Methodology' },
  { id: '4_Results', label: '4. Structural Results' },
  { id: '5_Discussion', label: '5. Technical Discussion' },
  { id: '6_Conclusions', label: '6. Final Adjudication' }
];

export default function ReportOutline({ sections }: { sections: any[] }) {
  return (
    <div className="flex flex-col gap-3">
      {EXPECTED_SECTIONS.map(req => {
        const generated = sections.find(s => s.section === req.id);
        const isActive = !generated && sections.length > 0 && sections.length < EXPECTED_SECTIONS.length;
        
        return (
          <div key={req.id} className="relative">
             <div className="flex items-center gap-2 mb-1">
               <div className={`w-1.5 h-1.5 rounded-full ${generated ? 'bg-octGreen' : isActive ? 'bg-blue-500 animate-pulse' : 'bg-gray-700'}`} />
               <span className={`text-xs font-semibold ${generated ? 'text-gray-300' : 'text-gray-600'}`}>{req.label}</span>
             </div>
             {generated && (
               <div className="ml-3 pl-2 border-l border-gray-800 text-[10px] text-gray-500 line-clamp-2 italic">
                 {generated.content}
               </div>
             )}
          </div>
        );
      })}
    </div>
  );
}
