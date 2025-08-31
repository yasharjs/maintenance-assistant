/* eslint-disable jsx-a11y/no-static-element-interactions */
/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable arrow-parens */
/* eslint-disable comma-dangle */
/* eslint-disable react/jsx-indent-props */

/* eslint-disable import/no-extraneous-dependencies */
/* eslint-disable object-curly-spacing */
/* eslint-disable no-empty */
/* eslint-disable no-constant-condition */
/* eslint-disable prefer-const */
/* eslint-disable object-curly-newline */
/* eslint-disable indent */
/* eslint-disable @typescript-eslint/no-unused-vars */
// eslint-disable-next-line simple-import-sort/imports
import React, { useContext, useEffect, useMemo, useState } from "react";
import { Clock, Menu, Plus, Search } from "lucide-react";
import { v4 as uuid } from "uuid";
import { conversationApi,
  frontendSettings,
  historyDelete,
  historyGenerate,
  historyList,
  historyRead,
  historyRename, 
  historyUpdate} from "../api/api";
import { ConversationRequest, ChatMessage, Conversation } from "../api/models";
import ChatInterface from "../components/ChatInterface";
import ShareDialog from "../components/ShareDialog";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { SidebarProvider, useSidebar } from "../components/ui/sidebar";
import { ScrollArea } from "../components/ui/scroll-area";
import { useToast } from "../hooks/use-toast";
import { AppStateContext } from "../state/AppProvider";
import { useTheme } from "../components/ThemeProvider";
import Sidebar from "../components/Sidebar";
import type { Chat } from "@/types/chats";

// Roles from old Chat.tsx
const ASSISTANT = "assistant";
const TOOL = "tool";
const ERROR = "error";


// Parse citations from tool messages (for UI if needed later)
const parseCitationFromMessage = (message: ChatMessage) => {
  if (message?.role === 'tool' && typeof message?.content === "string") {
    try {
      const toolMessage = JSON.parse(message.content);
      return toolMessage.citations || [];
    } catch {
      return [];
    }
  }
  return [];
};

// Pretty error formatting from old Chat.tsx
const tryGetRaiPrettyError = (errorMessage: string) => {
  try {
    const match = errorMessage.match(/'innererror': ({.*})\}\}/);
    if (match) {
      const fixedJson = match[1]
        .replace(/'/g, '"')
        .replace(/\bTrue\b/g, 'true')
        .replace(/\bFalse\b/g, 'false');
      const innerErrorJson = JSON.parse(fixedJson);
      if (innerErrorJson?.content_filter_result?.jailbreak?.filtered) {
        return `Prompt blocked by Azure OpenAI’s content filter. Reason: Jailbreak`;
      }
    }
  } catch {}
  return errorMessage;
};

const parseErrorMessage = (errorMessage: string) => {
  const innerErrorCue = "{\\'error\\': {\\'message\\': ";
  if (errorMessage.includes(innerErrorCue)) {
    try {
      let innerErrorString = errorMessage.substring(errorMessage.indexOf(innerErrorCue));
      innerErrorString = innerErrorString.replaceAll("\\'", "'");
      return tryGetRaiPrettyError(innerErrorString);
    } catch {}
  }
  return tryGetRaiPrettyError(errorMessage);
};


const MainContent = () => {
  const appStateContext = useContext(AppStateContext);
  const [activeChat, setActiveChat] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareDialogChatId, setShareDialogChatId] = useState<string>("");
  const [isOpen, setIsOpen] = useState(false); // Single state for sidebar
  const { toast } = useToast();
  const [scrollSignal, setScrollSignal] = useState(0);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchText, setSearchText] = useState("");


  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setIsOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

 const toggleSidebar = () => {
    setIsOpen((prev) => !prev);
  };

// Load chat history
useEffect(() => {
  async function loadSettings() {
    try {
      const settingsData = await frontendSettings();
      if (settingsData) {
        appStateContext?.dispatch({
          type: "FETCH_FRONTEND_SETTINGS",
          payload: settingsData
        });
      }
    } catch (err) {
      console.error("Failed to fetch frontend settings", err);
    }
  }
  loadSettings();
}, []);


