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

      {data.items.length === 0 ? (
        <p className="text-sm text-neutral-400">최근 공시 없음</p>
      ) : (
        <table className="w-full table-fixed text-sm">
          <tbody>
            {data.items.map((item) => (
              <tr key={item.rcept_no} className="border-b border-neutral-900 last:border-0">
                <td className="w-1/2 py-1 pr-2 sm:w-3/5">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block truncate text-neutral-200 underline decoration-neutral-700 underline-offset-2 hover:text-neutral-50"
                    >
                      {item.report_nm}
                    </a>
                  ) : (
                    <span className="block truncate text-neutral-200">{item.report_nm}</span>
                  )}
                </td>
                <td className="hidden truncate py-1 pr-2 text-xs text-neutral-300 sm:table-cell">
                  {item.flr_nm}
                </td>
                <td className="w-24 py-1 text-right text-xs tabular-nums text-neutral-300">
                  {formatDisclosureDate(item.rcept_dt)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
