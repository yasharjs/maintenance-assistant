/*this file is component types for the application, defining the structure of chats, messages, and sidebar properties*/


export interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
  citations?: Citation[]; 
}

export interface Chat {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messages: Message[];
}

export interface SidebarProps {
  chats: Chat[];
  activeChat: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  onDeleteChat: (chatId: string) => void;
  onRenameChat: (chatId: string, newTitle: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onShareChat: (chatId: string) => void;
}

export interface ChatInterfaceProps { 
  messages: Message[];
  onSendMessage: (content: string) => void;
  isLoading: boolean;
  chatTitle?: string;
  onShareChat?: () => void;
  onStopGeneration?: () => void;
  showCentered?: boolean;
  isCollapsed?: boolean;
}

export interface ShareDialogProps {
  isOpen: boolean;
  onClose: () => void;
  chatId: string;
  chatTitle: string;
}

export type Citation = {
  id?: string;
  title?: string;
  url?: string;        // image or pdf-to-image preview URL
  filepath?: string;
  part_index?: number;
  chunk_id?: string;
  locator?: string;    // e.g., "L10–L20" or "p. 16"
};

// If you already have ChatMessageUI/Message type, add:
export type ChatMessageUI = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: Citation[];   // <-- new (optional)
};
