import { formatTime } from "@/lib/format";

type AiBriefData = {
  summary: string;
  data_source: string;
  generated_at: string;
};

export default function AiBrief({ title, data }: { title: string; data: AiBriefData }) {
  return (
    <section className="border border-neutral-800 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">{title}</h2>
        <span className="text-xs text-neutral-600">
          {data.data_source === "mock" ? "MOCK BRIEF" : "AI BRIEF"}
        </span>
      </div>
      <p className="whitespace-pre-line text-sm leading-relaxed text-neutral-200">{data.summary}</p>
      <p className="mt-2 text-xs text-neutral-600">생성 시각: {formatTime(data.generated_at)}</p>
    </section>
  );
}
