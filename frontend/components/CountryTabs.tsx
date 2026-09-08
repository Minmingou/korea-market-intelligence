import Link from "next/link";
import type { Country } from "@/types/market";

const TABS: { country: Country; label: string; href: string }[] = [
  { country: "KR", label: "국내", href: "/" },
  { country: "US", label: "미국", href: "/?country=us" },
];

export default function CountryTabs({ active }: { active: Country }) {
  return (
    <nav className="flex gap-1 border border-neutral-800 p-1 text-sm">
      {TABS.map((tab) => (
        <Link
          key={tab.country}
          href={tab.href}
          className={`px-3 py-1 ${
            tab.country === active
              ? "bg-neutral-100 text-black"
              : "text-neutral-300 hover:bg-neutral-900"
          }`}
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}
