/*this file is component types for the application, defining the structure of chats, messages, and sidebar properties*/


export interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
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
}

export interface ShareDialogProps {
  isOpen: boolean;
  onClose: () => void;
  chatId: string;
  chatTitle: string;
}