// Load frontend settings
useEffect(() => {
  async function loadHistory() {
    try {
      const chatHistory = await historyList();

      if (chatHistory) {
        // Fill missing titles with a fallback before dispatch
        const filledHistory = chatHistory.map(chat => ({
          ...chat,
          title: chat.title?.trim() || "Untitled Chat"
        }));

        appStateContext?.dispatch({
          type: "FETCH_CHAT_HISTORY",
          payload: filledHistory
        });
      }
    } catch (err) {
      console.error("Failed to load chat history", err);
    }
  }
  loadHistory();
}, []);
  
  // Get data from AppStateContext
  const chats = appStateContext?.state.chatHistory || [];
  const currentChat = appStateContext?.state.currentChat;
  const settings = appStateContext?.state.frontendSettings;
  const renderedMessages = useMemo(
  () =>
    (currentChat?.messages?.map(m => ({
      id: m.id,
      content: typeof m.content === "string" ? m.content : "",
      role: m.role as "user" | "assistant",
      timestamp: m.createdAt ? new Date(m.createdAt) : new Date(),
      citations: Array.isArray((m as any).citations) ? (m as any).citations : []
    })) || []),
  [currentChat?.messages]
);


  function normalizeContent(content: any): string {
    if (typeof content === "string") return content;
    if (Array.isArray(content)) {
      return content
        .map(part => {
          if (typeof part === "string") return part;
          if (part?.type === "text" && part?.text) return part.text;
          if (part?.type === "image_url" && part?.image_url?.url) {
            return `[Image: ${part.image_url.url}]`;
          }
          return "";
        })
        .filter(Boolean)
        .join(" ");
    }
    return "";
  }

  // Convert AppState chat history to local format
const truncateString = (str: string, n: number) =>
  str && str.length > n ? str.slice(0, n) + "…" : str;

const mappedChats: Chat[] = (chats || []).map(conv => {
  let safeTitle = "";

  // Case 1: Title is a string
  if (typeof conv.title === "string") {
    safeTitle = conv.title.trim();
  }

  // Case 2: Title is an array
  else if (Array.isArray(conv.title)) {
    const firstBlock: any = conv.title[0]; // use any here to avoid never

    if (
      firstBlock &&
      typeof firstBlock === "object" &&
      "type" in firstBlock &&
      firstBlock.type === "text" &&
      "text" in firstBlock &&
      typeof firstBlock.text === "string"
    ) {
      safeTitle = firstBlock.text.trim();
    }
  }

  // Fallback: First message content
  if (!safeTitle) {
    safeTitle =
      typeof conv.messages?.[0]?.content === "string"
        ? conv.messages[0].content
        : "New Chat";
  }
    const lastMsg =
    Array.isArray(conv.messages) && conv.messages.length
      ? conv.messages[conv.messages.length - 1]
      : undefined;

  return {
    id: conv.id,
    title: truncateString(safeTitle, 40), // always a string now
    lastMessage: truncateString(
      normalizeContent(typeof lastMsg?.content === "string" ? lastMsg.content : ""),
      35
    ),
    timestamp: conv.date ? new Date(conv.date) : new Date(),
    messages: (conv.messages || []).map(m => ({
      id: m.id,
      content: normalizeContent(m.content),
      role: m.role as "user" | "assistant",
      timestamp: m.createdAt ? new Date(m.createdAt) : new Date(),      
      citations: Array.isArray(m.citations) ? m.citations : []
    }))
  };
});

  const filteredModalChats = useMemo(() => {
    const q = searchText.trim().toLowerCase();
    if (!q) return mappedChats.slice(0, 20);
    return mappedChats
      .filter(c => (c.title?.toLowerCase().includes(q) || c.lastMessage?.toLowerCase().includes(q)))
      .slice(0, 20);
  }, [searchText, mappedChats]);

  // Pretty timestamp format like the sidebar
  const formatTime = (date: Date) => {
    const now = new Date();
    let days = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    if (days < 0) days = 0;
    if (days === 0) return "Today";
    if (days === 1) return "Yesterday";
    if (days <= 5) return `${days} days ago`;
    return "7+ days ago";
  };


const getCurrentChat = () => {

    return mappedChats.find(chat => chat.id === activeChat);
  };

  // Select a chat and load it in AppState
