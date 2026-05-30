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
    <header className="h-12 bg-zinc-950/95 backdrop-blur-xl border-b border-white/5 flex items-center px-4 shrink-0 sticky top-0 z-40">
      <div className="flex items-center justify-between w-full">
        {/* Left: Logo + Domain */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-sm font-semibold text-zinc-100 tracking-tight hidden sm:inline">
              Syro
            </span>
          </div>

          <div className="h-4 w-px bg-white/10" />

          <DomainSelector
            currentDomain={currentDomain}
            onDomainChange={onDomainChange}
          />
        </div>

        {/* Right: Current domain pill */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-900 border border-white/6">
          <DomainIcon className="w-3.5 h-3.5 text-zinc-400" />
          <span className="text-xs text-zinc-400 font-medium">{domain.shortName}</span>
        </div>
      </div>
    </header>
  );
}
