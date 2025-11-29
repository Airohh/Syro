import { Sparkles, ArrowRight } from 'lucide-react';
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
    <div className="flex items-center justify-center h-full px-6 animate-fade-in">
      <div className="max-w-2xl w-full text-center">
        {/* Icon & Title */}
        <div className="mb-10">
          <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl 
            ${domainClasses.bgLight} ${domainClasses.text} mb-6 shadow-medium`}>
            <Icon className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-3 tracking-tight">
            {domain.name}
          </h2>
          <p className="text-gray-600 text-sm max-w-md mx-auto leading-relaxed">
            {domain.welcomeMessage}
          </p>
        </div>

        {/* Example Prompts */}
        <div className="space-y-2.5 mb-8">
          <p className="text-xs font-medium text-gray-500 mb-4 uppercase tracking-wider">
            Exemples de questions
          </p>
          {domain.examplePrompts.map((prompt, index) => (
            <button
              key={index}
              onClick={() => onPromptClick?.(prompt)}
              className="w-full text-left px-4 py-3.5 bg-white border border-gray-200 rounded-xl 
                hover:border-gray-300 hover:shadow-soft transition-all duration-200 
                group text-sm text-gray-700 hover:text-gray-900 flex items-center gap-3"
            >
              <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
                ${domainClasses.bgLight} ${domainClasses.text} group-hover:opacity-90 transition-opacity`}>
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="flex-1 text-left leading-relaxed">{prompt}</span>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100" />
            </button>
          ))}
        </div>

        {/* Hint */}
        <p className="text-xs text-gray-400">
          Commencez à taper votre question dans le champ ci-dessous
        </p>
      </div>
    </div>
  );
}
