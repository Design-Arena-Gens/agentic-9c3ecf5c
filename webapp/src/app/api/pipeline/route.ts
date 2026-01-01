import { NextResponse } from "next/server";

import { readStatus, recordStatus, summarizeLatestRun, triggerPipeline } from "@/lib/pipeline";

export async function GET() {
  const status = readStatus();
  return NextResponse.json(status);
}

export async function POST() {
  try {
    const run = await triggerPipeline();
    const status = readStatus();
    recordStatus({
      ...status,
      lastRun: run,
    });
    return NextResponse.json(run);
  } catch (error) {
    const status = readStatus();
    recordStatus({
      ...status,
      isRunning: false,
    });
    return NextResponse.json(
      {
        error: (error as Error).message,
        lastRun: status.lastRun ?? summarizeLatestRun(),
      },
      { status: 500 },
    );
  }
}
