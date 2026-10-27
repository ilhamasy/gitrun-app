"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  Loader2,
  AlertCircle,
  Terminal,
  RotateCcw,
  Sparkles,
  BookOpen,
  MessageSquare,
  Network,
  GitBranch,
  Plus,
  Trash2,
} from "lucide-react";

interface StageConfig {
  id: string;
  stage: string;
  detail: string;
  body: string;
}

const SINGLE_STAGES: StageConfig[] = [
  {
    id: "clone",
    stage: "Clone",
    detail: "git clone --depth 1",
    body: "A shallow clone of the repository at its default branch, discarded after the run.",
  },
  {
    id: "bundle",
    stage: "Bundle",
    detail: "repomix --ignore",
    body: "Source packed into one token-efficient file with tests, lockfiles, and binaries excluded.",
  },
  {
    id: "toc",
    stage: "Outline",
    detail: "pass 1 · table of contents",
    body: "One model call writes the contents for the fixed page set: overview, architecture, setup, API reference.",
  },
  {
    id: "doc_gen",
    stage: "Pages",
    detail: "pass 2 · parallel generation",
    body: "One call per page, run concurrently, each written from the bundle and the outline.",
  },
  {
    id: "pageindex",
    stage: "Index",
    detail: "headings → tree",
    body: "Headings become nodes with one-line summaries — the structure the chat reasons over.",
  },
];

const SYSTEM_STAGES: StageConfig[] = [
  {
    id: "system_init",
    stage: "Mesh Init",
    detail: "topology coordinator",
    body: "Initializes multi-repo context and registers member microservice boundaries.",
  },
  {
    id: "clone_all",
    stage: "Parallel Clone",
    detail: "git clone --depth 1",
    body: "Clones all member microservices concurrently into isolated environments.",
  },
  {
    id: "bundle_all",
    stage: "Repomix Bundle All",
    detail: "repomix --ignore",
    body: "Packs each microservice codebase into token-efficient XML skeletons.",
  },
  {
    id: "synthesize_members",
    stage: "Member Wikis",
    detail: "pass 1 & 2 per repo",
    body: "Synthesizes standard documentation pages for every member microservice repository.",
  },
  {
    id: "mesh_extract",
    stage: "Topology & Links",
    detail: "cross-service discovery",
    body: "Discovers synchronous RPCs, Kafka topics, and injects peer cross-links into every page.",
  },
  {
    id: "pageindex_all",
    stage: "PageIndex Trees",
    detail: "headings → trees",
    body: "Builds vectorless tree indexes for each microservice and the federated system.",
  },
];

const SINGLE_PRESETS = [
  { label: "Payment Gateway", value: "payment-gateway", desc: "Go · distributed idempotency" },
  { label: "Auth Sentinel", value: "auth-sentinel", desc: "TypeScript · OAuth2 / OIDC" },
  { label: "Express.js", value: "https://github.com/expressjs/express", desc: "Node.js web framework" },
];

type StepStatus = "idle" | "running" | "completed" | "error";

interface LogEntry {
  id: string;
  timestamp: string;
  step: string;
  text: string;
}

interface MemberInput {
  name: string;
  url: string;
}

