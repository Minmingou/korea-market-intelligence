"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getStock } from "@/lib/api";
import { changeColorClass, formatChangeRate, formatMoney, formatPrice } from "@/lib/format";
import { currencyForMarket } from "@/lib/market";
import { WATCHLIST_EVENT, getWatchlist, removeFromWatchlist } from "@/lib/watchlist";
import type { Stock } from "@/types/market";

export default function Watchlist() {
  // null = 최초 마운트 전(하이드레이션 불일치 방지, RefreshButton과 동일한 패턴)
  const [codes, setCodes] = useState<string[] | null>(null);
  const [stocks, setStocks] = useState<Record<string, Stock | null>>({});

  useEffect(() => {
    function sync() {
      setCodes(getWatchlist());
    }
    sync();
    window.addEventListener(WATCHLIST_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(WATCHLIST_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  useEffect(() => {
    if (!codes || codes.length === 0) return;
    let cancelled = false;
    Promise.all(
      codes.map((code) =>
        getStock(code)
          .then((stock) => [code, stock] as const)
          .catch(() => [code, null] as const),
      ),
    ).then((entries) => {
      if (!cancelled) setStocks(Object.fromEntries(entries));
    });
    return () => {
      cancelled = true;
    };
  }, [codes]);

  if (codes === null) return null;

  return (
    <section>
      <h2 className="mb-2 text-sm font-semibold tracking-wide text-neutral-400">MY WATCHLIST</h2>
      {codes.length === 0 ? (
        <p className="border border-neutral-800 p-4 text-sm text-neutral-400">
          관심종목이 없습니다. 종목 상세 페이지의 ☆ 관심종목 버튼으로 추가하세요.
        </p>
      ) : (
        <div className="overflow-x-auto border border-neutral-800">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-neutral-800 text-xs text-neutral-400">
                <th className="px-3 py-2 text-left">종목명</th>
                <th className="px-3 py-2 text-right">현재가</th>
                <th className="px-3 py-2 text-right">등락률</th>
                <th className="px-3 py-2 text-right">거래대금</th>
                <th className="px-3 py-2 text-right">외국인 순매수</th>
                <th className="px-3 py-2 text-right" />
              </tr>
            </thead>
            <tbody>
              {codes.map((code) => {
                const stock = stocks[code];
                const currency = stock ? currencyForMarket(stock.market) : "KRW";
                return (
                  <tr key={code} className="border-b border-neutral-900 last:border-0">
                    <td className="px-3 py-2">
                      <Link href={`/stocks/${code}`} className="text-neutral-200 hover:underline">
                        {stock ? stock.stock_name : code}
                      </Link>
                      <span className="ml-1 text-xs text-neutral-500">{code}</span>
                    </td>
                    {stock ? (
                      <>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {formatPrice(stock.price, currency)}
                        </td>
                        <td
                          className={`px-3 py-2 text-right tabular-nums ${changeColorClass(stock.change_rate)}`}
                        >
                          {formatChangeRate(stock.change_rate)}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums text-neutral-300">
                          {formatMoney(stock.trading_value, currency)}
                        </td>
                        <td
                          className={`px-3 py-2 text-right tabular-nums ${changeColorClass(stock.foreign_net_buy)}`}
                        >
                          {formatMoney(stock.foreign_net_buy, currency)}
                        </td>
                      </>
                    ) : (
                      <td className="px-3 py-2 text-right text-neutral-500" colSpan={4}>
                        N/A
                      </td>
                    )}
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => removeFromWatchlist(code)}
                        className="text-xs text-neutral-500 hover:text-red-400"
                      >
                        제거
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
