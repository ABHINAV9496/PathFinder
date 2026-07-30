import { useEffect } from "react";

const SITE = "JobbLoot";

export function useTitle(title: string, description?: string) {
  useEffect(() => {
    document.title = title ? `${title} — ${SITE}` : SITE;

    let meta = document.querySelector('meta[name="description"]');
    if (description) {
      if (!meta) {
        meta = document.createElement("meta");
        meta.setAttribute("name", "description");
        document.head.appendChild(meta);
      }
      meta.setAttribute("content", description);
    }
  }, [title, description]);
}
