import type { NewsList as NewsListData } from "@/types/market";

export default function NewsList({ data }: { data: NewsListData }) {
  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">RECENT NEWS</h2>
        <span className="text-xs text-neutral-400">
          {data.data_source === "mock" ? "MOCK DATA" : "네이버 뉴스"}
        </span>
      </div>

      {data.items.length === 0 ? (
        <p className="text-sm text-neutral-400">최근 뉴스 없음</p>
      ) : (
        <table className="w-full table-fixed text-sm">
          <tbody>
            {data.items.map((item, i) => (
              <tr key={`${item.title}-${i}`} className="border-b border-neutral-900 last:border-0">
                <td className="w-1/2 py-1 pr-2 sm:w-3/5">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block truncate text-neutral-200 underline decoration-neutral-700 underline-offset-2 hover:text-neutral-50"
                    >
                      {item.title}
                    </a>
                  ) : (
                    <span className="block truncate text-neutral-200">{item.title}</span>
                  )}
                </td>
                <td className="hidden truncate py-1 pr-2 text-xs text-neutral-300 sm:table-cell">
                  {item.source}
                </td>
                <td className="w-20 py-1 text-right text-xs tabular-nums text-neutral-300">
                  {item.published_at}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
