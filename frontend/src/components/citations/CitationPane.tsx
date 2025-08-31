/* eslint-disable indent */
/* eslint-disable react/jsx-indent */
/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable jsx-a11y/no-static-element-interactions */
/* eslint-disable simple-import-sort/imports */
/* eslint-disable jsx-a11y/no-noninteractive-element-interactions */
import react, { useState, useEffect, useMemo, useRef } from "react";
import styles from "./Citations.module.css";
import type { Citation } from "@/types/chats";

type Props = {
  open: boolean;
  citations: Citation[];
  onClose: () => void;
};

export default function CitationPane({ open, citations, onClose }: Props) {
  const imageUrls = useMemo(() => (citations || []).map(c => c.url).filter(Boolean) as string[], [citations]);
  const [zoomIndex, setZoomIndex] = useState<number | null>(null);
  const paneRef = useRef<HTMLDivElement | null>(null);
  
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (zoomIndex !== null) setZoomIndex(null);
        else if (open) onClose();
      } else if (zoomIndex !== null && (e.key === "ArrowRight" || e.key === "ArrowLeft")) {
        e.preventDefault();
        const delta = e.key === "ArrowRight" ? 1 : -1;
        const total = imageUrls.length;
        const next = (zoomIndex + delta + total) % total;
        setZoomIndex(next);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, zoomIndex, imageUrls, onClose]);

  useEffect(() => {
    if (!open) return;
    const handleDown = (e: MouseEvent) => {
      if (zoomIndex !== null) return; // don’t close pane while zoom is open
      const pane = paneRef.current;
      if (pane && !pane.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handleDown);
    return () => document.removeEventListener("mousedown", handleDown);
  }, [open, zoomIndex, onClose]);

   useEffect(() => {
    if (zoomIndex !== null) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    // cleanup just in case component unmounts while zoom is active
    return () => {
      document.body.style.overflow = "";
    };
  }, [zoomIndex]);

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
                      onClick={() => setZoomIndex(imageUrls.indexOf(c.url!))}
                    />
                </>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Zoom overlay */}
      <div className={`${styles.zoom} ${zoomIndex !== null ? styles.zoomOpen : ""}`} onClick={() => setZoomIndex(null)}>
        {zoomIndex !== null && imageUrls[zoomIndex] && (
          <>
            <button className={styles.zoomClose} onClick={() => setZoomIndex(null)}>
              Close
            </button>
            <img className={styles.zoomImg} src={imageUrls[zoomIndex]} alt="zoomed reference" />
            {imageUrls.length > 1 && (
              <>
                <button
                  className={styles.prevBtn}
                  onClick={(e) => { e.stopPropagation(); setZoomIndex((zoomIndex - 1 + imageUrls.length) % imageUrls.length); }}
                  aria-label="Previous"
                >
                  ‹
                </button>
                <button
                  className={styles.nextBtn}
                  onClick={(e) => { e.stopPropagation(); setZoomIndex((zoomIndex + 1) % imageUrls.length); }}
                  aria-label="Next"
                >
                  ›
                </button>
              </>
            )}
          </>
        )}
      </div>
    </>
  );
}
