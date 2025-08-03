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
import React, { useContext, useEffect, useState } from "react";
import { Menu } from "lucide-react";
import { v4 as uuid } from "uuid";
import { conversationApi,
  frontendSettings,
  historyDelete,
  historyDeleteAll,
  historyGenerate,
  historyList,
  historyRead,
  historyRename, 
  historyUpdate} from "../api/api";
import { ConversationRequest, ChatMessage } from "../api/models";
import AppSidebar from "../components/AppSidebar";
import ChatInterface from "../components/ChatInterface";
import ShareDialog from "../components/ShareDialog";
import { Button } from "../components/ui/button";
import { SidebarProvider, useSidebar } from "../components/ui/sidebar";
import { useToast } from "../hooks/use-toast";
import { AppStateContext } from "../state/AppProvider";

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
}

interface Chat {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messages: Message[];
}

// Roles from old Chat.tsx
const [ASSISTANT, TOOL, ERROR] = ['assistant', 'tool', 'error'];

let assistantMessage = {} as ChatMessage;
let toolMessage = {} as ChatMessage;
let assistantContent = '';
let latestCitations: any[] = [];

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

  const { toast } = useToast();
  const { open, setOpen } = useSidebar();
  
  // Get data from AppStateContext
  const chats = appStateContext?.state.chatHistory || [];
  const currentChat = appStateContext?.state.currentChat;
  const settings = appStateContext?.state.frontendSettings;

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
  const mappedChats: Chat[] = chats.map(conv => ({
    id: conv.id,
    title: conv.title,
    lastMessage: normalizeContent(
      conv.messages?.[conv.messages.length - 1]?.content ?? ""
    ),
    timestamp: conv.date ? new Date(conv.date) : new Date(),
    messages: (conv.messages || []).map(m => ({
      id: m.id,
      content: normalizeContent(m.content),
      role: m.role as "user" | "assistant",
      timestamp: m.date ? new Date(m.date) : new Date()
    }))
  }));

  const getCurrentChat = () => {
    return mappedChats.find(chat => chat.id === activeChat);
  };

  // Select a chat and load it in AppState
  const handleSelectChat = async (chatId: string) => {
    setActiveChat(chatId);
    const selectedChat = chats.find(c => c.id === chatId);
    if (selectedChat) {
      appStateContext?.dispatch({ type: 'UPDATE_CURRENT_CHAT', payload: selectedChat });
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

  assistantMessage = { id: '', role: ASSISTANT, content: '', date: new Date().toISOString() };
  toolMessage = {} as ChatMessage;
  assistantContent = '';
  latestCitations = [];

  try {
    // Create new or use existing conversation
    if (!conversation) {
      conversation = {
        id: Date.now().toString(),
        title: content.slice(0, 50) + (content.length > 50 ? "..." : ""),
        messages: [userMessage],
        date: new Date().toISOString()
      };
      request = { messages: [userMessage] };
    } else {
      conversation.messages.push(userMessage);
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
              if (result.citations) latestCitations = result.citations;

              if (result.choices?.length > 0) {
                result.choices[0].messages.forEach((msg: any) => {
                  if (msg.role === ASSISTANT) {
                    assistantContent += msg.content;
                    assistantMessage = {...assistantMessage, ...msg, id: msg.id || uuid()}; 
                    assistantMessage.content = assistantContent;

                    if (latestCitations.length > 0) {
                      (assistantMessage as any).citations = latestCitations;
                    }
                  }
                    if (msg.role === TOOL) {
                      toolMessage = { ...msg, id: msg.id || uuid() };
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

      console.log("[DEBUG] Backend history_metadata:", finalResult.history_metadata);

      // Title fallback logic
      if (!currentChat && finalResult.history_metadata) {
        conversation.id = finalResult.history_metadata.conversation_id;
        conversation.title =
          finalResult.history_metadata.title?.trim() ||
          content.slice(0, 50) + (content.length > 50 ? "..." : "");
        conversation.date = finalResult.history_metadata.date;
      }

      // Append tool message first if present
      if (Object.keys(toolMessage).length > 0) {
        conversation.messages.push(toolMessage);
      }

      if (assistantMessage.content) {
        conversation.messages.push(assistantMessage);
      }

      appStateContext?.dispatch({ type: 'UPDATE_CURRENT_CHAT', payload: conversation });
      appStateContext?.dispatch({ type: 'UPDATE_CHAT_HISTORY', payload: conversation });
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

  return (
    <div className="min-h-screen bg-background flex w-full relative">
      {!open && (
        <Button
          onClick={() => setOpen(true)}
          className="fixed top-4 left-4 z-50 h-10 w-10 p-0 rounded-full shadow-lg bg-primary hover:bg-primary/90"
        >
          <Menu className="h-5 w-5" />
        </Button>
      )}

      <div className="flex flex-1">
        <AppSidebar
          chats={mappedChats}
          activeChat={activeChat}
          onSelectChat={handleSelectChat}
          onNewChat={handleNewChat}
          onDeleteChat={handleDeleteChat}
          onRenameChat={handleRenameChat}
        />
        <div className="flex-1 flex">
          <ChatInterface
            messages={currentChat?.messages?.map(m => ({
              id: m.id,
              content: normalizeContent(m.content),
              role: m.role as "user" | "assistant",
              timestamp: m.date ? new Date(m.date) : new Date()
            })) || []}
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
          />
        </div>
      </div>

      <ShareDialog
        isOpen={shareDialogOpen}
        onClose={() => setShareDialogOpen(false)}
        chatId={shareDialogChatId}
        chatTitle={
          mappedChats.find(c => c.id === shareDialogChatId)?.title || "Chat"
        }
      />
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
