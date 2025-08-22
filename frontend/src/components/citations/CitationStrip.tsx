
import type { Citation } from "@/types/chats";
import React from "react";
import styles from "./Citations.module.css";

type Props = {
  citations: Citation[];
  onOpen: (all: Citation[]) => void;  // <-- accepts array (matches ChatInterface)
  paneId?: string;
};

export default function CitationStrip({ citations, onOpen, paneId = "citation-pane" }: Props) {
  if (!Array.isArray(citations) || citations.length === 0) return null;

  const count = citations.length;
  const label = count === 1 ? "1 reference" : `${count} references`;

  return (
    <div className={styles.strip}>
      <button
        type="button"
        className={styles.stripPill ?? styles.countBtn}  // falls back if you kept .countBtn
        onClick={() => onOpen(citations)}                 // <-- pass array through
        aria-controls={paneId}
        aria-expanded="false"
        aria-label={`Open ${label}`}
        title={label}
      >
        {/* tiny inline icon; safe to remove if you wish */}
        <svg className={styles.pillIcon} viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
        <span style={{ fontSize: "12px" }}>References</span>
        <span className={styles.pillCount}>{count}</span>
      </button>
    </div>
  );
}