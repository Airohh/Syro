import { useState, useEffect, useRef } from 'react';
import { chatService, Message } from '../services/api';
import ChatBubble from '../components/ChatBubble';
import ChatInput from '../components/ChatInput';
import EmptyState from '../components/EmptyState';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import { domainService } from '../services/api';
import { getDomainConfig } from '../utils/domainConfig';

interface ChatPageProps {
  onLogout: () => void;
}

export default function ChatPage({ onLogout }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentDomain, setCurrentDomain] = useState<string>('general');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Load current domain from API
  // NOTE: Avec l'architecture multi-domaines, un seul appel suffit car tous les domaines utilisent le même backend (port 8000)
  useEffect(() => {
    const loadDomain = async () => {
      try {
        // Un seul appel suffit car tous les domaines utilisent le même backend
        const data = await domainService.getDomains('general');
        if (data.current_domain) {
          setCurrentDomain(data.current_domain);
          console.log(`✓ Domaine chargé avec succès: ${data.current_domain}`);
        } else {
          // Fallback si pas de domaine retourné
          setCurrentDomain('general');
          console.log('✓ Utilisation du domaine par défaut: general');
        }
      } catch (error) {
        // En cas d'erreur, utiliser 'general' par défaut
        console.warn('⚠ Erreur lors du chargement du domaine, utilisation du domaine par défaut:', error);
        setCurrentDomain('general');
      }
    };
    
    loadDomain();
  }, []);

  // Réinitialiser la conversation quand le domaine change
  useEffect(() => {
    setMessages([]);
    setConversationId(null);
    setSelectedId(null);
    setCurrentConversationId(null);
    setIsLoadingConversation(false);
  }, [currentDomain]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (content: string) => {
    if (!content.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: content,
    };
    setMessages((prev: Message[]) => [...prev, userMessage]);
    setLoading(true);

    try {
      // Passer le domaine actuel pour utiliser le bon port API
      const response = await chatService.sendMessage(content, conversationId, undefined, currentDomain);
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.message,
        sources: response.sources,
        usage: response.usage,
      };
      setMessages((prev: Message[]) => [...prev, assistantMessage]);
      setConversationId(response.conversation_id);
      // Si on a un ID de conversation actuel, le garder, sinon utiliser le nouveau
      if (!currentConversationId) {
        setCurrentConversationId(response.conversation_id);
      }
    } catch (error: any) {
      console.error('Error sending message:', error);
      // Utiliser le message user-friendly si disponible, sinon le message par défaut
      const errorMsg = error?.userMessage || error?.message || 'Désolé, une erreur est survenue.';
      const errorSolution = error?.solution ? `\n\n💡 ${error.solution}` : '';
      const errorAction = error?.action ? `\n\n🔧 ${error.action}` : '';
      
      const errorMessage: Message = {
        role: 'assistant',
        content: `❌ **Erreur**\n\n${errorMsg}${errorSolution}${errorAction}`,
      };
      setMessages((prev: Message[]) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = (prompt: string) => {
    handleSend(prompt);
  };

  // _selectedId: ID de la conversation sélectionnée dans l'historique (pour synchronisation future)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setSelectedId(null);
    setCurrentConversationId(null);
    setIsLoadingConversation(false);
  };

  const handleSelectConversation = (messages: Message[], conversationId?: string) => {
    setIsLoadingConversation(true);
    setMessages(messages);
    setSelectedId(conversationId || null);
    setCurrentConversationId(conversationId || null);
    // Ne pas sauvegarder immédiatement, on est en train de charger
    setTimeout(() => setIsLoadingConversation(false), 100);
  };

  // Sauvegarder la conversation quand elle change (mais pas si on charge depuis l'historique)
  useEffect(() => {
    // Ne pas sauvegarder si :
    // 1. On est en train de charger une conversation depuis l'historique
    // 2. Il n'y a pas de messages
    if (isLoadingConversation || messages.length === 0) {
      return;
    }

    // Si on a un ID de conversation (chargée depuis l'historique), mettre à jour l'existante
    if (currentConversationId && (window as any).updateConversation) {
      (window as any).updateConversation(currentConversationId, messages);
    } else if ((window as any).saveConversation) {
      // Sinon, créer une nouvelle conversation (première fois qu'on envoie un message)
      const newId = (window as any).saveConversation(messages);
      if (newId) {
        setCurrentConversationId(newId);
        setSelectedId(newId);
      }
    }
  }, [messages, isLoadingConversation, currentConversationId]);

  // Exposer la fonction pour la Sidebar
  useEffect(() => {
    (window as any).onNewConversation = handleNewConversation;
    return () => {
      delete (window as any).onNewConversation;
    };
  }, []);

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      <Sidebar 
        onLogout={onLogout} 
        currentDomain={currentDomain}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
      />
      
      <div className="flex-1 flex flex-col min-w-0 bg-gray-50">
        <Header 
          currentDomain={currentDomain} 
          onDomainChange={setCurrentDomain}
        />

        {/* Messages area */}
        <div 
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto px-6 py-8"
        >
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 ? (
              <EmptyState 
                domainId={currentDomain} 
                onPromptClick={handlePromptClick}
              />
            ) : (
              <>
                {messages.map((message, index) => (
                  <ChatBubble 
                    key={index} 
                    message={message} 
                    domainId={currentDomain}
                  />
                ))}
                {loading && (
                  <div className="flex items-center gap-3 text-gray-500 animate-fade-in">
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-gray-600"></div>
                    </div>
                    <span className="text-sm">Réflexion en cours...</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>
        </div>

        {/* Input */}
        <ChatInput 
          onSend={handleSend} 
          loading={loading}
          placeholder={`Posez une question sur ${getDomainConfig(currentDomain).shortName}...`}
        />
      </div>
    </div>
  );
}