export function IngestionStepper() {
  const [mode, setMode] = useState<"single" | "system">("single");

  // Single repo state
  const [url, setUrl] = useState("payment-gateway");

  // Multi-repo system state
  const [systemName, setSystemName] = useState("checkout-mesh");
  const [systemDisplayName, setSystemDisplayName] = useState("Checkout & Identity Mesh");
  const [systemRepos, setSystemRepos] = useState<MemberInput[]>([
    { name: "auth-sentinel", url: "auth-sentinel" },
    { name: "payment-gateway", url: "payment-gateway" },
  ]);

  const [status, setStatus] = useState<"idle" | "running" | "completed" | "error">("idle");
  const [activeStep, setActiveStep] = useState<string | null>(null);
  const [stepStates, setStepStates] = useState<Record<string, StepStatus>>({});
  const [stepDetails, setStepDetails] = useState<Record<string, string>>({});
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [result, setResult] = useState<{
    repo?: string;
    system?: string;
    display_name?: string;
    services_count?: number;
    repos?: string[];
    redirect: string;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const activeStages = mode === "single" ? SINGLE_STAGES : SYSTEM_STAGES;

  // Auto-scroll log ticker
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const addLog = (step: string, text: string) => {
    const time = new Date().toLocaleTimeString("en-GB", { hour12: false });
    setLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        timestamp: time,
        step,
        text,
      },
    ]);
  };

  const addRepoRow = () => {
    setSystemRepos((prev) => [...prev, { name: "", url: "" }]);
  };

  const updateRepoRow = (index: number, field: "name" | "url", val: string) => {
    setSystemRepos((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: val };
      return next;
    });
  };

  const removeRepoRow = (index: number) => {
    if (systemRepos.length <= 1) return;
    setSystemRepos((prev) => prev.filter((_, i) => i !== index));
  };

  const loadSystemPreset = () => {
    setSystemName("checkout-mesh");
    setSystemDisplayName("Checkout & Identity Mesh");
    setSystemRepos([
      { name: "auth-sentinel", url: "auth-sentinel" },
      { name: "payment-gateway", url: "payment-gateway" },
    ]);
  };

  const startIngestion = async () => {
    if (status === "running") return;

    if (mode === "single" && !url.trim()) return;
    if (mode === "system" && (!systemName.trim() || systemRepos.length === 0)) return;

    setStatus("running");
    setErrorMessage(null);
    setResult(null);
    setLogs([]);
    setStepDetails({});

    const initialStates: Record<string, StepStatus> = {};
    activeStages.forEach((s, idx) => {
      initialStates[s.id] = idx === 0 ? "running" : "idle";
    });
    setStepStates(initialStates);
    setActiveStep(activeStages[0].id);

    const payload =
      mode === "single"
        ? { url: url.trim() }
        : {
            system_name: systemName.trim(),
            display_name: systemDisplayName.trim() || undefined,
            repos: systemRepos.filter((r) => r.name.trim() && r.url.trim()),
          };

    addLog(
      "system",
      mode === "single"
        ? `Starting ingestion for: ${url.trim()}`
        : `Starting multi-repo system ingestion for: ${systemDisplayName} (${systemRepos.length} repos)`
    );

    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Pipeline request failed with status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body stream received from server");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          if (!block.trim()) continue;

          let eventName = "message";
          let dataStr = "";

          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) {
              eventName = line.replace("event:", "").trim();
            } else if (line.startsWith("data:")) {
              dataStr += line.replace("data:", "").trim();
            }
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            if (eventName === "step") {
              const stepName = data.step as string;
              setActiveStep(stepName);

              // Mark previous steps completed
              setStepStates((prev) => {
                const next = { ...prev };
                const order = activeStages.map((s) => s.id);
                const currIdx = order.indexOf(stepName);
                if (currIdx !== -1) {
                  for (let i = 0; i < currIdx; i++) {
                    next[order[i]] = "completed";
                  }
                  next[stepName] = "running";
                }
                return next;
              });

              if (data.progress) {
                setStepDetails((prev) => ({
                  ...prev,
                  [stepName]: data.page ? `${data.progress} (${data.page})` : data.progress,
                }));
                addLog(stepName, `${data.progress}${data.page ? ` · ${data.page}` : ""}`);
              } else if (data.message) {
                setStepDetails((prev) => ({ ...prev, [stepName]: data.message }));
                addLog(stepName, data.message);
              }
            } else if (eventName === "done") {
              const finalStates: Record<string, StepStatus> = {};
              activeStages.forEach((s) => {
                finalStates[s.id] = "completed";
              });
              setStepStates(finalStates);
              setStatus("completed");
              setActiveStep(null);
              setResult({
                repo: data.repo,
                system: data.system,
                display_name: data.display_name || data.repo,
                services_count: data.services_count,
                repos: data.repos,
                redirect: data.redirect || (data.system ? `/wiki/${data.system}/overview` : `/wiki/${data.repo}/overview`),
              });
              addLog("system", `Ingestion completed successfully.`);
            } else if (eventName === "error") {
              setStatus("error");
              setErrorMessage(data.error || "An unhandled pipeline error occurred.");
              addLog("error", data.error || "Pipeline failure");
            }
          } catch {
            // Ignore malformed chunk
          }
        }
      }
    } catch (err: unknown) {
      setStatus("error");
      const errStr = err instanceof Error ? err.message : String(err);
      setErrorMessage(errStr);
      addLog("error", errStr);
    }
  };

  const handleReset = () => {
    setStatus("idle");
    setActiveStep(null);
    setResult(null);
    setErrorMessage(null);
    setLogs([]);
    setStepStates({});
    setStepDetails({});
  };

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_24rem]">
      {/* Left Column: Visual Stepper Line */}
      <section aria-labelledby="stages-heading">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 id="stages-heading" className="label text-ink">
              Pipeline stages
            </h2>
            <span className="font-mono text-xs text-ink-3">
              [{mode === "single" ? "Single Repo" : "Microservice Mesh"}]
            </span>
          </div>

          {status === "running" && (
            <span className="inline-flex items-center gap-1.5 text-xs font-mono text-line-cedar">
              <span className="h-2 w-2 animate-ping bg-line-cedar" />
              Live runner active
            </span>
          )}
        </div>

        <ol className="relative">
          {/* Background rail */}
          <span
            aria-hidden="true"
            className="absolute bottom-6 left-[0.6875rem] top-3 w-[3px] bg-ink/15"
          />

          {activeStages.map((step, index) => {
            const state = stepStates[step.id] || "idle";
            const isRunning = state === "running";
            const isCompleted = state === "completed";
            const isError = state === "error";
            const detailText = stepDetails[step.id];

            return (
              <li
                key={step.id}
                className="relative grid grid-cols-[1.5rem_minmax(0,1fr)] gap-4 pb-7"
              >
                {/* Station Node Badge */}
                <span
                  className={`relative z-10 mt-1 flex h-6 w-6 items-center justify-center border-2 transition-colors duration-300 ${
                    isCompleted
                      ? "border-line-cedar bg-line-cedar text-white"
                      : isRunning
                      ? "border-ink bg-signal text-ink shadow-[0_0_12px_rgba(245,197,24,0.6)]"
                      : isError
                      ? "border-fault bg-fault text-white"
                      : "border-ink bg-paper"
                  }`}
                  aria-hidden="true"
                >
                  {isCompleted ? (
                    <Check className="h-3.5 w-3.5 stroke-[3]" />
                  ) : isRunning ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : isError ? (
                    <AlertCircle className="h-3.5 w-3.5" />
                  ) : (
                    <span className="h-1.5 w-1.5 bg-ink/20" />
                  )}
                </span>

                {/* Stage Info */}
                <div>
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <h3
                      className={`signage text-[1.375rem] ${
                        isRunning ? "text-ink underline decoration-signal decoration-2 underline-offset-4" : ""
                      }`}
                    >
                      {step.stage}
                    </h3>
                    <span className="data text-ink-3">{step.detail}</span>

                    {isRunning && (
                      <span className="tag tag-on-signal ml-auto text-[0.6875rem] uppercase tracking-wider">
                        Running
                      </span>
                    )}
                    {isCompleted && (
                      <span className="ml-auto font-mono text-[0.6875rem] font-bold text-line-cedar uppercase tracking-wider">
                        Complete
                      </span>
                    )}
                  </div>

                  <p className="mt-1 max-w-[56ch] text-[0.9375rem] leading-relaxed text-ink-2">
                    {step.body}
                  </p>

                  {/* Dynamic Progress / Step Detail */}
                  {detailText && (
                    <div className="mt-2 inline-flex items-center gap-1.5 border border-hairline bg-paper-2 px-2.5 py-1 font-mono text-xs text-ink">
                      <span className="h-1.5 w-1.5 bg-ink" />
                      <span>{detailText}</span>
                    </div>
                  )}

                  <p className="label-wide mt-2 text-ink-3">
                    Stage {String(index + 1).padStart(2, "0")} of {String(activeStages.length).padStart(2, "0")}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>

        {/* Live SSE Event Log Terminal */}
        {logs.length > 0 && (
          <div className="mt-4 border border-hairline bg-surface">
            <div className="flex items-center justify-between border-b border-hairline bg-paper-2 px-3 py-2 text-xs">
              <span className="flex items-center gap-2 font-mono text-ink-2">
                <Terminal className="h-3.5 w-3.5" />
                Pipeline Stream Logs ({logs.length})
              </span>
              <span className="font-mono text-[0.6875rem] text-ink-3">SSE text/event-stream</span>
            </div>
            <div
              ref={logContainerRef}
              className="max-h-48 overflow-y-auto p-3 font-mono text-xs leading-relaxed text-ink-2"
            >
              {logs.map((log) => (
                <div key={log.id} className="flex gap-2">
                  <span className="text-ink-3">[{log.timestamp}]</span>
                  <span className="font-semibold text-ink">[{log.step}]</span>
                  <span className="text-ink-2">{log.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Right Column: Submission & Configuration Surface */}
      <aside className="flex flex-col gap-5">
        {/* Mode Selector Tabs */}
        {status !== "running" && status !== "completed" && (
          <div className="grid grid-cols-2 border border-hairline bg-surface p-1 text-xs">
            <button
              type="button"
              onClick={() => {
                setMode("single");
                handleReset();
              }}
              className={`flex items-center justify-center gap-1.5 py-2 font-mono font-medium transition-colors ${
                mode === "single"
                  ? "bg-enamel text-white font-bold"
                  : "text-ink-2 hover:bg-paper"
              }`}
            >
              <GitBranch className="h-3.5 w-3.5" />
              Single Repo
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("system");
                handleReset();
              }}
              className={`flex items-center justify-center gap-1.5 py-2 font-mono font-medium transition-colors ${
                mode === "system"
                  ? "bg-enamel text-white font-bold"
                  : "text-ink-2 hover:bg-paper"
              }`}
            >
              <Network className="h-3.5 w-3.5" />
              Microservice Mesh
            </button>
          </div>
        )}

        {status === "completed" && result ? (
          /* Completion Card */
          <div className="border-2 border-line-cedar bg-surface p-5 shadow-sm">
            <div className="flex items-center gap-2 text-line-cedar">
              <Sparkles className="h-5 w-5" />
              <span className="label font-bold text-line-cedar tracking-wider uppercase">
                {result.system ? "Federated System Minted" : "Documentation Minted"}
              </span>
            </div>

            <h3 className="signage mt-2 text-[2rem] leading-none text-ink">
              {result.display_name || result.system || result.repo}
            </h3>

            <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink-2">
              {result.system
                ? `Synthesized federated system topology, cross-service interaction matrix, and peer links across ${result.services_count} microservices.`
                : "All 4 pages synthesized and vectorless PageIndex tree generated. Ready for reading and reasoning chat."}
            </p>

            {result.repos && result.repos.length > 0 && (
              <div className="mt-3 border-t border-hairline pt-3">
                <span className="label-wide text-ink-3">Member Service Wikis</span>
                <ul className="mt-1.5 flex flex-wrap gap-1.5">
                  {result.repos.map((r) => (
                    <li key={r}>
                      <Link
                        href={`/wiki/${r}/overview`}
                        className="inline-flex items-center gap-1 border border-hairline bg-paper px-2 py-0.5 font-mono text-[0.6875rem] text-ink hover:border-ink"
                      >
                        <span className="h-1.5 w-1.5 bg-line-cedar" />
                        {r}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-5 flex flex-col gap-2.5">
              <Link
                href={result.redirect}
                className="flex h-11 items-center justify-between bg-enamel px-4 font-mono text-xs font-semibold text-white transition-colors hover:bg-enamel-2"
              >
                <span className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4" />
                  {result.system ? "Open Federated System Wiki" : "Read Wiki"}
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>

              <Link
                href={`/chat?repo=${result.system || result.repo}`}
                className="flex h-11 items-center justify-between border border-ink bg-paper px-4 font-mono text-xs font-semibold text-ink transition-colors hover:bg-paper-2"
              >
                <span className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  {result.system ? "Reason Across Microservices" : "Ask AI with Tree Reasoning"}
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>

              <button
                type="button"
                onClick={handleReset}
                className="mt-2 flex items-center justify-center gap-1.5 py-1 text-center font-mono text-xs text-ink-3 hover:text-ink"
              >
                <RotateCcw className="h-3 w-3" />
                Document another project
              </button>
            </div>
          </div>
        ) : mode === "single" ? (
          /* Single Repo Form */
          <div className="border border-hairline bg-surface">
            <div className="border-b border-hairline px-4 py-2.5">
              <h2 className="label text-ink">Single Repository Ingestion</h2>
            </div>

            <div className="px-4 py-4">
              <label
                htmlFor="repo-url"
                className="label-wide mb-1.5 block text-ink-2"
              >
                Repository URL or local name
              </label>
              <input
                id="repo-url"
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={status === "running"}
                placeholder="https://github.com/org/service"
                className="h-10 w-full border border-hairline-strong bg-paper px-3 font-mono text-[0.8125rem] text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
              />

              {errorMessage && (
                <div className="mt-3 flex items-start gap-2 border border-fault/30 bg-fault/10 p-2 text-xs text-fault">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Quick Preset Buttons */}
              <div className="mt-4">
                <span className="label-wide mb-2 block text-ink-3">
                  Quick Presets
                </span>
                <div className="flex flex-col gap-1.5">
                  {SINGLE_PRESETS.map((p) => (
                    <button
                      key={p.value}
                      type="button"
                      disabled={status === "running"}
                      onClick={() => setUrl(p.value)}
                      className={`flex flex-col items-start border p-2 text-left transition-colors ${
                        url === p.value
                          ? "border-ink bg-paper-2 font-medium"
                          : "border-hairline bg-surface hover:bg-paper"
                      }`}
                    >
                      <span className="font-mono text-xs font-semibold text-ink">
                        {p.label}
                      </span>
                      <span className="text-[0.6875rem] text-ink-3">{p.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Action Button */}
              <button
                type="button"
                onClick={startIngestion}
                disabled={!url.trim() || status === "running"}
                className={`mt-5 flex h-11 w-full items-center justify-center gap-2 font-mono text-xs font-bold uppercase tracking-wider transition-colors ${
                  status === "running"
                    ? "cursor-not-allowed bg-paper-2 text-ink-3 border border-hairline"
                    : "bg-enamel text-white hover:bg-enamel-2"
                }`}
              >
                {status === "running" ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Ingesting Pipeline...
                  </>
                ) : (
                  <>
                    <ArrowRight className="h-4 w-4" />
                    Start Ingestion
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          /* Multi-Repo System Form */
          <div className="border border-hairline bg-surface">
            <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
              <h2 className="label text-ink">Multi-Repo System Mesh</h2>
              <button
                type="button"
                disabled={status === "running"}
                onClick={loadSystemPreset}
                className="font-mono text-[0.6875rem] text-enamel underline hover:text-enamel-2"
              >
                Load Demo Mesh
              </button>
            </div>

            <div className="px-4 py-4">
              <div className="grid gap-3">
                <div>
                  <label htmlFor="sys-slug" className="label-wide mb-1 block text-ink-2">
                    System Identifier (slug)
                  </label>
                  <input
                    id="sys-slug"
                    type="text"
                    value={systemName}
                    onChange={(e) => setSystemName(e.target.value)}
                    disabled={status === "running"}
                    placeholder="e.g. checkout-mesh"
                    className="h-9 w-full border border-hairline-strong bg-paper px-3 font-mono text-xs text-ink focus:border-ink focus:outline-none"
                  />
                </div>

                <div>
                  <label htmlFor="sys-title" className="label-wide mb-1 block text-ink-2">
                    System Display Title
                  </label>
                  <input
                    id="sys-title"
                    type="text"
                    value={systemDisplayName}
                    onChange={(e) => setSystemDisplayName(e.target.value)}
                    disabled={status === "running"}
                    placeholder="e.g. Checkout & Identity Mesh"
                    className="h-9 w-full border border-hairline-strong bg-paper px-3 font-mono text-xs text-ink focus:border-ink focus:outline-none"
                  />
                </div>
              </div>

              {/* Repositories List */}
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="label-wide text-ink-3">
                    Member Repositories ({systemRepos.length})
                  </span>
                  <button
                    type="button"
                    disabled={status === "running"}
                    onClick={addRepoRow}
                    className="inline-flex items-center gap-1 font-mono text-[0.6875rem] text-enamel hover:underline"
                  >
                    <Plus className="h-3 w-3" />
                    Add Repo
                  </button>
                </div>

                <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
                  {systemRepos.map((repo, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 border border-hairline bg-paper p-2 text-xs"
                    >
                      <div className="flex-1 grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={repo.name}
                          disabled={status === "running"}
                          onChange={(e) => updateRepoRow(idx, "name", e.target.value)}
                          placeholder="service-name"
                          className="h-7 w-full border border-hairline bg-surface px-2 font-mono text-[0.6875rem] text-ink focus:outline-none"
                        />
                        <input
                          type="text"
                          value={repo.url}
                          disabled={status === "running"}
                          onChange={(e) => updateRepoRow(idx, "url", e.target.value)}
                          placeholder="git-url or local"
                          className="h-7 w-full border border-hairline bg-surface px-2 font-mono text-[0.6875rem] text-ink focus:outline-none"
                        />
                      </div>
                      <button
                        type="button"
                        disabled={status === "running" || systemRepos.length <= 1}
                        onClick={() => removeRepoRow(idx)}
                        className="text-ink-3 hover:text-fault disabled:opacity-30"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {errorMessage && (
                <div className="mt-3 flex items-start gap-2 border border-fault/30 bg-fault/10 p-2 text-xs text-fault">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Action Button */}
              <button
                type="button"
                onClick={startIngestion}
                disabled={!systemName.trim() || systemRepos.length === 0 || status === "running"}
                className={`mt-5 flex h-11 w-full items-center justify-center gap-2 font-mono text-xs font-bold uppercase tracking-wider transition-colors ${
                  status === "running"
                    ? "cursor-not-allowed bg-paper-2 text-ink-3 border border-hairline"
                    : "bg-enamel text-white hover:bg-enamel-2"
                }`}
              >
                {status === "running" ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Synthesizing System Mesh...
                  </>
                ) : (
                  <>
                    <Network className="h-4 w-4" />
                    Ingest Microservice Mesh
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Informational Card */}
        <div className="border border-hairline bg-surface p-4">
          <h3 className="label text-ink">
            {mode === "system" ? "Department Multi-Repo Mesh" : "Autonomous Documentation"}
          </h3>
          <p className="mt-2 text-[0.875rem] leading-relaxed text-ink-2">
            {mode === "system"
              ? "Ingests multiple repositories into a unified system mesh. Traces synchronous RPCs, Kafka event topics, and generates cross-linked documentation."
              : "GoWiki strips code noise with Repomix, synthesizes standardized pages via LLM passes, and constructs vectorless hierarchical heading indices."}
          </p>
          <div className="mt-3 flex items-center gap-2 font-mono text-xs text-ink-3">
            <span className="h-2 w-2 bg-line-cedar" />
            <span>PageIndex cross-service reasoning</span>
          </div>
        </div>
      </aside>
    </div>
  );
}
