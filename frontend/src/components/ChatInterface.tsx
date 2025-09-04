/* eslint-disable object-curly-newline */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react/jsx-indent */
/* eslint-disable indent */
/* eslint-disable comma-dangle */
/* eslint-disable simple-import-sort/imports */
import React, { useDeferredValue, useEffect, useRef, useState } from "react";
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

//citations
import CitationStrip from "../components/citations/CitationStrip";
import CitationPane from "../components/citations/CitationPane";
import type { Citation } from "@/types/chats";
import { Menu } from "lucide-react";
const MemoMarkdown = React.memo(Markdown);

const ChatInterface: React.FC<ChatInterfaceProps & { 
  toggleSidebar: () => void; 
  isSidebarCollapsed: boolean; 
  scrollSignal?: number;
}> = ({
  messages,
  onSendMessage,
  isLoading,
  chatTitle = "New Chat",
  onShareChat,
  onStopGeneration,
  showCentered = false,
  isCollapsed = false,
  toggleSidebar, // Add toggleSidebar prop
  isSidebarCollapsed, // Add isSidebarCollapsed prop
  scrollSignal  
}) => {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showJump, setShowJump] = useState(false);
  const [forceTyping, setForceTyping] = useState(false);
  // Measure input area's height to avoid scroll button overlap
  const inputWrapRef = useRef<HTMLDivElement>(null);
  const [inputOffset, setInputOffset] = useState(144); // px; fallback ~ bottom-36
  const measureInput = () => {
    const el = inputWrapRef.current;
    if (!el) return;
    const h = el.getBoundingClientRect().height || 0;
    // Keep a small gap so the button doesn't touch the input
    setInputOffset(Math.max(96, Math.ceil(h) + 16));
  };
 // Show indicator if: (normal rule) OR (debug forced)
  const deferredMessages = useDeferredValue(messages);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto"; // reset to measure
    const maxPx = parseFloat(getComputedStyle(el).maxHeight || "0");
    const next = Math.min(el.scrollHeight, Number.isFinite(maxPx) ? maxPx : el.scrollHeight);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > next ? "auto" : "hidden";
};
// --- Title display: prefer a real chat title and avoid flicker during streaming
const hasAssistantMsg = messages?.some(m => m.role === "assistant");
const hasRealTitle = Boolean(chatTitle?.trim()) && chatTitle !== "New Chat";
const displayTitle = hasRealTitle ? chatTitle : "Maintenance Agent";

// Run once on mount and whenever input text changes
useEffect(() => { autoResize(); }, []);
useEffect(() => { autoResize(); }, [input]);

// (Optional) keep height correct on viewport resize (vh-based caps)
useEffect(() => {
  const onResize = () => autoResize();
  window.addEventListener("resize", onResize);
  return () => window.removeEventListener("resize", onResize);
}, []);

// Initial measurement and recompute when input grows/shrinks or loading state changes
useEffect(() => { measureInput(); }, []);
useEffect(() => { requestAnimationFrame(measureInput); }, [input, isLoading]);
useEffect(() => {
  const onResize = () => measureInput();
  window.addEventListener("resize", onResize);
  return () => window.removeEventListener("resize", onResize);
}, []);

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
  // only act on deliberate signals (> 0) and when there is content
  if (!scrollSignal || messages.length === 0) return;

  // wait for layout to settle
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      scrollToBottom("auto");
    });
  });
}, [scrollSignal]);
  useEffect(() => {
    if (isLoading) {
      // streaming started: ensure the button is hidden
      setShowJump(false);
    } else {
      // streaming finished: recompute whether we should show it
      const viewport = getViewport();
      if (viewport) {
        const atBottom = isNearBottom(viewport, 80);
        setShowJump(!atBottom);
      }
  }
}, [isLoading]);
  useEffect(() => {
    if (messages.some(m => m.role === "assistant")) setIsTyping(false);
  }, [messages]);

  useEffect(() => {
  const viewport = getViewport();
  if (!viewport) return;

  let ticking = false;
  const onScroll = () => {
    if (isLoading || ticking) return;   // skip updates while streaming
    ticking = true;
    requestAnimationFrame(() => {
      const atBottom = isNearBottom(viewport, 80);
      setShowJump(prev => {
        const next = !atBottom;
        return prev === next ? prev : next; // update only if changed
      });
      ticking = false;
    });
  };

  // Initialize only if not streaming
  if (!isLoading) onScroll();

  viewport.addEventListener("scroll", onScroll);
  return () => viewport.removeEventListener("scroll", onScroll);
}, [isLoading, messages]);

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
  const TypingIndicator = () => <div className="flex items-center space-x-2 text-foreground dark:dark:text-foreground px-4 py-4">
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

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const [refPaneOpen, setRefPaneOpen] = useState(false);
  const [paneCitations, setPaneCitations] = useState<Citation[]>([]);
  const openRefs = (cits: Citation[]) => {
    if (!cits?.length) return;
    setPaneCitations(cits);
    setRefPaneOpen(true);
  };
  const lastIsAssistant = messages[messages.length - 1]?.role === "assistant";
  const showTypingIndicator = (isLoading && !lastIsAssistant) || forceTyping;
  
  return <div
    className="flex-1 flex flex-col h-screen bg-chat-background transition-[padding-right] duration-200"
  
