/* eslint-disable indent */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable comma-dangle */
/* eslint-disable simple-import-sort/imports */
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import supersub from "remark-supersub";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { nord } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MarkdownRendererProps {
  content: string;
}


const tableComponents = {
  table: ({ node, ...props }: any) => (
    <table
      className="w-full border-collapse rounded-xl overflow-hidden shadow-md bg-white/70 dark:bg-neutral-900/70 backdrop-blur-sm text-sm my-6"
      {...props}
    />
  ),
  thead: ({ node, ...props }: any) => (
    <thead
      className="bg-gray-100 dark:bg-neutral-800 text-gray-800 dark:text-gray-200 font-semibold uppercase tracking-wide"
      {...props}
    />
  ),
  tbody: ({ node, ...props }: any) => (
    <tbody
      className="divide-y divide-gray-200 dark:divide-neutral-700"
      {...props}
    />
  ),
  tr: ({ node, ...props }: any) => (
    <tr
      className="hover:bg-gray-50 dark:hover:bg-neutral-800 transition-colors duration-200"
      {...props}
    />
  ),
  th: ({ node, ...props }: any) => (
    <th
      className="px-5 py-3 border border-gray-200 dark:border-neutral-700 text-left"
      {...props}
    />
  ),
  td: ({ node, ...props }: any) => (
    <td
      className="px-5 py-3 border border-gray-200 dark:border-neutral-700"
      {...props}
    />
  ),
};



  const markdownComponents = {
  ...tableComponents,
  p: ({ node, ...props }: any) => (
    <p
      className="leading-relaxed text-gray-800 dark:text-gray-200 mb-4"
      {...props}
    />
  ),
  strong: ({ node, ...props }: any) => (
    <strong
      className="font-semibold text-gray-900 dark:text-gray-100"
      {...props}
    />
  ),
  ul: ({ node, ...props }: any) => (
    <ul
      className="list-disc pl-6 mb-4 space-y-1 text-gray-800 dark:text-gray-200"
      {...props}
    />
  ),
  ol: ({ node, ...props }: any) => (
    <ol
      className="list-decimal pl-6 mb-4 space-y-1 text-gray-800 dark:text-gray-200"
      {...props}
    />
  ),
  li: ({ node, ...props }: any) => (
    <li
      className="leading-relaxed"
      {...props}
    />
  ),

};

const Markdown: React.FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <ReactMarkdown
      className="prose prose-sm max-w-none dark:prose-invert text-left"
      remarkPlugins={[remarkGfm, supersub]}
      components={markdownComponents}
    >
      {content}
    </ReactMarkdown>
  );
};

export default Markdown;
