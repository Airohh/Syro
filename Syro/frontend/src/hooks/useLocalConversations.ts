import { useState, useCallback } from 'react';
import { Message } from '../services/api';

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = 'syro_conversations';

function readFromStorage(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return [];
  }
}

function writeToStorage(conversations: Conversation[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch {
    // Storage full or unavailable — fail silently
  }
}

export function useLocalConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    readFromStorage().sort((a, b) => b.updatedAt - a.updatedAt)
  );

  const refresh = useCallback(() => {
    setConversations(readFromStorage().sort((a, b) => b.updatedAt - a.updatedAt));
  }, []);

  const save = useCallback((messages: Message[]): string | null => {
    if (messages.length === 0) return null;
    const stored = readFromStorage();
    const firstUser = messages.find(m => m.role === 'user');
    const title = firstUser?.content.slice(0, 50) || 'Nouvelle conversation';
    const conversation: Conversation = {
      id: crypto.randomUUID(),
      title,
      messages,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    writeToStorage([...stored, conversation]);
    refresh();
    return conversation.id;
  }, [refresh]);

  const update = useCallback((id: string, messages: Message[]): void => {
    if (messages.length === 0) return;
    const stored = readFromStorage();
    const idx = stored.findIndex(c => c.id === id);
    if (idx === -1) return;
    const firstUser = messages.find(m => m.role === 'user');
    stored[idx] = {
      ...stored[idx],
      title: firstUser?.content.slice(0, 50) || stored[idx].title,
      messages,
      updatedAt: Date.now(),
    };
    writeToStorage(stored);
    refresh();
  }, [refresh]);

  const remove = useCallback((id: string): void => {
    const stored = readFromStorage().filter(c => c.id !== id);
    writeToStorage(stored);
    refresh();
  }, [refresh]);

  return { conversations, save, update, remove };
}
