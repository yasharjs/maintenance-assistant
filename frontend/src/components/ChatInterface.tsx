/* eslint-disable object-curly-newline */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/jsx-indent */
/* eslint-disable indent */
/* eslint-disable comma-dangle */
/* eslint-disable simple-import-sort/imports */
import React, { useEffect, useRef, useState } from "react";
import { Check,
  Copy,
  MessageSquare,
  RotateCcw,
  Send,
  Share2,
  Sparkles,
  Square,
  ThumbsDown,
  ThumbsUp,
  ChevronDown } from "lucide-react";
import logoImage from '@/assets/logo.png';

import { historyMessageFeedback } from "../api/api";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { Textarea } from "../components/ui/textarea";
import { useToast } from "../hooks/use-toast";
import { cn } from "../lib/utils";
import Markdown from "./ui/Markdown";
import type { ChatInterfaceProps } from "@/types/chats";

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  onSendMessage,
  isLoading,
  chatTitle = "New Chat",
  onShareChat,
  onStopGeneration,
  showCentered = false
}) => {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showJump, setShowJump] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    toast
  } = useToast();
// Get the Radix ScrollArea viewport (so we can control scroll precisely)
  const getViewport = () =>
    messagesEndRef.current?.closest("[data-radix-scroll-area-viewport]") as HTMLElement | null;

  const isNearBottom = (viewport: HTMLElement, threshold = 80) => {
    const { scrollTop, clientHeight, scrollHeight } = viewport;
    return scrollHeight - (scrollTop + clientHeight) < threshold;
  };

  // Only smooth-scroll when NOT streaming; instant scroll during streaming,
  // and never steal scroll if user has scrolled up.
  const scrollToBottom = (behavior: ScrollBehavior) => {
    const viewport = getViewport();
    if (!viewport) {
      messagesEndRef.current?.scrollIntoView({ behavior });
      return;
    }
    if (!isNearBottom(viewport) && isLoading) return; // respect user scroll while streaming
    viewport.scrollTo({ top: viewport.scrollHeight, behavior });
  };

  useEffect(() => {
    scrollToBottom(isLoading ? "auto" : "smooth");
  }, [messages, isLoading]);
  useEffect(() => {
    if (messages.some(m => m.role === "assistant")) setIsTyping(false);
  }, [messages]);

  useEffect(() => {
  const viewport = getViewport();
  if (!viewport) return;

  const onScroll = () => {
    const atBottom = isNearBottom(viewport, 80);
    setShowJump(!atBottom);
  };

  onScroll(); // initialize state on mount/update
  viewport.addEventListener("scroll", onScroll);
  return () => viewport.removeEventListener("scroll", onScroll);
}, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
      setIsTyping(true);
      // NEW: force an instant jump to bottom as soon as user sends
      requestAnimationFrame(() => scrollToBottom("auto"));
      // If your first message doesn't jump reliably, use a double RAF:
      // requestAnimationFrame(() => requestAnimationFrame(() => scrollToBottom("auto")));
      setTimeout(() => setIsTyping(false), 1000);
    }
  };
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };
  const copyToClipboard = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(messageId);
      toast({
        title: "Copied to clipboard",
        description: "Message copied successfully."
      });
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      toast({
        title: "Failed to copy",
        description: "Please try again.",
        variant: "destructive"
      });
    }
  };
  
