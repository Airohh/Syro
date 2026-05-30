import { Message, Source } from '../services/api';
import { User, Copy, Check, ChevronDown, ChevronUp, ExternalLink, FileText } from 'lucide-react';
import { useState } from 'react';
import DOMPurify from 'dompurify';
import { getDomainConfig } from '../utils/domainConfig';
import { getDomainClasses } from '../utils/domainStyles';

interface ChatBubbleProps {
  message: Message;
  domainId?: string;
}

function renderContent(text: string): { __html: string } {
  // Escape HTML first
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Split on code blocks, process each part separately
  const parts: string[] = [];
  const codeBlockRe = /```(\w*)\n?([\s\S]*?)```/g;
  let last = 0;
  let m: RegExpExecArray | null;

  while ((m = codeBlockRe.exec(text)) !== null) {
    if (m.index > last) parts.push(processText(text.slice(last, m.index), esc));
    const code = esc(m[2].trim());
    const lang = m[1] ? `<span class="text-[10px] text-zinc-600 uppercase tracking-widest font-mono mr-2">${esc(m[1])}</span>` : '';
    parts.push(
      `<pre class="bg-zinc-800/70 border border-white/5 rounded-xl p-4 my-3 overflow-x-auto text-xs font-mono text-zinc-200 leading-relaxed">${lang}${code}</pre>`
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(processText(text.slice(last), esc));

  return { __html: DOMPurify.sanitize(parts.join(''), { ADD_ATTR: ['class'] }) };
}

function processText(text: string, esc: (s: string) => string): string {
  let html = esc(text);
  // Headings
  html = html.replace(/^### (.+)$/gm, '<h3 class="text-sm font-semibold text-zinc-200 mt-3 mb-1">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2 class="text-base font-semibold text-zinc-100 mt-4 mb-1.5">$1</h2>');
  // Bold + italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong class="font-semibold text-zinc-100"><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-zinc-100">$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em class="italic text-zinc-400">$1</em>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="bg-zinc-800 text-blue-300 px-1.5 py-0.5 rounded text-xs font-mono">$1</code>');
  // List items
  html = html.replace(/^[\-\*] (.+)$/gm,
    '<div class="flex gap-2 items-start py-0.5"><span class="text-zinc-600 mt-0.5 shrink-0 text-xs">▸</span><span class="text-zinc-300 text-sm">$1</span></div>'
  );
  // Paragraphs
  const paras = html.split(/\n\n+/);
  return paras
    .filter(p => p.trim())
    .map(p => {
      const trimmed = p.trim();
      if (trimmed.startsWith('<h') || trimmed.startsWith('<pre') || trimmed.startsWith('<div')) return trimmed;
      return `<p class="text-zinc-300 text-sm leading-relaxed mb-2">${trimmed.replace(/\n/g, '<br />')}</p>`;
    })
    .join('');
}

export default function ChatBubble({ message, domainId = 'general' }: ChatBubbleProps) {
  const [showSources, setShowSources] = useState(false);
  const [copied, setCopied] = useState(false);
  const domain = getDomainConfig(domainId);
  const domainClasses = getDomainClasses(domainId);
  const borderLeftClass = domainClasses.border.replace(/^border-/, 'border-l-');
  const isUser = message.role === 'user';
  const Icon = domain.icon;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex gap-3 justify-end animate-fade-in">
        <div className="flex flex-col items-end gap-1 max-w-[80%] md:max-w-[70%]">
          <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm shadow-blue-500/10">
            <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
              {message.content}
            </p>
          </div>
        </div>
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-zinc-800 border border-white/8 flex items-center justify-center mt-0.5">
          <User className="w-3.5 h-3.5 text-zinc-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 justify-start animate-fade-in group">
      {/* Domain icon */}
      <div className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center mt-0.5
        ${domainClasses.bgLight} ${domainClasses.text}`}>
        <Icon className="w-3.5 h-3.5" />
      </div>

      <div className="flex flex-col gap-2 max-w-[85%] md:max-w-[75%]">
        {/* Message card */}
        <div className={`bg-zinc-900 border border-white/6 border-l-2 ${borderLeftClass} rounded-2xl rounded-tl-sm px-4 py-3`}>
          <div
            className="prose-dark"
            dangerouslySetInnerHTML={renderContent(message.content)}
          />
        </div>

        {/* Action bar */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150 px-1">
          <button
            onClick={handleCopy}
            aria-label="Copier le message"
            className="flex items-center gap-1.5 px-2 py-1 rounded-md text-zinc-600 hover:text-zinc-300
              hover:bg-zinc-800 transition-all duration-150 cursor-pointer text-xs"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-emerald-500" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
            {copied ? 'Copié' : 'Copier'}
          </button>

          {message.usage && (
            <span className="text-xs text-zinc-700 px-1">{message.usage} tokens</span>
          )}

          {message.sources && message.sources.length > 0 && (
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1.5 px-2 py-1 rounded-md text-zinc-600 hover:text-zinc-300
                hover:bg-zinc-800 transition-all duration-150 cursor-pointer text-xs ml-auto"
            >
              <FileText className="w-3.5 h-3.5" />
              {showSources ? (
                <>Masquer <ChevronUp className="w-3 h-3" /></>
              ) : (
                <>{message.sources.length} source{message.sources.length > 1 ? 's' : ''} <ChevronDown className="w-3 h-3" /></>
              )}
            </button>
          )}
        </div>

        {/* Sources */}
        {showSources && message.sources && message.sources.length > 0 && (
          <div className="space-y-2 animate-slide-up">
            {message.sources.map((source: Source, index: number) => (
              <div
                key={index}
                className="bg-zinc-900/60 border border-white/5 rounded-xl p-3 text-xs
                  hover:bg-zinc-800/60 hover:border-white/8 transition-all duration-150"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-medium text-zinc-400">Source {index + 1}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-600 font-mono">
                      {(source.score * 100).toFixed(0)}%
                    </span>
                    {source.metadata?.url && (
                      <a
                        href={source.metadata.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label="Ouvrir la source"
                        className="text-zinc-600 hover:text-blue-400 transition-colors cursor-pointer"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
                <p className="text-zinc-500 line-clamp-2 leading-relaxed">
                  {source.text}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
