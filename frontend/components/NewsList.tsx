import type { NewsList as NewsListData } from "@/types/market";

export default function NewsList({ data }: { data: NewsListData }) {
  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">RECENT NEWS</h2>
        <span className="text-xs text-neutral-600">
          {data.data_source === "mock" ? "MOCK DATA" : "뉴스"}
        </span>
      </div>

      <ul className="space-y-1 text-sm">
        {data.items.map((item, i) => (
          <li key={`${item.title}-${i}`} className="flex items-center justify-between gap-2">
            {item.url ? (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="truncate text-neutral-200 underline decoration-neutral-700 underline-offset-2 hover:text-neutral-50"
              >
                {item.title}
              </a>
            ) : (
              <span className="truncate text-neutral-200">{item.title}</span>
            )}
            <span className="flex shrink-0 gap-3 text-xs text-neutral-500 tabular-nums">
              <span className="hidden sm:inline">{item.source}</span>
              <span>{item.published_at}</span>
            </span>
          </li>
        ))}
        {data.items.length === 0 && <li className="text-neutral-600">최근 뉴스 없음</li>}
      </ul>
    </section>
  );
}
