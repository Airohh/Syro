import { ArrowRight } from 'lucide-react';
import { getDomainConfig } from '../utils/domainConfig';
import { getDomainClasses } from '../utils/domainStyles';

interface EmptyStateProps {
  domainId?: string;
  onPromptClick?: (prompt: string) => void;
}

export default function EmptyState({ domainId = 'general', onPromptClick }: EmptyStateProps) {
  const domain = getDomainConfig(domainId);
  const domainClasses = getDomainClasses(domainId);
  const Icon = domain.icon;

  return (
    <div className="flex items-center justify-center h-full px-4 py-12 animate-fade-in">
      <div className="max-w-2xl w-full">
        {/* Hero */}
        <div className="text-center mb-10">
          <div className={`relative inline-flex items-center justify-center w-20 h-20 rounded-3xl mb-6
            ${domainClasses.bgLight} ${domainClasses.text}`}>
            <Icon className="w-10 h-10" />
            {/* Subtle glow */}
            <div className={`absolute inset-0 rounded-3xl opacity-30 blur-xl ${domainClasses.bgLight}`} />
          </div>

          <h2 className="text-2xl font-semibold text-zinc-100 mb-2 tracking-tight">
            {domain.name}
          </h2>
          <p className="text-sm text-zinc-500 max-w-sm mx-auto leading-relaxed">
            {domain.welcomeMessage}
          </p>
        </div>

        {/* Prompt grid */}
        <div>
          <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest text-center mb-4">
            Exemples de questions
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {domain.examplePrompts.map((prompt, index) => (
              <button
                key={index}
                onClick={() => onPromptClick?.(prompt)}
                className="group text-left px-4 py-3.5 bg-zinc-900/80 border border-white/6 rounded-xl
                  hover:bg-zinc-800/80 hover:border-white/10 transition-all duration-200 cursor-pointer
                  flex items-start gap-3"
              >
                <div className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center mt-0.5
                  ${domainClasses.bgLight} ${domainClasses.text} opacity-80 group-hover:opacity-100`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <span className="flex-1 text-sm text-zinc-400 group-hover:text-zinc-200 leading-relaxed transition-colors">
                  {prompt}
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-zinc-700 group-hover:text-zinc-400 shrink-0 mt-1
                  transition-all duration-200 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0" />
              </button>
            ))}
          </div>
        </div>

        <p className="text-center text-xs text-zinc-700 mt-6">
          Tapez votre question ci-dessous
        </p>
      </div>
    </div>
  );
}
