import { Construction } from "lucide-react";

export default function Placeholder({
  title,
  description,
  planned,
}: {
  title: string;
  description: string;
  planned: string[];
}) {
  return (
    <div className="card mx-auto max-w-3xl">
      <div className="flex items-start gap-4">
        <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600">
          <Construction size={20} />
        </span>
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-ink-muted">{description}</p>
        </div>
      </div>
      <div className="mt-5 rounded-xl bg-brand-50 p-4">
        <p className="text-xs font-bold uppercase tracking-wide text-brand-600">
          This module is online in the build pipeline
        </p>
        <ul className="mt-2 grid gap-1 text-sm text-ink-soft sm:grid-cols-2">
          {planned.map((p) => (
            <li key={p} className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400" />
              {p}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}