const handleFeedback = async (messageId: string, type: 'up' | 'down') => {
  // Show a toast immediately for UX responsiveness
  toast({
    title: `Feedback ${type === 'up' ? 'positive' : 'negative'}`,
    description: "Submitting your feedback..."
  });

  try {
    const response = await historyMessageFeedback(messageId, type);

    if (response.ok) {
      toast({
        title: "Feedback recorded",
        description: "Thank you for helping us improve!"
      });
    } else {
      toast({
        title: "Feedback failed",
        description: "Please try again later.",
        variant: "destructive"
      });
    }
  } catch (err) {
    toast({
      title: "Error submitting feedback",
      description: "Please try again later.",
      variant: "destructive"
    });
  }
};
  const handleShare = () => {
    const shareUrl = `${window.location.origin}${window.location.pathname}`;
    navigator.clipboard.writeText(shareUrl);
    toast({
      title: "Share link copied",
      description: "Share this conversation with others."
    });
    onShareChat?.();
  };
  const TypingIndicator = () => <div className="flex items-center space-x-2 text-muted-foreground px-6 py-4">
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{
        animationDelay: '0ms'
      }} />
        <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{
        animationDelay: '150ms'
      }} />
        <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{
        animationDelay: '300ms'
      }} />
      </div>
      <span className="text-sm">Thinking...</span>
    </div>;
  const isCentered = showCentered && messages.length === 0;
  
  return <div className="flex-1 flex flex-col h-screen bg-chat-background">

      {/* Header */}
      <div className="border-b border-chat-border p-4 bg-card/50 backdrop-blur-xl sticky top-0 z-10">
        <div className="mx-auto w-full  flex items-center justify-between gap-2 px-2 sm:px-4">
          <div className="flex min-w-0 items-center gap-3 flex-1">
            <img src={logoImage} alt="Logo" className="w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16 shrink-0" />
            <h1 className="text-xl font-semibold text-foreground">{chatTitle}</h1>
          </div>
          <div className="flex items-center space-x-4 ml-auto">
          
            {messages.length > 0 && onShareChat && <Button variant="outline" size="sm" onClick={handleShare} className="h-8 px-3 text-xs">
                <Share2 className="w-3 h-3 mr-1" />
                Share
              </Button>}
          </div>
        </div>
      </div>

      {/* Messages */}
            <ScrollArea className={cn("flex-1", isCentered ? "flex items-center justify-center" : " pt-4")}>
              <div className={cn("w-full", isCentered ? "mx-auto" : "space-y-8 ml-0")}>

          {messages.length === 0 && isCentered ? <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 py-0 my-[0px]">
              <div className="text-center space-y-4">
                <h1 className="text-4xl font-semibold text-foreground">
                  What's on your mind today?
                </h1>
              </div>
              <div className="w-full max-w-2xl">
                <form onSubmit={handleSubmit} className="relative">
                  <div className="relative group">
                  <Textarea
                    ref={textareaRef}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything..."
                    className={cn(
                      "min-h-[60px] max-h-[200px] pr-14 resize-none transition-all duration-200",
                      // light defaults
                      "bg-white border-slate-300 placeholder-slate-400",
                      // dark overrides
                      "dark:bg-zinc-900 dark:border-zinc-200",
                      // focus/hover etc.
                      "focus:ring-ring focus:ring-2 hover:shadow-lg hover:border-border",
                      "rounded-2xl text-base leading-relaxed shadow-lg"
                    )}
                    disabled={isLoading}
                  />                 
                    <Button type="submit" size="icon" disabled={!input.trim() || isLoading} className={cn("absolute right-3 bottom-3 h-10 w-10 rounded-xl", "bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-all duration-200", "hover:scale-105 active:scale-95", "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100")}>
                      <Send className="w-4 h-4" />
                    </Button>
                  </div>
                </form>
              </div>
            </div> : messages.length === 0 ? <div className="text-center py-20 space-y-6">
              <div className="w-20 h-20 mx-auto bg-gradient-to-br from-muted/50 to-muted/20 rounded-full flex items-center justify-center">
                <MessageSquare className="w-10 h-10 text-muted-foreground" />
              </div>
              <div className="space-y-2">
                <h2 className="text-3xl font-bold text-foreground">
                  Ready when you are.
                </h2>
                <p className="text-muted-foreground text-lg">
                  Start a conversation and I'll help you with anything you need.
                </p>
              </div>
            </div> : messages.map(message => <div key={message.id} className={cn("group mb-6 transition-all duration-200", message.role === 'user' ? "flex justify-end" : "flex justify-start")}>
                <div className={cn("transition-all duration-200", message.role === 'user' ? "mr-8 ml-8 w-1/2 ml-8" : "w-full mr-8")}>
                   {/* Message Content */}
                   <div className={cn("p-3 rounded-2xl transition-all duration-200 block w-full", 
                   
                    message.role === "user"
                    ? "text-gray-900 bg-[#444654] text-white hover:shadow-md"
                    : "bg-chat-message-assistant text-foreground border border-chat-border/30 hover:shadow-black/10 hover:dark:shadow-white/15")}>
                      {message.role === "assistant" ? (
                        <Markdown content={message.content} />
                      ) : (
                        <p className="whitespace-pre-wrap leading-relaxed text-base text-left m-0">
                          {message.content}
                        </p>
                      )}
                   </div>
                  {/* Message Actions */}
                  <div className={cn("flex items-center mt-1 px-0 opacity-0 group-hover:opacity-100 transition-all duration-200", message.role === 'user' ? "justify-end" : "justify-start")}>
                    <div className="flex items-center space-x-1">
                      <Button variant="ghost" size="sm" onClick={() => copyToClipboard(message.content, message.id)} className="h-7 px-2 text-xs hover:bg-muted/50">
                        {copiedId === message.id ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
                      </Button>
                      
                      {message.role === 'assistant' && <>
                          <Button variant="ghost" size="sm" onClick={() => handleFeedback(message.id, 'up')} className="h-7 px-2 text-xs hover:bg-muted/50 hover:text-green-600">
                            <ThumbsUp className="w-3 h-3" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleFeedback(message.id, 'down')} className="h-7 px-2 text-xs hover:bg-muted/50 hover:text-red-600">
                            <ThumbsDown className="w-3 h-3" />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs hover:bg-muted/50">
                            <RotateCcw className="w-3 h-3" />
                          </Button>
                        </>}
                    </div>
                    
                    <span className="text-xs text-muted-foreground ml-2">
                      {message.timestamp.toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
                    </span>
                  </div>
                </div>
              </div>)}

          {(isLoading && (messages[messages.length - 1]?.role !== "assistant")) && <div className="group mb-6 flex justify-start">
              <div className="max-w-[80%] mr-8 hover:shadow-lg transition-all duration-200">
                <div className="bg-chat-message-assistant text-foreground border border-chat-border/30 p-4 rounded-2xl">
                  <TypingIndicator />
                </div>
                {isLoading && onStopGeneration && <div className="flex items-center mt-2 px-2">
                    <Button variant="ghost" size="sm" onClick={onStopGeneration} className="h-7 px-3 text-xs hover:bg-muted/50 text-red-600 hover:text-red-700">
                      <Square className="w-3 h-3 mr-1" />
                      Stop
                    </Button>
                  </div>}
              </div>
            </div>}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      {showJump && (
  <div
    className={
      // Centered overlay, above the input
      // If your input area is taller/shorter, tweak the bottom offset.
      "pointer-events-none fixed inset-x-0  bottom-36  z-40 flex justify-center"
    }
  >
    <Button
      onClick={() => requestAnimationFrame(() => scrollToBottom("auto"))}
      className="pointer-events-auto h-8 px-2 rounded-full shadow-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-opacity"
    >
      <ChevronDown className="w-4 h-4" />
     
      <span className="sr-only">Scroll to latest</span>
    </Button>
  </div>
)}
      {/* Input Area - Only show when not centered or when there are messages */}
      {!isCentered && <div className="border-t border-chat-border bg-card/50 backdrop-blur-xl px-20 py-4">
          <div className="max-w-4xl mx-auto">
            <form onSubmit={handleSubmit} className="relative">
              <div className="relative group">
                <Textarea ref={textareaRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="Ask anything..." className={cn("min-h-[60px] max-h-[200px] pr-14 resize-none transition-all duration-200", "!bg-chat-input dark:bg-zinc-900 border-chat-border focus:ring-ring focus:ring-2", "hover:shadow-lg hover:border-border", "rounded-2xl text-base leading-relaxed", "placeholder:text-muted-foreground/60")} disabled={isLoading} />
                <Button type="submit" size="icon" disabled={!input.trim() || isLoading} className={cn("absolute right-3 bottom-3 h-10 w-10 rounded-xl", "bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-all duration-200", "hover:scale-105 active:scale-95", "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100")}>
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </form>
            <p className="text-xs text-muted-foreground/80 mt-3 text-center">
              AI can make mistakes. Consider checking important information.
            </p>
          </div>
        </div>}
    </div>;
};
export default ChatInterface;

