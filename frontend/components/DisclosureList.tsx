import type { DisclosureList as DisclosureListData } from "@/types/market";

function formatDisclosureDate(rceptDt: string): string {
  if (rceptDt.length !== 8) return rceptDt;
  return `${rceptDt.slice(0, 4)}-${rceptDt.slice(4, 6)}-${rceptDt.slice(6, 8)}`;
}

export default function DisclosureList({ data }: { data: DisclosureListData }) {
  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">RECENT DISCLOSURES</h2>
        <span className="text-xs text-neutral-400">
          {data.data_source === "mock" ? "MOCK DATA" : "DART 전자공시"}
        </span>
      </div>

      <ul className="space-y-1 text-sm">
        {data.items.map((item) => (
          <li key={item.rcept_no} className="flex items-center justify-between gap-2">
            {item.url ? (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="truncate text-neutral-200 underline decoration-neutral-700 underline-offset-2 hover:text-neutral-50"
              >
                {item.report_nm}
              </a>
            ) : (
              <span className="truncate text-neutral-200">{item.report_nm}</span>
            )}
            <span className="flex shrink-0 gap-3 text-xs text-neutral-300 tabular-nums">
              <span className="hidden sm:inline">{item.flr_nm}</span>
              <span>{formatDisclosureDate(item.rcept_dt)}</span>
            </span>
          </li>
        ))}
        {data.items.length === 0 && <li className="text-neutral-400">최근 공시 없음</li>}
      </ul>
    </section>
  );
}
