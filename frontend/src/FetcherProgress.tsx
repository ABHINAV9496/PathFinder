import { useEffect, useRef, useState, createContext, useContext, useCallback } from "react";
import { api } from "./api/client";

interface FetcherProgress {
  running: boolean;
  percent: number;
  message: string;
  step: string;
  details: Record<string, number>;
  elapsed_seconds?: number;
}

interface FetcherCtx {
  progress: FetcherProgress | null;
  running: boolean;
  startFetcher: () => void;
}

const FetcherContext = createContext<FetcherCtx>({
  progress: null,
  running: false,
  startFetcher: () => {},
});

export function useFetcher() {
  return useContext(FetcherContext);
}

const PLACEHOLDER: FetcherProgress = {
  running: true,
  percent: 0,
  message: "Starting fetcher...",
  step: "starting",
  details: {},
};

export function FetcherProvider({ children }: { children: React.ReactNode }) {
  const [progress, setProgress] = useState<FetcherProgress | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const aliveRef = useRef(true);

  useEffect(() => {
    aliveRef.current = true;
    checkExistingRun();
    return () => {
      aliveRef.current = false;
      stopPolling();
    };
  }, []);

  async function checkExistingRun() {
    try {
      const data = await api.fetcher.status();
      if (data.running) {
        const p: FetcherProgress = {
          running: true,
          percent: Number(data.percent) || 0,
          message: String(data.message || ""),
          step: String(data.step || ""),
          details: (data.details as Record<string, number>) || {},
          elapsed_seconds: data.elapsed_seconds as number | undefined,
        };
        setProgress(p);
        startPolling();
      }
    } catch {
      // server not reachable, no problem
    }
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function startPolling() {
    stopPolling();
    pollRef.current = setInterval(async () => {
      if (!aliveRef.current) return;
      try {
        const data = await api.fetcher.status();
        const p: FetcherProgress = {
          running: !!data.running,
          percent: Number(data.percent) || 0,
          message: String(data.message || ""),
          step: String(data.step || ""),
          details: (data.details as Record<string, number>) || {},
          elapsed_seconds: data.elapsed_seconds as number | undefined,
        };
        setProgress(p);
        if (!p.running) {
          stopPolling();
          setTimeout(() => setProgress(null), 5000);
        }
      } catch {
        // keep polling, next tick may work
      }
    }, 2000);
  }

  const startFetcher = useCallback(async () => {
    setProgress(PLACEHOLDER);
    try {
      await api.fetcher.run();
      startPolling();
    } catch {
      setProgress(null);
      stopPolling();
    }
  }, []);

  const running = progress?.running ?? false;

  return (
    <FetcherContext.Provider value={{ progress, running, startFetcher }}>
      {children}
    </FetcherContext.Provider>
  );
}
