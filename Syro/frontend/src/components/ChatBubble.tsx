import { Message, Source } from '../services/api';
import { User, Copy, Check, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { useState } from 'react';
import { getDomainConfig } from '../utils/domainConfig';
import { getDomainClasses } from '../utils/domainStyles';

interface ChatBubbleProps {
  message: Message;
  domainId?: string;
}

export default function ChatBubble({ message, domainId = 'general' }: ChatBubbleProps) {
  const [showSources, setShowSources] = useState(false);
  const [copied, setCopied] = useState(false);
  const domain = getDomainConfig(domainId);
  const domainClasses = getDomainClasses(domainId);
  const isUser = message.role === 'user';
  const Icon = domain.icon;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-3 group ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      {!isUser && (
        <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center 
          ${domainClasses.bgLight} ${domainClasses.text} shadow-soft`}>
          <Icon className="w-4 h-4" />
        </div>
      )}

      <div className={`flex flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'} max-w-[85%] md:max-w-[75%]`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? `${domainClasses.bg} text-white shadow-soft`
              : 'bg-white border border-gray-200 text-gray-900 shadow-soft'
          }`}
        >
          <div className="whitespace-pre-wrap text-sm leading-relaxed break-words">
            {message.content}
          </div>
        </div>

        {/* Actions bar */}
        {!isUser && (
          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
              title="Copier"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-green-600" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        )}

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="w-full">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors px-2 py-1 rounded-lg hover:bg-gray-50"
            >
              {showSources ? (
                <>
                  <ChevronUp className="w-3.5 h-3.5" />
                  <span>Masquer les sources ({message.sources.length})</span>
                </>
              ) : (
                <>
                  <ChevronDown className="w-3.5 h-3.5" />
                  <span>Voir les sources ({message.sources.length})</span>
                </>
              )}
            </button>

            {showSources && (
              <div className="mt-2 space-y-2 animate-slide-up">
                {message.sources.map((source: Source, index: number) => (
                  <div
                    key={index}
                    className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-xs hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <span className="font-medium text-gray-700">
                        Source {index + 1}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">
                          {source.score.toFixed(2)}
                        </span>
                        {source.metadata?.url && (
                          <a
                            href={source.metadata.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-gray-400 hover:text-gray-600"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>
                    <p className="text-gray-600 line-clamp-2 leading-relaxed">
                      {source.text}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Usage info */}
        {!isUser && message.usage && (
          <div className="text-xs text-gray-400 px-1">
            {message.usage} tokens
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gray-200 flex items-center justify-center">
          <User className="w-4 h-4 text-gray-600" />
        </div>
      )}
    </div>
  );
}

