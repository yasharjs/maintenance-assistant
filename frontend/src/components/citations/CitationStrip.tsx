
import type { Citation } from "@/types/chats";

import styles from "./Citations.module.css";

type Props = {
  citations: Citation[];
  onOpen: (all: Citation[]) => void;
};

export default function CitationStrip({ citations, onOpen }: Props) {
  if (!Array.isArray(citations) || citations.length === 0) return null;

  const label = `${citations.length} reference${citations.length > 1 ? "s" : ""}`;
  return (
    <div className={styles.strip}>
      <button className={styles.countBtn} onClick={() => onOpen(citations)} aria-label="Open references">
        {label}
      </button>
    </div>
  );
}
