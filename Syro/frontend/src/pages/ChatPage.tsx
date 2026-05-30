import { useState, useEffect, useRef } from 'react';
import { chatService, Message } from '../services/api';
import ChatBubble from '../components/ChatBubble';
import ChatInput from '../components/ChatInput';
import EmptyState from '../components/EmptyState';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import { domainService } from '../services/api';
import { getDomainConfig } from '../utils/domainConfig';
import { useLocalConversations } from '../hooks/useLocalConversations';

interface ChatPageProps {
  onLogout: () => void;
}

export default function ChatPage({ onLogout }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentDomain, setCurrentDomain] = useState<string>('general');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const { conversations, save, update, remove } = useLocalConversations();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Save/update conversation whenever messages change (not when loading history)
  useEffect(() => {
    if (isLoadingHistory || messages.length === 0) return;
    if (conversationId) {
      update(conversationId, messages);
    } else {
      const newId = save(messages);
      if (newId) setConversationId(newId);
    }
  }, [messages]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const loadDomain = async () => {
      try {
        const data = await domainService.getDomains('general');
        setCurrentDomain(data.current_domain || 'general');
      } catch {
        setCurrentDomain('general');
      }
    };
    loadDomain();
  }, []);

  useEffect(() => {
    setMessages([]);
    setConversationId(null);
  }, [currentDomain]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (content: string) => {
    if (!content.trim() || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
    };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await chatService.sendMessage(content, conversationId, undefined, currentDomain);
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.message,
        sources: response.sources,
        usage: response.usage,
      };
      setMessages(prev => [...prev, assistantMessage]);
      if (!conversationId) setConversationId(response.conversation_id);
    } catch (error: any) {
      const errorMsg = error?.userMessage || error?.message || 'Désolé, une erreur est survenue.';
      const errorSolution = error?.solution ? `\n\n💡 ${error.solution}` : '';
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `**Erreur**\n\n${errorMsg}${errorSolution}`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setIsLoadingHistory(false);
  };

  const handleSelectConversation = (msgs: Message[], convId: string) => {
    setIsLoadingHistory(true);
    setMessages(msgs.map(m => ({ ...m, id: m.id || crypto.randomUUID() })));
    setConversationId(convId);
    setTimeout(() => setIsLoadingHistory(false), 100);
  };

  const domain = getDomainConfig(currentDomain);

  return (
    <div className="flex h-screen bg-zinc-950 overflow-hidden">
      <Sidebar
        onLogout={onLogout}
        currentDomain={currentDomain}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
        conversations={conversations}
        onDeleteConversation={remove}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Header
          currentDomain={currentDomain}
          onDomainChange={setCurrentDomain}
        />

        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.length === 0 ? (
              <EmptyState
                domainId={currentDomain}
                onPromptClick={handleSend}
              />
            ) : (
              <>
                {messages.map((message) => (
                  <ChatBubble
                    key={message.id}
                    message={message}
                    domainId={currentDomain}
                  />
                ))}

                {loading && (
                  <div className="flex gap-3 items-center animate-fade-in">
                    <div className="w-7 h-7 rounded-lg bg-zinc-800 border border-white/6 flex items-center justify-center shrink-0">
                      <div className="flex gap-0.5">
                        {[0, 1, 2].map((i) => (
                          <div
                            key={i}
                            className="w-1 h-1 rounded-full bg-zinc-400 animate-bounce"
                            style={{ animationDelay: `${i * 150}ms` }}
                          />
                        ))}
                      </div>
                    </div>
                    <span className="text-xs text-zinc-600">
                      {domain.name} réfléchit...
                    </span>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>
        </div>

        <ChatInput
          onSend={handleSend}
          loading={loading}
          placeholder={`Posez une question sur ${getDomainConfig(currentDomain).shortName}...`}
        />
      </div>
    </div>
  );
}
