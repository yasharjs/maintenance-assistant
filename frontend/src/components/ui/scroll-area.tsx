import * as React from "react";
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";

import { cn } from "../../lib/utils";

const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>
>(({ className, children, ...props }, ref) => (
  <ScrollAreaPrimitive.Root
    ref={ref}
    // group class enables hover fade-in for scrollbars
    className={cn("relative overflow-hidden group/sa", className)}
    {...props}
  >
    <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">
      {children}
    </ScrollAreaPrimitive.Viewport>
    <ScrollBar />
    <ScrollAreaPrimitive.Corner />
  </ScrollAreaPrimitive.Root>
));
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName;

const ScrollBar = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>
>(({ className, orientation = "vertical", ...props }, ref) => (
  <ScrollAreaPrimitive.ScrollAreaScrollbar
    ref={ref}
    orientation={orientation}
    className={cn(
      // Soft track that fades in on hover (VS Code/ChatGPT feel)
      "flex touch-none select-none rounded-full transition-opacity duration-150 opacity-0 group-hover/sa:opacity-100 hover:opacity-100",
      orientation === "vertical" &&
        "h-full w-2 p-[2px] bg-[hsl(var(--scrollbar-track)/0.35)]",
      orientation === "horizontal" &&
        "h-2 flex-col p-[2px] bg-[hsl(var(--scrollbar-track)/0.35)]",
      className
    )}
    {...props}
  >
    <ScrollAreaPrimitive.ScrollAreaThumb
      className="relative flex-1 rounded-full bg-[hsl(var(--scrollbar-thumb)/0.7)] hover:bg-[hsl(var(--scrollbar-thumb)/0.9)] shadow-[inset_0_0_0_1px_rgba(0,0,0,0.06)]"
    />
  </ScrollAreaPrimitive.ScrollAreaScrollbar>
));
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName;

export { ScrollArea, ScrollBar };
