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
  placeholder = 'Posez votre question...',
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
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

  const canSend = input.trim() && !loading && !disabled;

  return (
    <div className="px-4 pb-4 pt-2 bg-zinc-950 border-t border-white/5">
      <div className="max-w-3xl mx-auto">
        <div className="bg-zinc-900 border border-white/8 rounded-2xl overflow-hidden
          focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/20
          transition-all duration-200">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="w-full px-4 pt-3.5 pb-2 bg-transparent text-zinc-100 resize-none
              outline-none text-sm font-sans leading-relaxed placeholder:text-zinc-600
              min-h-[52px] max-h-[180px]"
            disabled={loading || disabled}
            rows={1}
          />

          <div className="flex items-center justify-between px-3 pb-3 pt-1 gap-2">
            <div className="text-xs text-zinc-700">
              {input.length > 0 && (
                <span>{input.length} car.</span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span className="hidden sm:block text-xs text-zinc-700">
                <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-600 font-mono text-[10px]">⇧ Enter</kbd>
                {' '}nouvelle ligne
              </span>

              <button
                onClick={handleSend}
                disabled={!canSend}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                  transition-all duration-200 cursor-pointer
                  ${canSend
                    ? 'bg-blue-600 text-white hover:bg-blue-500 shadow-sm shadow-blue-500/20'
                    : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                  }`}
              >
                {loading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
                <span className="hidden sm:inline">{loading ? 'Envoi...' : 'Envoyer'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
