import { PipelineDashboard } from "@/components/pipeline-dashboard";
import { readStatus } from "@/lib/pipeline";

export default function Home() {
  const status = readStatus();
  return (
    <main className="min-h-screen bg-slate-950 py-12 text-slate-950">
      <div className="mx-auto max-w-6xl rounded-3xl bg-white/95 px-6 py-12 shadow-2xl backdrop-blur md:px-12">
        <PipelineDashboard initialStatus={status} />
      </div>
    </main>
  );
}