const handleSelectChat = async (chatId: string) => {
  setActiveChat(chatId);

  try {
    // Find chat from mapped list
    const chat = mappedChats.find(c => c.id === chatId);
    if (!chat) return;

    // Load messages for this chat
    
    let messages = await historyRead(chatId);

    // FIX: Normalize citations for each message
    messages = (messages || []).map(m => ({
      ...m,
      citations: Array.isArray(m.citations) ? m.citations : []
    }));

    // Create a proper Conversation object
    const updatedChat: Conversation = {
      id: chat.id,
      title: chat.title,
      date: chat.timestamp.toISOString(),
      messages
    };

    // Dispatch full Conversation
    appStateContext?.dispatch({
      type: "UPDATE_CURRENT_CHAT",
      payload: updatedChat
    });

    setScrollSignal(s => s + 1);
  } catch (err) {
    console.error("Failed to load chat messages", err);
  }
};


  // Delete chat using AppState
  const handleDeleteChat = async (chatId: string) => {
    try {
      await historyDelete(chatId);
      appStateContext?.dispatch({ type: 'DELETE_CHAT_ENTRY', payload: chatId });
      if (activeChat === chatId) {
        setActiveChat(null);
      }
      toast({
        title: "Chat deleted",
        description: "The conversation has been removed."
      });
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to delete chat.",
        variant: "destructive"
      });
    }
  };

  // Rename chat using AppState
  const handleRenameChat = async (chatId: string, newTitle: string) => {
    try {
      await historyRename(chatId, newTitle);
      appStateContext?.dispatch({ 
        type: 'UPDATE_CHAT_TITLE', 
        payload: { id: chatId, title: newTitle } as any
      });
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to rename chat.",
        variant: "destructive"
      });
    }
  };

  // Create new chat
  const handleNewChat = async () => {
    setActiveChat(null);
    appStateContext?.dispatch({ type: 'UPDATE_CURRENT_CHAT', payload: null });
  };

  const handleShareChat = (chatId: string) => {
    setShareDialogChatId(chatId);
    setShareDialogOpen(true);
  };

  // Send message using proper backend integration
 const handleSendMessage = async (content: string) => {
  const userMessage: ChatMessage = {
    id: Date.now().toString(),
    role: "user",
    content,
    date: new Date().toISOString()
  };

  setIsLoading(true);
  const abortController = new AbortController();
  let conversation = currentChat;
  let request: ConversationRequest;

  let assistantMessage: ChatMessage = { id: "", role: ASSISTANT, content: "", date: new Date().toISOString() };
  let toolMessage: ChatMessage = {} as ChatMessage;
  let assistantContent = "";
  let latestCitations: any[] = [];

  try {
    // Create new or use existing conversation
    if (!conversation) {
      conversation = {
        id: Date.now().toString(),
        title: content.slice(0, 50) + (content.length > 50 ? "..." : ""),
        messages: [userMessage],
        date: new Date().toISOString()
        
      };
      // eslint-disable-next-line no-console
      console.log("date : ", conversation.date);
      request = { messages: [userMessage] };
    } else {
      // else-branch
      conversation.messages = [...conversation.messages, userMessage];

      request = { messages: conversation.messages.filter(msg => msg.role !== ERROR) };
    }

    appStateContext?.dispatch({ type: 'UPDATE_CURRENT_CHAT', payload: conversation });
    setActiveChat(conversation.id);

    const response = await historyGenerate(
      request,
      abortController.signal,
      !currentChat ? undefined : conversation.id
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(parseErrorMessage(`Backend returned ${response.status}: ${errorText}`));
    }

    if (response?.body) {
      const reader = response.body.getReader();
      let runningText = '';
      let finalResult: any = {};
      let assistantInserted = false;
      let seenAssistantToken = false;
      let framePending = false;
      let lastFlushTs = 0;
      let assistantMessageId: string | null = null;
      const flush = () => {
      // conversation is defined in this scope; copy to trigger React updates safely
      appStateContext?.dispatch({ type: 'UPDATE_CURRENT_CHAT', payload: { ...conversation! } });
    };
      const scheduleFlush = () => {
        if (framePending) return;
        framePending = true;
        requestAnimationFrame(() => {
          flush();
          framePending = false;
        });
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = new TextDecoder('utf-8').decode(value);
        const objects = text.split('\n');

        for (const obj of objects) {
          try {
            if (obj && obj !== '{}') {
              runningText += obj;
              const result = JSON.parse(runningText);
              finalResult = result;

              // Capture citations
              if (Array.isArray(result.citations)) latestCitations = result.citations;

              if (result.choices?.length > 0) {
                result.choices[0].messages.forEach((msg: any) => {
                    if (msg.role === TOOL) {
                      toolMessage = { ...msg, id: msg.id || uuid() };
                      // NEW: try to extract citations from tool JSON
                      try {
                        if (typeof msg.content === "string") {
                          const parsed = JSON.parse(msg.content);
                          if (Array.isArray(parsed?.citations)) {
                            latestCitations = parsed.citations;
                          }
                        }
                      } catch {}
                    }
                  
                  if (msg.role === ASSISTANT) {
                    if (!assistantMessageId) {
                      assistantMessageId = msg.id || uuid();
                    }
                    assistantContent += msg.content;
                    assistantMessage = {...assistantMessage, ...msg, id: assistantMessageId }; 
                    assistantMessage.content = assistantContent;

                    if (Array.isArray(latestCitations) && latestCitations.length > 0) {
                      (assistantMessage as any).citations = latestCitations;
                    }
                    // Update the conversation in real-time as we stream
                    const assistantIndex = conversation.messages.findIndex(m => m.id === assistantMessageId);
                    const nextMessages =
                    assistantIndex === -1
                      ? [...conversation.messages, { ...assistantMessage }]
                      : conversation.messages.map((m, i) => (i === assistantIndex ? { ...assistantMessage } : m));

                  conversation.messages = nextMessages;
                  scheduleFlush();
                  }
                
                });
              }
              runningText = '';
            }
          } catch (e) {
            if (!(e instanceof SyntaxError)) throw e;
          }
        }
      }
      // Title fallback logic
      if (!currentChat && finalResult.history_metadata) {
        conversation.id = finalResult.history_metadata.conversation_id;
        conversation.title =
          finalResult.history_metadata.title?.trim() ||
          content.slice(0, 50) + (content.length > 50 ? "..." : "");
        conversation.date = finalResult.history_metadata.date;
      }

      // Ensure the conversation has a fresh date so it sorts to the top
      try {
        // Prefer backend-provided date if present; otherwise use now
        conversation.date = (finalResult?.history_metadata?.date) || new Date().toISOString();
      } catch {}

      appStateContext?.dispatch({ type: 'UPDATE_CURRENT_CHAT', payload: conversation });
      appStateContext?.dispatch({ type: 'UPDATE_CHAT_HISTORY', payload: conversation });
      conversation.messages = conversation.messages.map(m => {
      if (m.role === ASSISTANT && Array.isArray((m as any).citations)) {
        // Already has citations, keep as is
        return m;
      }
      if (m.role === ASSISTANT && Array.isArray(latestCitations) && latestCitations.length > 0) {
        // Attach latest citations if missing
        return { ...m, citations: latestCitations };
      }
      return m;
    });
      try {
        // Save to backend so messages persist
        await historyUpdate(conversation.messages, conversation.id);
      } catch (e) {
        console.error("Failed to save conversation to backend:", e);
      }

    }
  } catch (err) {
    console.error("Error sending message:", err);

    const errorMessage: ChatMessage = {
      id: Date.now().toString(),
      role: ERROR,
      content: `Error: ${err instanceof Error ? err.message : 'Unknown error occurred'}`,
      date: new Date().toISOString()
    };

    if (conversation) {
      conversation.messages.push(errorMessage);
      appStateContext?.dispatch({ type: 'UPDATE_CURRENT_CHAT', payload: conversation });
    }

    toast({
      title: "Error",
      description: "Failed to send message to AI backend.",
      variant: "destructive"
    });
  } finally {
    setIsLoading(false);
  }
};



  // Handle chat selection on initial load
