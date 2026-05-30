import { useState } from 'react';
import { MessageSquare, Clock, Trash2, Plus } from 'lucide-react';
import { Message } from '../services/api';
import { Conversation } from '../hooks/useLocalConversations';

interface ConversationHistoryProps {
  conversations: Conversation[];
  onSelect: (messages: Message[], conversationId: string) => void;
  onDelete: (id: string) => void;
  onNewConversation: () => void;
}

export default function ConversationHistory({
  conversations,
  onSelect,
  onDelete,
  onNewConversation,
}: ConversationHistoryProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleSelect = (conv: Conversation) => {
    setSelectedId(conv.id);
    onSelect(conv.messages, conv.id);
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(id);
    if (selectedId === id) {
      setSelectedId(null);
      onNewConversation();
    }
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-2 px-1">
        <p className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest">
          Historique
        </p>
        <button
          onClick={onNewConversation}
          title="Nouvelle conversation"
          className="p-0.5 rounded text-zinc-700 hover:text-zinc-300 hover:bg-zinc-800 transition-all duration-150 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {conversations.length === 0 ? (
        <p className="text-xs text-zinc-700 text-center py-4 px-1">
          Aucune conversation
        </p>
      ) : (
        <div className="space-y-0.5 max-h-[360px] overflow-y-auto">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => handleSelect(conv)}
              className={`group relative flex items-start gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-all duration-150 ${
                selectedId === conv.id
                  ? 'bg-zinc-800 border border-white/8'
                  : 'hover:bg-zinc-900/80'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5 text-zinc-600 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-zinc-300 truncate leading-snug">{conv.title}</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <Clock className="w-2.5 h-2.5 text-zinc-700" />
                  <span className="text-[10px] text-zinc-700">
                    {new Date(conv.updatedAt).toLocaleDateString('fr-FR', {
                      day: '2-digit',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              </div>
              <button
                onClick={(e) => handleDelete(conv.id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-zinc-700 transition-all duration-150 shrink-0"
                title="Supprimer"
              >
                <Trash2 className="w-3 h-3 text-zinc-500 hover:text-red-400" />
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
