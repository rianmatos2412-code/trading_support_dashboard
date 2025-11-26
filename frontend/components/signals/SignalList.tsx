"use client";

import { memo, useEffect, useMemo, useRef, useState } from "react";
import { List, type RowComponentProps } from "react-window";
import { Card } from "@/components/ui/card";
import { useSignalsStore } from "@/stores/useSignalsStore";
import { SignalRow } from "./SignalRow";

interface SignalListProps {
  signalIds: string[];
  rowHeight?: number;
  overscanCount?: number;
}

interface VirtualizedRowProps extends RowComponentProps<SignalListRowProps> {}

interface SignalListRowProps {
  ids: string[];
}

const DEFAULT_ROW_HEIGHT = 80;
const MIN_LIST_HEIGHT = 360;
const HEIGHT_OFFSET = 320;

const rowsAreEqual = (prev: VirtualizedRowProps, next: VirtualizedRowProps) =>
  prev.index === next.index &&
  prev.style === next.style &&
  prev.ids === next.ids &&
  prev["ariaAttributes"] === next["ariaAttributes"];

const VirtualizedRow = memo(
  ({ index, style, ids, ariaAttributes }: VirtualizedRowProps) => {
    const signalId = ids[index];
    const signal = useSignalsStore((state) => state.signalMap[signalId]);

    if (!signal) {
      return null;
    }

    return (
      <div {...ariaAttributes} style={style} className="px-1">
        <SignalRow signal={signal} />
      </div>
    );
  },
  rowsAreEqual
);

VirtualizedRow.displayName = "VirtualizedRow";

export function SignalList({
  signalIds,
  rowHeight = DEFAULT_ROW_HEIGHT,
  overscanCount = 20,
}: SignalListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [containerWidth, setContainerWidth] = useState<number>(() =>
    typeof window === "undefined" ? 1200 : window.innerWidth
  );
  const [listHeight, setListHeight] = useState<number>(() =>
    typeof window === "undefined"
      ? MIN_LIST_HEIGHT
      : Math.max(window.innerHeight - HEIGHT_OFFSET, MIN_LIST_HEIGHT)
  );

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const handleResize = () => {
      setListHeight(Math.max(window.innerHeight - HEIGHT_OFFSET, MIN_LIST_HEIGHT));
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [mounted]);

  useEffect(() => {
    if (!mounted) return;
    const node = containerRef.current;
    if (!node || typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      if (!Array.isArray(entries) || !entries.length) return;
      const entry = entries[0];
      setContainerWidth(entry.contentRect.width);
    });
    observer.observe(node);
    setContainerWidth(node.clientWidth);
    return () => observer.disconnect();
  }, [mounted]);

  const rowProps = useMemo<SignalListRowProps>(
    () => ({
      ids: signalIds,
    }),
    [signalIds]
  );

  if (!mounted) {
    return <div className="h-[400px] w-full rounded-lg border border-dashed border-border/40" />;
  }

  if (!signalIds.length) {
    return (
      <Card className="flex h-[320px] items-center justify-center text-muted-foreground">
        No signals match the current filters.
      </Card>
    );
  }

  const computedWidth = Math.max(containerWidth, 320);

  return (
    <div
      ref={containerRef}
      className="w-full flex-1"
      style={{ height: listHeight, minHeight: MIN_LIST_HEIGHT }}
    >
      <List
        defaultHeight={listHeight}
        style={{ height: listHeight, width: computedWidth }}
        rowCount={signalIds.length}
        rowHeight={rowHeight}
        rowProps={rowProps}
        rowComponent={VirtualizedRow}
        overscanCount={overscanCount}
      />
    </div>
  );
}


