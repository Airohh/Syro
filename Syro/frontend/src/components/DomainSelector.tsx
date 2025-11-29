import { useState } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { domains, getDomainConfig } from '../utils/domainConfig';
import { getDomainClasses } from '../utils/domainStyles';

interface DomainSelectorProps {
  currentDomain: string;
  onDomainChange: (domainId: string) => void;
}

export default function DomainSelector({ currentDomain, onDomainChange }: DomainSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const current = getDomainConfig(currentDomain);
  const currentClasses = getDomainClasses(currentDomain);
  const CurrentIcon = current.icon;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2.5 px-3.5 py-2 rounded-lg 
          ${currentClasses.bgLight} ${currentClasses.text} 
          hover:opacity-90 transition-all duration-200 
          border border-transparent shadow-soft text-sm font-medium
          active:scale-[0.98]`}
      >
        <CurrentIcon className="w-4 h-4 flex-shrink-0" />
        <span className="hidden sm:inline font-medium">{current.shortName}</span>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-2 w-72 bg-white rounded-xl shadow-large 
            border border-gray-200 z-20 overflow-hidden animate-slide-down">
            <div className="p-2">
              {Object.values(domains).map((domain) => {
                const DomainIcon = domain.icon;
                const isSelected = domain.id === currentDomain;
                const domainClasses = getDomainClasses(domain.id);
                
                return (
                  <button
                    key={domain.id}
                    onClick={() => {
                      onDomainChange(domain.id);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-lg 
                      transition-all duration-200 text-left group
                      ${isSelected 
                        ? `${domainClasses.bgLight} ${domainClasses.text} shadow-soft` 
                        : 'hover:bg-gray-50 text-gray-700'
                      }`}
                  >
                    <DomainIcon className={`w-4 h-4 flex-shrink-0 ${isSelected ? '' : 'text-gray-400 group-hover:text-gray-600'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{domain.name}</div>
                      <div className="text-xs text-gray-500 truncate mt-0.5">{domain.description}</div>
                    </div>
                    {isSelected && (
                      <Check className="w-4 h-4 flex-shrink-0" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
