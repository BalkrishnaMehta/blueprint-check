"use client"

import { useEffect, useState, type FormEvent } from "react"

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

type Edge = { source: string; target: string; evidence: string }
type Report = {
  has_findings: boolean
  missing: Edge[]
  forbidden: Edge[]
  cycles: string[][]
  surprise_hub: { name: string; degree: number; evidence: string } | null
}
type Example = {
  id: string
  title: string
  detail: string
  repo: string
  claims: { components: string[]; edges: { from: string; to: string }[] }
}

export default function Page() {
  const [examples, setExamples] = useState<Example[]>([])
  const [selected, setSelected] = useState("sample")
  const [provider, setProvider] = useState("auto")
  const [file, setFile] = useState<File | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const example = examples.find((item) => item.id === selected) || examples[0]

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${API}/v1/examples`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Examples returned ${response.status}`)
        return response.json()
      })
      .then((payload: Example[]) => {
        setExamples(payload)
        setError("")
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return
        setError(`The API at ${API} did not respond.`)
      })
    return () => controller.abort()
  }, [])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!example) return
    setBusy(true)
    setError("")
    const body = new FormData()
    body.set("provider", provider)
    body.set("repo", example.repo)
    try {
      if (file) body.set("image", file)
      else body.set("claims", JSON.stringify(example.claims))
      const response = await fetch(`${API}/v1/checks`, { method: "POST", body })
      const text = await response.text()
      let payload: { detail?: string } = {}
      if (text) {
        try {
          payload = JSON.parse(text)
        } catch {
          throw new Error(text.slice(0, 180))
        }
      }
      if (!response.ok) {
        setReport(null)
        setError(explain(typeof payload.detail === "string" ? payload.detail : "Check failed"))
        return
      }
      setReport(payload as Report)
    } catch (err) {
      setReport(null)
      setError(explain(err instanceof Error ? err.message : `The API at ${API} did not respond.`))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main>
      <header>
        <p className="kicker">Graphify graph, checked against a diagram</p>
        <h1>Blueprint</h1>
        <p className="lede">
          Pick a codebase. The claims are the diagram. A missing arrow was drawn and never imported. A forbidden arrow was imported and never drawn.
        </p>
      </header>
      <form onSubmit={onSubmit}>
        <div className="tracks" role="group" aria-label="Codebases">
          {examples.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={item.id === example?.id}
              onClick={() => {
                setSelected(item.id)
                setFile(null)
                setReport(null)
                setError("")
              }}
            >
              <strong>{item.title}</strong>
              <span>{item.detail}</span>
            </button>
          ))}
        </div>
        {example?.id === "sample" ? (
          <img src={`${API}/v1/sample/diagram`} alt="Drawn diagram: billing points at auth and payments. Payments and notifications point at each other." />
        ) : null}
        <div className="controls">
          <label>
            Diagram image
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <label>
            Vision
            <select value={provider} onChange={(event) => setProvider(event.target.value)}>
              <option value="auto">Auto</option>
              <option value="gemini">Gemma 4 on Gemini</option>
              <option value="ollama">Local Ollama</option>
              <option value="vllm">vLLM</option>
              <option value="sglang">SGLang</option>
              <option value="hosted">Hosted Gemma</option>
            </select>
          </label>
          <button type="submit" disabled={busy || !example}>
            {busy ? "Checking" : file ? "Check this image" : "Check claims"}
          </button>
        </div>
        <p className="hint">
          {file
            ? `${file.name} goes to ${provider === "gemini" ? "Gemma on Gemini" : provider === "hosted" ? "the host in VISION_BASE_URL" : "the local vision server"}.`
            : "No image attached, so this check does not call a model."}
        </p>
      </form>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {report ? <ReportView report={report} /> : null}
    </main>
  )
}

function explain(detail: string) {
  return detail
    .replace("Re-run with --claims for the offline check.", "Leave the image empty and check the claims instead.")
    .replace("or re-run with --claims for the offline check.", "or leave the image empty and check the claims instead.")
}

function ReportView({ report }: { report: Report }) {
  const hub = report.surprise_hub
  const clear = [
    report.missing.length ? "" : "missing",
    report.forbidden.length ? "" : "forbidden",
    report.cycles.length ? "" : "cycle",
    hub ? "" : "surprise hub",
  ].filter(Boolean)
  return (
    <section className="report" aria-live="polite">
      <p className={report.has_findings ? "verdict drift" : "verdict match"}>
        {report.has_findings ? "The diagram and the code disagree" : "The diagram matches the code"}
      </p>
      <div className="findings">
        <Finding title="Missing" body={edgeText(report.missing)} />
        <Finding title="Forbidden" body={edgeText(report.forbidden)} />
        <Finding title="Cycle" body={report.cycles.map((cycle) => [...cycle, cycle[0]].join(" -> ")).join("\n")} />
        <Finding
          title="Surprise hub"
          body={hub ? `${hub.name}, ${hub.degree} inbound\n${hub.evidence}` : ""}
        />
      </div>
      {clear.length ? <p className="hint">Clear: {clear.join(", ")}</p> : null}
    </section>
  )
}

function edgeText(edges: Edge[]) {
  return edges.map((edge) => `${edge.source} -> ${edge.target}\n${edge.evidence}`).join("\n\n")
}

function Finding({ title, body }: { title: string; body: string }) {
  if (!body) return null
  return (
    <div className="finding">
      <h2>{title}</h2>
      <pre>{body}</pre>
    </div>
  )
}