>

  {/* Uncomment to debug the typing indicator */}
  {/* {import.meta.env.DEV && (
  <div className="fixed bottom-24 right-4 z-50 rounded-xl bg-black/60 text-white px-3 py-2 text-xs">
    <label className="inline-flex items-center space-x-2">
      <input
        type="checkbox"
        checked={forceTyping}
        onChange={e => setForceTyping(e.target.checked)}
      />
      <span>TypingIndicator (debug)</span>
    </label>
  </div>
)} */}
    {/* Header (sticky, consistent height, behind rail) */}
  <div className="sticky top-0 h-16 flex items-center border-b border-chat-border px-4 bg-card/50 backdrop-blur-xl z-[20] ">
    <div className="flex items-center w-full px-2 sm:px-4 relative">
        {/* Mobile: show a hamburger to open the sidebar */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="sm:hidden mr-2 h-9 w-9"
          aria-label="Open sidebar"
          title="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </Button>

<h1
  className="absolute left-1/2 -translate-x-1/2 transform
             font-semibold text-[#343541] dark:text-white
             text-center leading-tight
             max-w-[65%] sm:max-w-[70%]
             whitespace-normal"
  style={{ fontSize: "clamp(1.25rem, 4vw, 1.35rem)" }}
>
  {displayTitle}
</h1>

        
        {/* Share Button on Right */}
        <div className="ml-auto flex items-center">
          {messages.length > 0 && onShareChat && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleShare}
              className="h-8 px-3 text-sm text-[#343541] dark:text-white hover:bg-[#343541]/10 dark:hover:bg-primary/20 transition-colors duration-200"
            >
              <Share2 className="w-3 h-3" />
              Share
            </Button>
          )}
        </div>
      </div>
    </div>

      {/* Messages */}
            <ScrollArea className={cn("flex-1", isCentered ? "flex items-center justify-center" : " pt-4")}>
                <div className={cn(
                  "w-full max-w-[95vw] sm:max-w-xl md:max-w-2xl lg:max-w-3xl mx-auto px-2 sm:px-4",              // NEW: centered column + even gutters
                  isCentered ? "" : "space-y-6"   ,
                  "pb-28 sm:pb-32"            
                )}>

          {messages.length === 0 && isCentered ? <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 py-0 my-[0px]">
              <div className="text-center space-y-4">
                <h1 className="text-4xl font-semibold text-[#343541] dark:text-white">
                  What's on your mind today?
                </h1>
              </div>
              <div className="w-full max-w-2xl">
                <form onSubmit={handleSubmit} className="relative">
                  <div className="relative group">
                  <Textarea
                    ref={textareaRef}
                    value={input}
                    onChange={e => { setInput(e.target.value); requestAnimationFrame(autoResize); }}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything."
                    className={cn(
                      "min-h-[56px] sm:min-h-[64px] max-h-[50vh] sm:max-h-[45vh] md:max-h-[40vh] lg:max-h-[35vh]",
                      "overflow-y-auto pr-14 resize-none transition-all duration-200",
                      // keep the styles you already have in this block:
                      "bg-white border-[#343541] placeholder-slate-400",
                      "dark:bg-zinc-900 dark:border-zinc-200",
                      "focus:ring-ring focus:ring-2 hover:shadow-lg hover:border-border"
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
      </div> : deferredMessages.map(message => <div key={message.id} className={cn("group  mt-1 mb-6 transition-all duration-200", message.role === 'user' ? "flex justify-end" : "flex justify-start")}>
                <div className={cn("transition-all duration-200", message.role === 'user' ? "max-w-[75%]" : "w-full")}>
                   {/* Message Content */}
                   <div className={cn("px-4 py-3 rounded-2xl transition-all duration-200 w-full", 
                   
                    message.role === "user"
                    ? "bg-[#444654] dark:bg-[#343541] text-white"
                    : "bg-gray-200/0 dark:bg-chat-message-assistant/0 text-foreground border border-chat-border/0")}>

                      {message.role === "assistant" ? (
                        <MemoMarkdown content={message.content} />                      ) : (
                        <p className="whitespace-pre-wrap leading-relaxed text-[15px] text-left m-0">
                          {message.content}
                        </p>
                      )}
                   </div>

                    {/* References count / chips */}
                    {message.role === "assistant" &&
                      Array.isArray(message.citations) &&
                      message.citations.length > 0 && (
                        <div className="mt-2">
                          <CitationStrip citations={message.citations} onOpen={openRefs} />
                        </div>
                    )}

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

          {showTypingIndicator && (
          <div className="group mb-6 flex justify-start">
            <div className="max-w-[80%] transition-all duration-200">
              <div className="bg-gray-200/80 dark:bg-chat-message-assistant text-[#444654]  border border-chat-border/30 p-2 rounded-2xl">
                <TypingIndicator />
              </div>
              {onStopGeneration && (
                <div className="flex items-center mt-2 px-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onStopGeneration}
                    className="h-7 px-3 text-xs hover:bg-muted/50 text-red-600 hover:text-red-700"
                  >
                    <Square className="w-3 h-3 mr-1" />
                    Stop
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      {!isLoading && showJump && (
      <div
        className={
          // Centered overlay, above the input. Bottom is computed from input height.
          "pointer-events-none fixed inset-x-0 z-[10] flex justify-center"
        }
        style={{ bottom: `calc(${inputOffset}px + env(safe-area-inset-bottom))` }}
      >
        <Button
          onClick={() => requestAnimationFrame(() => scrollToBottom("auto"))}
          className="pointer-events-auto h-8 px-2 rounded-full shadow-lg bg-[#343541] dark:bg-foreground text-primary-foreground hover:bg-primary/90 transition-opacity"
        >
          <ChevronDown className="w-4 h-4" />
        
          <span className="sr-only">Scroll to latest</span>
        </Button>
      </div>
    )}
      {/* Input Area - Only show when not centered or when there are messages */}
      {!isCentered && <div ref={inputWrapRef} className="border-t border-chat-border bg-card/50 backdrop-blur-xl px-4 py-4 ">
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleSubmit} className="relative">
              <div className="relative group">
                <Textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => { setInput(e.target.value); requestAnimationFrame(autoResize); }}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything."
                  className={cn(
    // Auto-grow baseline + responsive max height (taller cap on smaller screens)
    " min-h-[56px] sm:min-h-[64px] max-h-[50vh] sm:max-h-[45vh] md:max-h-[40vh] lg:max-h-[35vh]",
    "overflow-y-auto pr-14 resize-none transition-all duration-200",
    // keep your existing theming & focus rings
    "!bg-chat-input dark:bg-red-900 border-chat-border focus:ring-ring focus:ring-2",
    "rounded-2xl text-base leading-relaxed",
    "placeholder:text-muted-foreground/60"
  )}
                  disabled={isLoading}
/>
                <Button type="submit" size="icon" disabled={!input.trim() || isLoading} className={cn("absolute right-3 bottom-3 h-10 w-10 rounded-xl", "bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-all duration-200", "hover:scale-105 active:scale-95", "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100")}>
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </form>
            <p className="text-xs text-muted-foreground/80 mt-3 text-center">
              AI can make mistakes. Consider checking important information.
            </p>
          </div>
        </div>}

      <CitationPane
        open={refPaneOpen}
        citations={paneCitations}
        onClose={() => setRefPaneOpen(false)}
      />

    </div>;
};
export default ChatInterface;
