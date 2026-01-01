"use client";

import { useCallback, useState, useTransition } from "react";
import useSWR from "swr";
import { AlertCircle, Loader2, Play, RefreshCw, TrendingUp } from "lucide-react";

import type { PipelineRun, PipelineStatus } from "@/lib/types";

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load status");
  return (await res.json()) as PipelineStatus;
};

type Props = {
  initialStatus: PipelineStatus;
};

export function PipelineDashboard({ initialStatus }: Props) {
  const { data, mutate } = useSWR("/api/pipeline", fetcher, {
    fallbackData: initialStatus,
    refreshInterval: 20000,
  });
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const triggerRun = useCallback(() => {
    if (data?.isRunning) return;
    setError(null);
    startTransition(() => {
      fetch("/api/pipeline", { method: "POST" })
        .then(async (response) => {
          if (!response.ok) {
            const payload = await response.json();
            throw new Error(payload.error ?? "Pipeline failed");
          }
          return response.json();
        })
        .then(() => mutate())
        .catch((err: Error) => setError(err.message));
    });
  }, [data?.isRunning, mutate]);

  const lastRun = data?.lastRun ?? null;
  const nextScheduleText = data?.nextScheduledAt
    ? new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(data.nextScheduledAt))
    : "Daily at 12:00 UTC";

  return (
    <section className="flex flex-col gap-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
            Viral Shorts Factory
          </h1>
          <p className="text-slate-600">
            Monitor discovery, editing, metadata, and publishing automation in one place.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => mutate()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            disabled={isPending}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={triggerRun}
            disabled={data?.isRunning || isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-2 text-sm font-semibold text-white shadow-lg transition hover:from-indigo-600 hover:to-purple-600 disabled:opacity-60"
          >
            {data?.isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Running…
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Run Pipeline
              </>
            )}
          </button>
        </div>
      </header>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-5 w-5" />
          <div>
            <p className="font-semibold">Pipeline error</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label="Sources processed"
          value={lastRun?.sourcesProcessed ?? 0}
          description="Across YouTube, TikTok, Instagram, podcasts"
        />
        <MetricCard
          label="Shorts published"
          value={lastRun?.shortsPublished ?? 0}
          description="Uploaded via YouTube Data API"
        />
        <MetricCard
          label="Next schedule"
          value={nextScheduleText}
          description="Auto-run cadence"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard
          title="Discovery"
          description="Trending velocity & niche scoring"
          status={lastRun ? "Synced" : "Pending"}
          details={lastRun?.summary ?? "No runs yet"}
        />
        <StatusCard
          title="Editing"
          description="Vertical reframes, subtitles, music, branding"
          status={lastRun && lastRun.shortsPublished > 0 ? "Optimized" : "Queued"}
          details="FFmpeg + AI hooks scoring per segment"
        />
        <StatusCard
          title="Publishing"
          description="Metadata, scheduling, analytics feedback"
          status={lastRun && lastRun.shortsPublished > 0 ? "Live" : "Awaiting"}
          details={`Analytics log: ${lastRun?.analyticsPath ?? "n/a"}`}
        />
      </div>

      <RecentRuns runs={data?.recentRuns ?? []} />
    </section>
  );
}

type MetricProps = {
  label: string;
  value: string | number;
  description: string;
};

function MetricCard({ label, value, description }: MetricProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{description}</p>
    </div>
  );
}

type StatusCardProps = {
  title: string;
  description: string;
  details: string;
  status: "Synced" | "Optimized" | "Live" | "Queued" | "Pending" | "Awaiting";
};

function StatusCard({ title, description, details, status }: StatusCardProps) {
  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
          <TrendingUp className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">{title}</p>
          <p className="text-xs text-slate-500">{description}</p>
        </div>
      </div>
      <div className="mt-4 grow rounded-lg bg-slate-100/80 p-3 text-sm text-slate-600">
        {details}
      </div>
      <div className="mt-4 inline-flex w-fit items-center gap-2 rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
        {status}
      </div>
    </div>
  );
}

type RecentRunsProps = {
  runs: PipelineRun[];
};

function RecentRuns({ runs }: RecentRunsProps) {
  if (!runs.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
        Pipeline status will appear here after the first automation run.
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left font-semibold text-slate-600">
          <tr>
            <th className="px-4 py-3">Completed</th>
            <th className="px-4 py-3">Sources</th>
            <th className="px-4 py-3">Shorts</th>
            <th className="px-4 py-3">Summary</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {runs.map((run) => (
            <tr key={run.id} className="hover:bg-slate-50">
              <td className="px-4 py-3 text-slate-700">
                {new Intl.DateTimeFormat(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                }).format(new Date(run.completedAt))}
              </td>
              <td className="px-4 py-3 text-slate-700">{run.sourcesProcessed}</td>
              <td className="px-4 py-3 text-slate-700">{run.shortsPublished}</td>
              <td className="px-4 py-3 text-slate-500">{run.summary}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
