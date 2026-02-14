"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { JobLog } from "@/lib/types";

interface JobLogsProps {
  jobId: number;
}

const levelColors = {
  info: "text-blue-600 dark:text-blue-400",
  warning: "text-yellow-600 dark:text-yellow-400",
  error: "text-red-600 dark:text-red-400",
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
        className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
      >
        {expanded ? "Hide logs" : "Show logs"}
      </button>

      {expanded && job?.logs && (
        <div className="mt-2 space-y-1 pl-4 border-l-2 border-gray-200 dark:border-gray-700">
          {job.logs.length > 0 ? (
            job.logs.map((log: JobLog) => (
              <div key={log.id} className="text-sm">
                <span className="text-gray-400 dark:text-gray-500 mr-2">
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
                <span
                  className={`font-medium mr-2 ${
                    levelColors[log.level as keyof typeof levelColors] ||
                    "text-gray-600"
                  }`}
                >
                  [{log.level.toUpperCase()}]
                </span>
                <span className="text-gray-700 dark:text-gray-300">
                  {log.message}
                </span>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No logs available
            </p>
          )}
        </div>
      )}
    </div>
  );
}
