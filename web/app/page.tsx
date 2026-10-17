"use client"

import { useState, type FormEvent } from "react"

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

type Edge = { source: string; target: string; evidence: string }
type Report = {
  has_findings: boolean
  missing: Edge[]
  forbidden: Edge[]
  cycles: string[][]
  surprise_hub: { name: string; degree: number; evidence: string } | null
}

export default function Page() {
  const [provider, setProvider] = useState("auto")
  const [file, setFile] = useState<File | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError("")
    const body = new FormData()
    body.set("provider", provider)
    if (file) body.set("image", file)
    else body.set("claims", await fetch(`${API}/v1/sample/claims`).then((response) => response.text()))
    const response = await fetch(`${API}/v1/checks`, { method: "POST", body })
    const payload = await response.json()
    setBusy(false)
    if (!response.ok) {
      setReport(null)
      setError(payload.detail || "Check failed")
      return
    }
    setReport(payload)
  }

  return (
    <main>
      <header>
        <h1>Blueprint</h1>
        <p>
          The diagram is the claim. Graphify is the code. Gemma reads the picture, and this page shows the arrows that are missing, forbidden, cyclic, or sitting on a module the diagram forgot.
        </p>
      </header>
      <form onSubmit={onSubmit}>
        <div className="controls">
          <img src={`${API}/v1/sample/diagram`} alt="Sample architecture diagram" />
          <div>
            <label>
              Diagram image
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => setFile(event.target.files?.[0] || null)} />
            </label>
            <label>
              Vision provider
              <select value={provider} onChange={(event) => setProvider(event.target.value)}>
                <option value="auto">Auto</option>
                <option value="gemini">Gemma 4 on Gemini</option>
                <option value="ollama">Ollama</option>
                <option value="vllm">vLLM</option>
                <option value="sglang">SGLang</option>
              </select>
            </label>
            <button type="submit" disabled={busy}>{busy ? "Checking" : file ? "Check this image" : "Check the sample claims"}</button>
            <p>Leave the file empty to run the committed sample, which needs no model.</p>
          </div>
        </div>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {report ? <ReportView report={report} /> : null}
    </main>
  )
}

function ReportView({ report }: { report: Report }) {
  const hub = report.surprise_hub
    ? `${report.surprise_hub.name} (${report.surprise_hub.degree} inbound)\n${report.surprise_hub.evidence}`
    : "None"
  return (
    <section className="report">
      <div className="columns">
        <Card title="Missing" body={lines(report.missing)} />
        <Card title="Forbidden" body={lines(report.forbidden)} />
        <Card title="Cycle" body={report.cycles.map((cycle) => [...cycle, cycle[0]].join(" -> ")).join("\n") || "None"} />
        <Card title="Surprise hub" body={hub} />
      </div>
    </section>
  )
}

function lines(edges: Edge[]) {
  if (!edges.length) return "None"
  return edges.map((edge) => `${edge.source} -> ${edge.target}\n  ${edge.evidence}`).join("\n")
}

function Card({ title, body }: { title: string; body: string }) {
  return (
    <article>
      <h2>{title}</h2>
      <pre>{body}</pre>
    </article>
  )
}
