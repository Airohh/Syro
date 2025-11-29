import { Sparkles } from 'lucide-react';
import DomainSelector from './DomainSelector';
import { getDomainConfig } from '../utils/domainConfig';

interface HeaderProps {
  currentDomain: string;
  onDomainChange: (domainId: string) => void;
}

export default function Header({ currentDomain, onDomainChange }: HeaderProps) {
  const domain = getDomainConfig(currentDomain);
  const DomainIcon = domain.icon;

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center px-6 shrink-0 sticky top-0 z-40 backdrop-blur-sm bg-white/95">
      <div className="flex items-center justify-between w-full">
        {/* Left: Logo + Domain */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-gray-900 to-gray-700 flex items-center justify-center shadow-soft">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-semibold text-gray-900 hidden sm:inline tracking-tight">
              Syro
            </span>
          </div>
          <div className="h-5 w-px bg-gray-200" />
          <DomainSelector 
            currentDomain={currentDomain} 
            onDomainChange={onDomainChange}
          />
        </div>

        {/* Right: Domain info */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-100">
            <DomainIcon className="w-4 h-4 text-gray-600" />
            <span className="text-xs text-gray-600 font-medium">
              {domain.shortName}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
