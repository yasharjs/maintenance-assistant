/* eslint-disable jsx-a11y/label-has-associated-control */
/* eslint-disable jsx-a11y/no-static-element-interactions */
import React, { useState } from "react";
import { ChevronLeft,
  ChevronRight,
  MessageSquare,
  MessageSquarePlus,
  Moon,
  Settings,
  Share,
  Sun,
  Trash2 } from "lucide-react";

import { Button } from "../components/ui/button";
import { Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger } from "../components/ui/dialog";
import { ScrollArea } from "../components/ui/scroll-area";
import { cn } from "../lib/utils";

interface Chat {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
}

interface ChatSidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  chats: Chat[];
  activeChat: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  onDeleteChat: (chatId: string) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onShareChat: (chatId: string) => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  chats,
  activeChat,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  isDarkMode,
  onToggleDarkMode,
  onShareChat
}) => {
  const [settingsOpen, setSettingsOpen] = useState(false);

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return "Today";
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <div
      className={cn(
        "h-screen bg-card border-r border-chat-border transition-all duration-300 flex flex-col",
        isCollapsed ? "w-16" : "w-80"
      )}
    >
      {/* Header */}
      <div className="p-4 border-b border-chat-border flex items-center justify-between">
        {!isCollapsed && (
          <Button
            onClick={onNewChat}
            className="flex-1 mr-2 bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            <MessageSquarePlus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="hover:bg-muted"
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Chat List */}
      <ScrollArea className="flex-1 p-2">
        {!isCollapsed ? (
          <div className="space-y-2">
            {chats.map(chat => (
              <div
                key={chat.id}
                className={cn(
                  "group relative p-3 rounded-lg cursor-pointer transition-all duration-200 hover:bg-muted",
                  activeChat === chat.id ? "bg-muted" : ""
                )}
                onClick={() => onSelectChat(chat.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-sm text-sidebar-foreground truncate">
                      {chat.title}
                    </h3>
                    <p className="text-xs text-sidebar-foreground mt-1 truncate">
                      {chat.lastMessage}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatTime(chat.timestamp)}
                    </p>
                  </div>
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex space-x-1 ml-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 hover:bg-destructive hover:text-destructive-foreground"
                      onClick={e => {
                        e.stopPropagation();
                        onDeleteChat(chat.id);
                      }}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={e => {
                        e.stopPropagation();
                        onShareChat(chat.id);
                      }}
                    >
                      <Share className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {chats.slice(0, 5).map(chat => (
              <Button
                key={chat.id}
                variant="ghost"
                size="icon"
                className={cn(
                  "w-12 h-12 mx-auto",
                  activeChat === chat.id ? "bg-muted" : ""
                )}
                onClick={() => onSelectChat(chat.id)}
              >
                <MessageSquare className="w-4 h-4" />
              </Button>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Settings at bottom */}
      <div className="p-4 border-t border-chat-border">
        <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
          <DialogTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                "w-full justify-start",
                isCollapsed ? "px-0 justify-center" : ""
              )}
            >
              <Settings className="w-4 h-4" />
              {!isCollapsed && <span className="ml-2">Settings</span>}
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Settings</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Dark Mode</label>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={onToggleDarkMode}
                >
                  {isDarkMode ? (
                    <Sun className="w-4 h-4" />
                  ) : (
                    <Moon className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default ChatSidebar;
