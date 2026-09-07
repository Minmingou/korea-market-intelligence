"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { searchStocks } from "@/lib/api";
import type { StockSearchResult } from "@/types/market";

const DEBOUNCE_MS = 250;

export default function SearchBar() {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [closed, setClosed] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const trimmedQuery = query.trim();
  const isOpen = !closed && trimmedQuery.length > 0;

  useEffect(() => {
    if (!trimmedQuery) return;

    let cancelled = false;
    const timer = setTimeout(() => {
      searchStocks(trimmedQuery, 10)
        .then((res) => {
          if (cancelled) return;
          setResults(res.items);
          setActiveIndex(-1);
        })
        .catch(() => {
          if (cancelled) return;
          setResults([]);
        });
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [trimmedQuery]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setClosed(true);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleChange(value: string) {
    setQuery(value);
    setClosed(false);
  }

  function goToStock(code: string) {
    setClosed(true);
    setQuery("");
    router.push(`/stocks/${code}`);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!isOpen || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      goToStock(results[activeIndex].stock_code);
    } else if (e.key === "Escape") {
      setClosed(true);
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-xs">
      <input
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        onFocus={() => setClosed(false)}
        onKeyDown={handleKeyDown}
        placeholder="종목명 또는 코드 검색"
        className="w-full border border-neutral-700 bg-black px-3 py-1.5 text-sm text-neutral-100 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none"
      />
      {isOpen && (
        <ul className="absolute z-10 mt-1 max-h-80 w-full overflow-y-auto border border-neutral-700 bg-black text-sm shadow-lg">
          {results.length === 0 ? (
            <li className="px-3 py-2 text-neutral-400">검색 결과가 없습니다.</li>
          ) : (
            results.map((item, idx) => (
              <li key={item.stock_code}>
                <button
                  onClick={() => goToStock(item.stock_code)}
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={`flex w-full items-center justify-between px-3 py-2 text-left ${
                    idx === activeIndex ? "bg-neutral-800" : "hover:bg-neutral-900"
                  }`}
                >
                  <span className="truncate text-neutral-100">{item.stock_name}</span>
                  <span className="ml-2 shrink-0 text-xs text-neutral-400">
                    {item.stock_code} · {item.market}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
