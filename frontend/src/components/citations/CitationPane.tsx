/* eslint-disable indent */
/* eslint-disable react/jsx-indent */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable jsx-a11y/no-static-element-interactions */
/* eslint-disable simple-import-sort/imports */
/* eslint-disable jsx-a11y/no-noninteractive-element-interactions */
import react, { useState, useEffect, useRef } from "react";
import styles from "./Citations.module.css";
import type { Citation } from "@/types/chats";

type Props = {
  open: boolean;
  citations: Citation[];
  onClose: () => void;
};

export default function CitationPane({ open, citations, onClose }: Props) {
  const [zoomUrl, setZoomUrl] = useState<string | null>(null);
  const paneRef = useRef<HTMLDivElement | null>(null);
  
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (zoomUrl) setZoomUrl(null);
        else if (open) onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, zoomUrl, onClose]);

  useEffect(() => {
    if (!open) return;
    const handleDown = (e: MouseEvent) => {
      if (zoomUrl) return; // don’t close pane while zoom is open
      const pane = paneRef.current;
      if (pane && !pane.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handleDown);
    return () => document.removeEventListener("mousedown", handleDown);
  }, [open, zoomUrl, onClose]);

   useEffect(() => {
    if (zoomUrl) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    // cleanup just in case component unmounts while zoom is active
    return () => {
      document.body.style.overflow = "";
    };
  }, [zoomUrl]);

  return (
    <>
      {/* Dimmed overlay over ChatInterface; click outside to close */}
      <div
        className={`${styles.overlay} ${open ? styles.overlayOpen : ""}`}
      />
      <aside 
        id="citation-pane" ref= {paneRef} className={`${styles.pane} ${open ? styles.paneOpen : ""}`} aria-hidden={!open}>
        <div className={styles.paneHeader}>
          <div>References</div>
          <button onClick={onClose}>Close</button>
        </div>

        <div className={styles.paneBody}>
          {citations.map((c, i) => (
            <div key={c.id ?? `${i}-${c.url}`} className={styles.item}>
              <div className={styles.title}>
                {c.title || c.filepath || `Reference ${i + 1}`}
                {c.locator ? ` • ${c.locator}` : ""}
              </div>

              {c.url && (
                <>
                  <a className={styles.link} href={c.url} target="_blank" rel="noreferrer">
                    Open source
                  </a>
                    {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
                    <img
                      className={styles.thumb}
                      src={c.url}
                      alt={c.title || "reference"}
                      onClick={() => setZoomUrl(c.url!)}
                    />
                </>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Zoom overlay */}
      <div className={`${styles.zoom} ${zoomUrl ? styles.zoomOpen : ""}`} onClick={() => setZoomUrl(null)}>
        {zoomUrl && (
          <>
            <button className={styles.zoomClose} onClick={() => setZoomUrl(null)}>
              Close
            </button>
            <img className={styles.zoomImg} src={zoomUrl} alt="zoomed reference" />
          </>
        )}
      </div>
    </>
  );
}
