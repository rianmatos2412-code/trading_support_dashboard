"use client";

import { useState, useRef, useEffect, useCallback, ReactNode } from "react";

const SYMBOL_MANAGER_WIDTH_KEY = "symbol_manager_width";
const DEFAULT_SIDEBAR_WIDTH = 320;
const MIN_SIDEBAR_WIDTH = 240;
const MAX_SIDEBAR_WIDTH = 600;

interface ResizableSidebarProps {
  children: ReactNode;
}

export function ResizableSidebar({ children }: ResizableSidebarProps) {
  const [sidebarWidth, setSidebarWidth] = useState<number>(DEFAULT_SIDEBAR_WIDTH);
  const [isHydrated, setIsHydrated] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const resizeStartX = useRef<number>(0);
  const resizeStartWidth = useRef<number>(0);

  // Load width from localStorage after hydration
  useEffect(() => {
    setIsHydrated(true);
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(SYMBOL_MANAGER_WIDTH_KEY);
      if (stored) {
        const width = parseInt(stored, 10);
        const clampedWidth = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, width));
        setSidebarWidth(clampedWidth);
      }
    }
  }, []);

  // Persist width to localStorage
  useEffect(() => {
    if (isHydrated && typeof window !== "undefined") {
      localStorage.setItem(SYMBOL_MANAGER_WIDTH_KEY, sidebarWidth.toString());
    }
  }, [sidebarWidth, isHydrated]);

  // Handle resize start
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = sidebarWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [sidebarWidth]);

  // Handle resize
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - resizeStartX.current;
      const newWidth = Math.max(
        MIN_SIDEBAR_WIDTH,
        Math.min(MAX_SIDEBAR_WIDTH, resizeStartWidth.current + deltaX)
      );
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  // Handle window resize for responsiveness
  useEffect(() => {
    const handleResize = () => {
      if (typeof window !== "undefined" && sidebarRef.current) {
        const maxWidth = window.innerWidth * 0.5;
        if (sidebarWidth > maxWidth) {
          setSidebarWidth(Math.min(maxWidth, MAX_SIDEBAR_WIDTH));
        }
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => window.removeEventListener("resize", handleResize);
  }, [sidebarWidth]);

  return (
    <>
      <div
        ref={sidebarRef}
        className="flex-shrink-0 border-r border-border overflow-hidden"
        style={{ width: `${sidebarWidth}px` }}
      >
        {children}
      </div>
      <div
        className="flex-shrink-0 w-1 bg-border hover:bg-primary/50 cursor-col-resize transition-colors relative group"
        onMouseDown={handleResizeStart}
      >
        <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-2" />
        {isResizing && <div className="absolute inset-0 bg-primary/30" />}
      </div>
    </>
  );
}

