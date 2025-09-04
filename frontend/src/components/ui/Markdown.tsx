/* Markdown.tsx
 * ChatGPT-style Markdown rendering with clean typography, subtle quotes,
 * compact lists, tidy tables, and code blocks with a copy button.
 */

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ---------- Code block with copy button ----------
const CodeBlock: React.FC<{ language?: string; value: string }> = ({
  language,
  value,
}) => {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      // no-op
    }
  };

  return (
    <div className="relative group my-4">
      <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onCopy}
          className="text-xs px-2 py-1 rounded-md bg-zinc-800/80 text-zinc-100 border border-white/10 hover:bg-zinc-700/80"
          aria-label="Copy code"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      <pre className="w-full overflow-x-auto rounded-xl border border-zinc-700/50 bg-[#0f1117] text-zinc-100 p-4 text-sm leading-6">
        <code className="font-mono">{value}</code>
      </pre>
    </div>
  );
};

// ---------- Table primitives (light, compact) ----------
const tableComponents = {
  table: ({ node, ...props }: any) => (
    <div className="my-4 overflow-x-auto custom-scrollbar">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  thead: ({ node, ...props }: any) => (
    <thead className="bg-zinc-100 dark:bg-zinc-900" {...props} />
  ),
  tbody: ({ node, ...props }: any) => (
    <tbody
      className="divide-y divide-zinc-200 dark:divide-zinc-800"
      {...props}
    />
  ),
  tr: ({ node, ...props }: any) => <tr {...props} />,
  th: ({ node, ...props }: any) => (
    <th
      className="px-3 py-2 text-left font-medium text-foreground border-b border-zinc-300 dark:border-zinc-600"
      {...props}
    />
  ),
  td: ({ node, ...props }: any) => (
    <td
      className="px-3 py-2 align-top border-b border-zinc-300 dark:border-zinc-600"
      {...props}
    />
  ),
};

// ---------- Markdown element renderers (ChatGPT-like rhythm) ----------
const markdownComponents = {
  ...tableComponents,

  h1: ({ node, ...props }: any) => (
    <h1 className="mt-6 mb-3 text-2xl font-semibold text-foreground" {...props} />
  ),
  h2: ({ node, ...props }: any) => (
    <h2 className="mt-6 mb-3 text-xl font-semibold text-foreground" {...props} />
  ),
  h3: ({ node, ...props }: any) => (
    <h3 className="mt-5 mb-2 text-lg font-semibold text-foreground" {...props} />
  ),

  p: ({ node, ...props }: any) => (
    <p className="leading-7 text-foreground/95 mb-4" {...props} />
  ),

  strong: ({ node, ...props }: any) => (
    <strong className="font-semibold text-foreground" {...props} />
  ),

  a: ({ node, ...props }: any) => (
    <a
      className="underline underline-offset-2 hover:opacity-90 text-foreground"
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),

  ul: ({ node, ...props }: any) => (
    <ul className="list-disc pl-5 mb-4 space-y-1 text-foreground/95" {...props} />
  ),
  ol: ({ node, ...props }: any) => (
    <ol className="list-decimal pl-5 mb-4 space-y-1 text-foreground/95" {...props} />
  ),
  li: ({ node, ...props }: any) => <li className="leading-7" {...props} />,

  blockquote: ({ node, ...props }: any) => (
    <blockquote
      className="my-4 border-l-4 border-zinc-300 dark:border-zinc-700 pl-4 text-foreground/90 italic"
      {...props}
    />
  ),

  // Images stay within column and have gentle rounding
  img: ({ node, ...props }: any) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img className="max-w-full rounded-lg my-3" {...props} />
  ),

  hr: () => (
    <hr className="my-6 border-zinc-200 dark:border-zinc-800" />
  ),

  // Code handling: inline vs fenced
  code: ({
    inline,
    className,
    children,
    ...props
  }: {
    inline?: boolean;
    className?: string;
    children?: React.ReactNode;
  }) => {
    const match = /language-(\w+)/.exec(className || "");
    const value = String(children ?? "");

    if (!inline) {
      // Fenced code block
      return <CodeBlock language={match?.[1]} value={value} />;
    }

    // Inline code
    return (
      <code
        className="px-1.5 py-0.5 rounded-md bg-zinc-200/70 dark:bg-zinc-800 text-foreground text-[0.95em]"
        {...props}
      >
        {children}
      </code>
    );
  },
};

// ---------- Component ----------
export interface MarkdownProps {
  content: string;
  className?: string;
}

const Markdown: React.FC<MarkdownProps> = ({ content, className }) => {
  return (
    <div className={className}>
      <ReactMarkdown
        className="max-w-none text-left"
        remarkPlugins={[remarkGfm]}
        components={markdownComponents as any}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default Markdown;