const selectedChat = getCurrentChat();
const { theme, setTheme } = useTheme();
const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="h-screen bg-background flex w-full overflow-visible">
      {/* Sidebar Toggle Button */}
      
      {/* Collapsed rail removed for now to avoid overlap issues */}

      {/* Sidebar Overlay + Panel (animated) */}
      <div
        className={`
          fixed inset-0 z-[70]
          ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}
          transition-opacity duration-300
        `}
        aria-hidden={!isOpen}
      >
        {/* Backdrop */}
        <div
          className="fixed inset-0 z-[50] bg-black/50"
          onClick={() => setIsOpen(false)}
          aria-hidden
        />

        {/* Sliding Panel */}
        <div
          className={`
            fixed inset-y-0 left-0 z-[80]
            w-80 bg-card shadow-xl border-r border-sidebar-border
            transform transition-transform duration-300 
            ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          `}
          style={{
              visibility: isOpen ? 'visible' : 'hidden',
              maxWidth: '100vw',
            }}
        >
          <Sidebar
            chats={mappedChats}
            activeChat={activeChat}
            onSelectChat={handleSelectChat}
            onNewChat={handleNewChat}
            onDeleteChat={handleDeleteChat}
            onRenameChat={handleRenameChat}
            isCollapsed={!isOpen}
            onToggleCollapse={toggleSidebar}
            isDarkMode={theme === "dark"}
            onToggleDarkMode={() => setTheme(theme === "dark" ? "light" : "dark")}
            onShareChat={handleShareChat}
          />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1">
        <div className="flex-1 flex justify-center">
          <ChatInterface
            messages={renderedMessages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
              chatTitle={
                currentChat?.title?.trim() ||
                settings?.ui?.chat_title?.trim() ||
                "New Chat"
              }
            onShareChat={() => activeChat && handleShareChat(activeChat)}
            onStopGeneration={() => setIsLoading(false)}
            showCentered={!currentChat}
            isCollapsed={!isOpen}
            toggleSidebar={toggleSidebar} // Pass toggleSidebar function
            isSidebarCollapsed={!isOpen}  // Pass sidebar state (true when collapsed)
            scrollSignal={scrollSignal} 
          />
        </div>
      </div>
      
      {/* Share Dialog */}    
      <ShareDialog
        isOpen={shareDialogOpen}
        onClose={() => setShareDialogOpen(false)}
        chatId={shareDialogChatId}
        chatTitle={
          mappedChats.find(c => c.id === shareDialogChatId)?.title || "Chat"
        }
      />
      {/* Collapsed launcher (top-left) + thin rail opener */}
      {!isOpen && (
      <>
        {/* Clickable thin rail along the left edge */}
        <button
        type="button"
        aria-label="Open sidebar"
        onClick={() => setIsOpen(true)}
        className="fixed inset-y-0 left-0 z-[55] w-16 cursor-ew-resize group bg-chat-background"
      >
          {/* Draw the divider on the inner edge so it separates content clearly */}
          <div className="h-full w-px ml-auto bg-sidebar-border group-hover:bg-foreground/40 transition-colors" />
        </button>

        {/* Floating quick actions at the top */}
        <div className="fixed top-4 z-[60] flex flex-col gap-2"
           style={{ left: "calc(4rem / 2 - 1.25rem)" }}>
          <Button
          variant="ghost"
          size="icon"
          title="New Chat"
          aria-label="New Chat"
          className="h-10 w-10 rounded-full bg-muted/30 dark:bg-zinc-800/50 hover:bg-muted/60 dark:hover:bg-zinc-700/70 backdrop-blur"
          onClick={() => { handleNewChat(); setIsOpen(true); }}
        >
            <Plus className="w-4 h-4" />
          </Button>
          <Button
          variant="ghost"
          size="icon"
          title="Search"
          aria-label="Search"
          className="h-10 w-10 rounded-full bg-muted/30 dark:bg-zinc-800/50 hover:bg-muted/60 dark:hover:bg-zinc-700/70 backdrop-blur"
          onClick={() => {
            setSearchText("");
            setIsSearchOpen(true);
          }}
        >
            <Search className="w-4 h-4" />
          </Button>
        </div>
      </>
    )}

      {/* Centered Search Modal for collapsed state */}
      {isSearchOpen && (
      <div className="fixed inset-0 z-[90] flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50" onClick={() => setIsSearchOpen(false)} />
        <div className="relative z-[95] w-[92vw] max-w-xl rounded-xl border border-sidebar-border bg-background shadow-2xl">
          <div className="p-4 border-b border-sidebar-border">
            <Input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search chats..."
              className="h-10"
            />
          </div>
          <ScrollArea className="max-h-[60vh] p-2">
            {filteredModalChats.length === 0 ? (
              <div className="p-6 text-center text-muted-foreground">No results</div>
            ) : (
              filteredModalChats.map(c => (
                <button
                  key={c.id}
                  className="w-full text-left p-3 rounded-lg hover:bg-muted/50 transition-colors"
                  onClick={() => { setIsSearchOpen(false); setIsOpen(true); handleSelectChat(c.id); }}
                >
                  <div className="flex items-center justify-between">
                    <div className="font-medium truncate mr-2">{c.title}</div>
                    <div className="text-xs text-muted-foreground whitespace-nowrap">{formatTime(c.timestamp)}</div>
                  </div>
                </button>
              ))
            )}
          </ScrollArea>
          <div className="p-3 text-center text-xs text-muted-foreground border-t border-sidebar-border">Press ESC to close</div>
        </div>
      </div>
    )}

    </div>
  );
};

const Index = () => {
  return (
    <SidebarProvider>
      <MainContent />
    </SidebarProvider>
  );
};

export default Index;
