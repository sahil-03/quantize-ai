export default function Robot() {
  return (
    <div className="flex items-center justify-center min-h-[40px]">
      <div className="relative w-full h-10">
        <div className="absolute left-0 top-0 -translate-y-1/2 animate-walk-contained">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-bounce-subtle">
            {/* Robot head */}
            <rect x="7" y="4" width="10" height="10" rx="2" fill="#4B5563" className="animate-tilt"/>
            {/* Robot eyes */}
            <circle cx="10" cy="8" r="1" fill="#10B981"/>
            <circle cx="14" cy="8" r="1" fill="#10B981"/>
            {/* Robot antenna */}
            <line x1="12" y1="2" x2="12" y2="4" stroke="#4B5563" strokeWidth="2"/>
            {/* Robot body */}
            <rect x="9" y="14" width="6" height="6" fill="#4B5563"/>
            {/* Robot legs */}
            <line x1="10" y1="20" x2="10" y2="22" stroke="#4B5563" strokeWidth="2" className="animate-walk-leg-left"/>
            <line x1="14" y1="20" x2="14" y2="22" stroke="#4B5563" strokeWidth="2" className="animate-walk-leg-right"/>
          </svg>
        </div>
      </div>
    </div>
  );
}