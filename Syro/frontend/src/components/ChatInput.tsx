import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  loading?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({ 
  onSend, 
  loading = false, 
  disabled = false,
  placeholder = "Posez votre question..."
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || loading || disabled) return;
    onSend(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-white border-t border-gray-200 px-6 py-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="textarea-field min-h-[52px] max-h-[200px] pr-14"
              disabled={loading || disabled}
              rows={1}
            />
            <div className="absolute bottom-3 right-3 text-xs text-gray-400 pointer-events-none">
              {input.length > 0 && (
                <span className="bg-white/80 px-1.5 py-0.5 rounded">
                  {input.length}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={handleSend}
            disabled={loading || disabled || !input.trim()}
            className="btn-primary px-5 py-3 h-[52px] disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">Envoyer</span>
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-400 text-center">
          <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 font-mono">Entrée</kbd> pour envoyer, 
          <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 font-mono ml-1">Shift + Entrée</kbd> pour une nouvelle ligne
        </div>
      </div>
    </div>
  );
}
