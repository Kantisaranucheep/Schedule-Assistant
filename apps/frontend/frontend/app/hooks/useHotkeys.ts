"use client";

import { useState, useEffect } from "react";

export function useHotkeys(setEventModalOpen: (open: boolean) => void, chat: { setChatOpen: (open: boolean) => void }) {
  const [hotkeysOpen, setHotkeysOpenState] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setEventModalOpen(false);
        setHotkeysOpenState(false);
        chat.setChatOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setEventModalOpen, chat]);

  return {
    hotkeysOpen,
    setHotkeysOpen: setHotkeysOpenState,
  };
}