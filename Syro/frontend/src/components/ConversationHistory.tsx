import { useState, useEffect } from 'react';
import { MessageSquare, Clock, Trash2 } from 'lucide-react';
import { Message } from '../services/api';

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

interface ConversationHistoryProps {
  onSelectConversation: (messages: Message[], conversationId?: string) => void;
  onNewConversation: () => void;
}

export default function ConversationHistory({ 
  onSelectConversation, 
  onNewConversation 
}: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = () => {
    const stored = localStorage.getItem('syro_conversations');
    if (stored) {
      const parsed = JSON.parse(stored);
      setConversations(parsed.sort((a: Conversation, b: Conversation) => b.updatedAt - a.updatedAt));
    }
  };

  const saveConversation = (messages: Message[]): string | null => {
    if (messages.length === 0) return null;

    const conversations = JSON.parse(localStorage.getItem('syro_conversations') || '[]');
    const firstUserMessage = messages.find(m => m.role === 'user');
    const title = firstUserMessage?.content.substring(0, 50) || 'Nouvelle conversation';
    
    const conversation: Conversation = {
      id: Date.now().toString(),
      title,
      messages,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    conversations.push(conversation);
    localStorage.setItem('syro_conversations', JSON.stringify(conversations));
    loadConversations();
    return conversation.id;
  };

  const updateConversation = (id: string, messages: Message[]) => {
    if (messages.length === 0) return;

    const conversations = JSON.parse(localStorage.getItem('syro_conversations') || '[]');
    const conversationIndex = conversations.findIndex((c: Conversation) => c.id === id);
    
    if (conversationIndex !== -1) {
      // Mettre à jour la conversation existante
      const firstUserMessage = messages.find(m => m.role === 'user');
      const title = firstUserMessage?.content.substring(0, 50) || conversations[conversationIndex].title;
      
      conversations[conversationIndex] = {
        ...conversations[conversationIndex],
        title,
        messages,
        updatedAt: Date.now(),
      };
      
      localStorage.setItem('syro_conversations', JSON.stringify(conversations));
      loadConversations();
    }
  };

  const deleteConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const conversations = JSON.parse(localStorage.getItem('syro_conversations') || '[]');
    const filtered = conversations.filter((c: Conversation) => c.id !== id);
    localStorage.setItem('syro_conversations', JSON.stringify(filtered));
    loadConversations();
    if (selectedId === id) {
      onNewConversation();
    }
  };

  const handleSelect = (conversation: Conversation) => {
    setSelectedId(conversation.id);
    onSelectConversation(conversation.messages, conversation.id);
  };

  // Exposer les fonctions de sauvegarde et mise à jour
  useEffect(() => {
    (window as any).saveConversation = saveConversation;
    (window as any).updateConversation = updateConversation;
    return () => {
      delete (window as any).saveConversation;
      delete (window as any).updateConversation;
    };
  }, []);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Historique
        </h3>
        <button
          onClick={onNewConversation}
          className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          Nouveau
        </button>
      </div>

      {conversations.length === 0 ? (
        <div className="text-xs text-gray-400 text-center py-4">
          Aucune conversation
        </div>
      ) : (
        <div className="space-y-1 max-h-[400px] overflow-y-auto">
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              onClick={() => handleSelect(conversation)}
              className={`group relative px-2.5 py-2 rounded-lg cursor-pointer transition-colors ${
                selectedId === conversation.id
                  ? 'bg-gray-100 border border-gray-200'
                  : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start gap-2">
                <MessageSquare className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-gray-700 truncate">
                    {conversation.title}
                  </div>
                  <div className="flex items-center gap-1.5 mt-1">
                    <Clock className="w-3 h-3 text-gray-400" />
                    <span className="text-[10px] text-gray-400">
                      {new Date(conversation.updatedAt).toLocaleDateString('fr-FR', {
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => deleteConversation(conversation.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-200 transition-all"
                  title="Supprimer"
                >
                  <Trash2 className="w-3 h-3 text-gray-400 hover:text-red-600" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

