"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2 } from "lucide-react";

export function PageLoadingBar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const prevPathnameRef = useRef<string>("");
  const completionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Get current path
    const currentPath = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : "");
    
    // Check if this is an actual navigation (pathname changed)
    if (prevPathnameRef.current && prevPathnameRef.current !== currentPath) {
      // Start loading on navigation
      setIsLoading(true);

      // Clear any existing timeouts
      if (completionTimeoutRef.current) {
        clearTimeout(completionTimeoutRef.current);
      }

      // Complete loading when page is ready
      const handleComplete = () => {
        if (completionTimeoutRef.current) {
          clearTimeout(completionTimeoutRef.current);
          completionTimeoutRef.current = null;
        }
        // Small delay to ensure smooth transition
        setTimeout(() => {
          setIsLoading(false);
        }, 300);
      };

      // Check if page is already loaded
      if (typeof window !== "undefined") {
        if (document.readyState === "complete") {
          // Page already loaded, complete immediately
          setTimeout(handleComplete, 100);
        } else {
          // Wait for page to load
          window.addEventListener("load", handleComplete, { once: true });
          
          // Fallback: complete after max 3 seconds
          completionTimeoutRef.current = setTimeout(handleComplete, 3000);
        }
      }
    }

    // Update previous pathname
    prevPathnameRef.current = currentPath;

    return () => {
      if (completionTimeoutRef.current) {
        clearTimeout(completionTimeoutRef.current);
      }
    };
  }, [pathname, searchParams]);

  return (
    <AnimatePresence>
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[9999] bg-background/80 backdrop-blur-sm flex items-center justify-center pointer-events-none"
        >
          <div className="flex flex-col items-center gap-4">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{
                duration: 1,
                repeat: Infinity,
                ease: "linear",
              }}
            >
              <Loader2 className="h-8 w-8 text-primary" />
            </motion.div>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-sm text-muted-foreground"
            >
              Loading...
            </motion.p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
