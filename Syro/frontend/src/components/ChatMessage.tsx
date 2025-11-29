import { Message, Source } from '../services/api';
import { User, Bot, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);

  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
          <Bot className="w-5 h-5 text-white" />
        </div>
      )}

      <div className={`flex-1 max-w-3xl ${isUser ? 'order-2' : ''}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-primary-600 text-white'
              : 'bg-white border border-gray-200 text-gray-900'
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              {showSources ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  Masquer les sources ({message.sources.length})
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  Voir les sources ({message.sources.length})
                </>
              )}
            </button>

            {showSources && (
              <div className="mt-2 space-y-2">
                {message.sources.map((source: Source, index: number) => (
                  <div
                    key={index}
                    className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-700">
                        Source {index + 1}
                      </span>
                      <span className="text-gray-500">
                        Score: {source.score.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-gray-600 text-xs line-clamp-3">
                      {source.text}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!isUser && message.usage && (
          <div className="mt-1 text-xs text-gray-500">
            Tokens utilisés: {message.usage}
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center order-1">
          <User className="w-5 h-5 text-gray-700" />
        </div>
      )}
    </div>
  );
}

