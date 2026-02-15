"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { JobLog } from "@/lib/types";

interface JobLogsProps {
  jobId: number;
}

const levelConfig: Record<string, { color: string; label: string }> = {
  info: { color: "bg-sky text-ink", label: "INFO" },
  warning: { color: "bg-orange text-ink", label: "WARN" },
  error: { color: "bg-primary text-white", label: "ERR" },
};

export function JobLogs({ jobId }: JobLogsProps) {
  const [expanded, setExpanded] = useState(false);

  const { data: job } = useSWR(
    expanded ? `/api/jobs/${jobId}` : null,
    () => api.jobs.get(jobId)
  );

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs font-bold text-ink/40 hover:text-secondary transition-colors"
      >
        {expanded ? "Hide logs ▲" : "Show logs ▼"}
      </button>

      {expanded && job?.logs && (
        <div className="mt-2 space-y-1 pl-3 border-l-2 border-ink/20">
          {job.logs.length > 0 ? (
            job.logs.map((log: JobLog) => {
              const config = levelConfig[log.level] || { color: "bg-muted text-white", label: log.level };
              return (
                <div key={log.id} className="text-xs flex items-start gap-2">
                  <span className="text-ink/30 font-mono shrink-0">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                  <span className={`px-1.5 py-0 text-[10px] font-bold border border-ink ${config.color} shrink-0`}>
                    {config.label}
                  </span>
                  <span className="text-ink/70 font-mono break-all">{log.message}</span>
                </div>
              );
            })
          ) : (
            <p className="text-xs text-ink/30 font-medium">No logs available</p>
          )}
        </div>
      )}
    </div>
  );
}
