import { createContext, useContext, useState, useCallback, useRef, useEffect, type ReactNode } from 'react';

interface LogWindowContextValue {
  isOpen: boolean;
  pulse: boolean;
  openLog: () => void;
  closeLog: () => void;
}

const Ctx = createContext<LogWindowContextValue | null>(null);

export function LogWindowProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [pulse, setPulse] = useState(false);
  const pulseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (pulseTimer.current) clearTimeout(pulseTimer.current);
    };
  }, []);

  const openLog = useCallback(() => {
    if (isOpen) {
      // Already open — pulse to draw attention
      setPulse(true);
      if (pulseTimer.current) clearTimeout(pulseTimer.current);
      pulseTimer.current = setTimeout(() => setPulse(false), 700);
      return;
    }
    setIsOpen(true);
  }, [isOpen]);

  const closeLog = useCallback(() => {
    setIsOpen(false);
  }, []);

  return (
    <Ctx.Provider value={{ isOpen, pulse, openLog, closeLog }}>
      {children}
    </Ctx.Provider>
  );
}

export function useLogWindow() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useLogWindow must be used inside LogWindowProvider');
  return ctx;
}
