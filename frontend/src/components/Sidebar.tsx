/* eslint-disable object-curly-spacing */
/* Sidebar.tsx */
/* eslint-disable arrow-parens */
/* eslint-disable object-curly-newline */
/* eslint-disable simple-import-sort/imports */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable jsx-a11y/no-autofocus */
/* eslint-disable jsx-a11y/no-static-element-interactions */
/* eslint-disable indent */
/* eslint-disable react/jsx-indent */
/* eslint-disable jsx-a11y/label-has-associated-control */

import React, { useState } from 'react';
import {
  Plus, Search, MoreHorizontal, Trash2, Edit3, MessageSquare,
  Settings, Moon, Sun, ChevronLeft, ChevronRight, Share 
} from 'lucide-react';

import { useTheme } from '../components/ThemeProvider';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { ScrollArea } from '../components/ui/scroll-area';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/dropdown-menu';
import { Sidebar as UISidebar, SidebarContent, SidebarGroup, SidebarGroupContent, SidebarHeader, SidebarFooter, useSidebar } from '../components/ui/sidebar';
import { cn } from '../lib/utils';
import logoImage from '@/assets/logo.png';
import type {SidebarProps } from "@/types/chats";


const Sidebar: React.FC<SidebarProps> = ({
  chats,
  activeChat,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onRenameChat,
  isCollapsed,
  onToggleCollapse,
  onToggleDarkMode,
  onShareChat
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const { theme, setTheme } = useTheme();
  const { setOpen } = useSidebar();
  const filteredChats = chats.filter(chat =>
    chat.title?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleRename = (chatId: string, title: string) => {
    setRenamingId(chatId);
    setRenameValue(title);
  };

  const confirmRename = (chatId: string) => {
    if (renameValue.trim()) {
      onRenameChat(chatId, renameValue.trim());
    }
    setRenamingId(null);
    setRenameValue('');
  };

  const cancelRename = () => {
    setRenamingId(null);
    setRenameValue('');
  };

const formatTime = (date: Date) => {
  const now = new Date();
  let days = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (days < 0) days = 0;

  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days <= 5) return `${days} days ago`;
  return "7+ days ago";
};


  return (
    <UISidebar
      className={cn(
        "transition-all duration-300 flex flex-col",
        isCollapsed ? "w-16" : "w-80"
      )}
    >
      {/* Header */}
      <SidebarHeader>
        <div className="p-4 space-y-4 border-b border-sidebar-border">
          <div className="flex items-center justify-between">
            {!isCollapsed && (
              <div className="flex items-center gap-2">
                <img src={logoImage} alt="Logo" className="w-10 h-10 rounded-sm" />
                <h2 className="font-semibold text-sidebar-foreground text-sm"> </h2>
              </div>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="hover:bg-muted"
            >
              {/* {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />} */}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setOpen(false)}
              className="hover:bg-muted"
              title="Close sidebar"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </div>

          {!isCollapsed && (
            <>
              <Button
                onClick={onNewChat}
                className="w-full justify-center text-xs h-8 bg-gradient-to-r from-sidebar-accent to-sidebar-accent/80 hover:from-sidebar-accent/90 hover:to-sidebar-accent text-sidebar-foreground border border-sidebar-border/30 rounded-lg group"
                variant="ghost"
              >
                <Plus className="w-3.5 h-3.5 mr-1.5 group-hover:rotate-90 transition-transform duration-300" />
                New Chat
              </Button>

              <div className="relative group">
                <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-sidebar-foreground/40" />
                <Input
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 h-8 text-xs bg-sidebar-accent/30 border border-sidebar-border/20 rounded-lg"
                />
              </div>
            </>
          )}
        </div>
      </SidebarHeader>
      {/* Chat List */}
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            {!isCollapsed ? (
              <ScrollArea className="flex-1 [&>[data-radix-scroll-area-viewport]]:bg-transparent [&>[data-radix-scroll-area-scrollbar]]:bg-sidebar-accent/20 [&>[data-radix-scroll-area-thumb]]:bg-sidebar-border hover:[&>[data-radix-scroll-area-thumb]]:bg-sidebar-foreground/30 [&>[data-radix-scroll-area-scrollbar]]:w-2 [&>[data-radix-scroll-area-scrollbar]]:border-0">
                <div className="p-2 w-full">
                  {filteredChats.length === 0 ? (
                    <div className="text-center py-8 text-sidebar-foreground/50">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2" />
                      <p className="text-sm">No chats found</p>
                    </div>
                  ) : (
                    filteredChats.map(chat => (
                      <div
                        key={chat.id}
                        className={cn(
                          "group relative mb-1 rounded-lg transition-all duration-200 ease-in-out animate-fade-in w-full",
                          activeChat === chat.id ? "bg-sidebar-accent" : "hover:bg-sidebar-accent/50"
                        )}
                      >
                          <div
                            className="flex items-start justify-start p-3 cursor-pointer w-full"
                            onClick={() => onSelectChat(chat.id)}
>
                          <div className="flex-1 min-w-0 mr-2 text-left">
                            {renamingId === chat.id ? (
                              <Input
                                value={renameValue}
                                onChange={e => setRenameValue(e.target.value)}
                                onBlur={() => confirmRename(chat.id)}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') confirmRename(chat.id);
                                  if (e.key === 'Escape') cancelRename();
                                }}
                                className="w-full h-6 text-sm p-1 bg-sidebar border-sidebar-border"
                                autoFocus
                              />
                            ) : (
                              <>
                                <h3 className="text-sm font-medium text-sidebar-foreground truncate mb-1 max-w-[200px]">
                                  {chat.title?.trim() ||
                                    chat.messages?.[0]?.content?.slice(0, 40) ||
                                    "New Chat"}
                                </h3>
                                <p className="text-xs text-sidebar-foreground/60 truncate">
                                  {chat.lastMessage}
                                </p>
                                <p className="text-xs text-muted-foreground mt-1">
                                {formatTime(chat.timestamp)}
                                </p>
                              </>
                            )}
                          </div>

                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0 text-sidebar-foreground/50 hover:text-sidebar-foreground"
                                onClick={e => e.stopPropagation()}
                              >
                                <MoreHorizontal className="w-4 h-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-40">
                              <DropdownMenuItem onClick={() => handleRename(chat.id, chat.title)} className="text-sm">
                                <Edit3 className="w-4 h-4 mr-2" />
                                Rename
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => onShareChat(chat.id)}
                                className="text-sm"
                                >
                                <Share className="w-4 h-4 mr-2" />
                                Share
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => onDeleteChat(chat.id)} className="text-sm text-destructive focus:text-destructive">
                                <Trash2 className="w-4 h-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            ) : (
              <ScrollArea className="flex-1 p-2">
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
              </ScrollArea>
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* Footer / Settings */}
      <SidebarFooter>
        <div className="p-4 border-t border-sidebar-border/30">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className={cn(
                  "w-full justify-start",
                  isCollapsed ? "px-0 justify-center" : ""
                )}
              >
                <Settings className="w-4 h-4" />
                {!isCollapsed && <span className="ml-2">Theme</span>}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              side="top"
              sideOffset={4}
              className="w-48 bg-background border border-border shadow-lg z-50"
            >
              <DropdownMenuItem
                onClick={() => setTheme(theme === "light" ? "dark" : "light")}
                className="flex items-center gap-2 cursor-pointer"
              >
                {theme === "light" ? (
                  <>
                    <Moon className="w-4 h-4" />
                    <span>Dark Mode</span>
                  </>
                ) : (
                  <>
                    <Sun className="w-4 h-4" />
                    <span>Light Mode</span>
                  </>
                )}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </SidebarFooter>
    </UISidebar>
  );
};

export default Sidebar;
