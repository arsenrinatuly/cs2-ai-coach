"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

const api = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "1";
const maxBytes = 512 * 1024 * 1024;

type Evidence = { round_number: number; event_ordinal: number; tick: number };
type Player = {
  steamid: string;
  name: string | null;
  kills: number;
  deaths: number;
  assists: number;
  rounds_with_death_event_participation: number[];
  opening_deaths: Evidence[];
};
type Analytics = {
  match_id: string;
  map_name: string | null;
  round_count: number;
  players: Player[];
};
type Report = {
  source: "deterministic" | "model";
  observations: {
    observation: string;
    evidence: Evidence;
    suggested_review_action: string;
    uncertainty: string;
  }[];
};
type MatchStatus = { status: "queued" | "ready" | "failed"; error: string | null };
type View = { phase: "idle" | "uploading" | "processing" | "ready" | "error"; message: string };

async function get<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(api + path, { signal, cache: "no-store" });
  if (!response.ok) throw new Error("Could not retrieve match data. Check the API and try again.");
  return response.json();
}

function upload(file: File, signal: AbortSignal, progress: (value: number) => void): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", api + "/matches?filename=" + encodeURIComponent(file.name));
    xhr.timeout = 180_000;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) progress(Math.floor(event.loaded * 100 / event.total));
    };
    const cancel = () => xhr.abort();
    signal.addEventListener("abort", cancel, { once: true });
    xhr.onloadend = () => signal.removeEventListener("abort", cancel);
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    xhr.onerror = () => reject(new Error("Could not connect to the API."));
    xhr.ontimeout = () => reject(new Error("Upload timed out. Try again."));
    xhr.onload = () => {
      try {
        const response = JSON.parse(xhr.responseText);
        if (xhr.status === 202 && typeof response.status_url === "string") {
          resolve(response.status_url);
        } else {
          reject(new Error(typeof response.detail === "string" ? response.detail : "Upload failed."));
        }
      } catch {
        reject(new Error("The API returned an unreadable response."));
      }
    };
    xhr.send(file);
  });
}

function pause(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    signal.throwIfAborted();
    const timer = window.setTimeout(() => {
      signal.removeEventListener("abort", cancel);
      resolve();
    }, 1200);
    function cancel() {
      window.clearTimeout(timer);
      reject(signal.reason);
    }
    signal.addEventListener("abort", cancel, { once: true });
  });
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [view, setView] = useState<View>({ phase: "idle", message: "" });
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<Analytics | null>(null);
  const [selected, setSelected] = useState("");
  const [demoReports, setDemoReports] = useState<Record<string, Report>>({});
  const [report, setReport] = useState<Report | null>(null);
  const [coachStatus, setCoachStatus] = useState("");
  const coachRequest = useRef<AbortController | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => {
    active.current?.abort();
    coachRequest.current?.abort();
  }, []);

  function resetCoach() {
    coachRequest.current?.abort();
    setReport(null);
    setCoachStatus("");
  }
  const player = result?.players.find((item) => item.steamid === selected);
  const busy = view.phase === "uploading" || view.phase === "processing";

  async function loadSample() {
    setView({ phase: "processing", message: "Loading the sample match…" });
    try {
      const response = await fetch("/demo-sample.json");
      if (!response.ok) throw new Error("The sample match is unavailable.");
      const sample: { analytics: Analytics; reports: Record<string, Report> } = await response.json();
      setDemoReports(sample.reports);
      setResult(sample.analytics);
      setSelected(sample.analytics.players[0]?.steamid ?? "");
      setView({ phase: "ready", message: "Sample match ready for review." });
    } catch (error) {
      setView({ phase: "error", message: error instanceof Error ? error.message : "Could not load the sample." });
    }
  }

  async function requestCoach() {
    if (!result || !player) return;
    resetCoach();
    if (demoMode) {
      setReport(demoReports[player.steamid] ?? null);
      return;
    }
    const controller = new AbortController();
    coachRequest.current = controller;
    setCoachStatus("Preparing review notes…");
    try {
      const response = await fetch(
        api + "/matches/" + result.match_id + "/players/" + player.steamid + "/coach",
        { method: "POST", signal: controller.signal },
      );
      if (!response.ok) throw new Error("Review notes are temporarily unavailable.");
      const nextReport: Report = await response.json();
      controller.signal.throwIfAborted();
      setReport(nextReport);
      setCoachStatus("");
    } catch (error) {
      if (!controller.signal.aborted) {
        setCoachStatus(error instanceof Error ? error.message : "Could not prepare review notes.");
      }
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    active.current?.abort();
    resetCoach();
    setResult(null);
    setSelected("");
    if (!file || !file.name.toLowerCase().endsWith(".dem")) {
      setView({ phase: "error", message: "Choose an extracted CS2 .dem file." });
      return;
    }
    if (file.size > maxBytes) {
      setView({ phase: "error", message: "The recording exceeds 512 MiB." });
      return;
    }
    const controller = new AbortController();
    active.current = controller;
    const { signal } = controller;
    setProgress(0);
    setView({ phase: "uploading", message: "Uploading recording…" });
    try {
      const path = await upload(file, signal, setProgress);
      setView({ phase: "processing", message: "Reading rounds and recorded events…" });
      for (let attempt = 0; attempt < 150; attempt++) {
        const status = await get<MatchStatus>(path, signal);
        if (status.status === "failed") throw new Error(status.error ?? "Demo processing failed.");
        if (status.status === "ready") {
          const analytics = await get<Analytics>(path + "/analytics", signal);
          signal.throwIfAborted();
          setResult(analytics);
          setSelected(analytics.players[0]?.steamid ?? "");
          setView({ phase: "ready", message: "Match ready for review." });
          return;
        }
        await pause(signal);
      }
      throw new Error("Processing is taking longer than expected. Submit the same file to check again.");
    } catch (error) {
      if (!signal.aborted) {
        setView({ phase: "error", message: error instanceof Error ? error.message : "Analysis failed." });
      }
    }
  }

  return (
    <main>
      <header><span className="mark" aria-hidden="true">CS</span><span>CS2 AI Coach</span></header>
      <section className="intro">
        <h1>Review a match</h1>
        <p>{demoMode ? "Explore an anonymized Valve match with recorded statistics and evidence." : "Upload a CS2 demo to inspect player statistics and opening deaths."}</p>
      </section>
      {demoMode ? <section className="panel upload">
        <button type="button" disabled={busy || result !== null} onClick={loadSample}>Open sample match</button>
        {view.message && <p role="status">{view.message}</p>}
      </section> : <form className="panel upload" onSubmit={submit}>
        <div>
          <label htmlFor="demo">Match recording</label>
          <input id="demo" type="file" accept=".dem" disabled={busy} onChange={(event) => {
            resetCoach();
            setFile(event.target.files?.[0] ?? null);
            setResult(null);
            setView({ phase: "idle", message: "" });
          }} />
          <small>Source 2 .dem · Up to 512 MiB</small>
        </div>
        <button disabled={!file || busy} type="submit">Analyze demo</button>
        {view.phase === "uploading" && <progress max={100} value={progress} aria-label="Upload progress" />}
        {view.message && <p className={view.phase === "error" ? "error" : "status"} role={view.phase === "error" ? "alert" : "status"}>{view.message}</p>}
      </form>}

      {result && <section className="results" aria-labelledby="match-title">
        <div className="match">
          <div><h2 id="match-title">{result.map_name ?? "Unknown map"}</h2><p>{result.round_count} recorded rounds</p></div>
          {result.players.length > 0 && <div><label htmlFor="player">Player</label>
            <select id="player" value={selected} onChange={(event) => { resetCoach(); setSelected(event.target.value); }}>
              {result.players.map((item) => <option key={item.steamid} value={item.steamid}>{item.name ?? item.steamid}</option>)}
            </select>
          </div>}
        </div>
        {!player && <p>No identified players were recorded.</p>}
        {player && <>
          <dl className="metrics">
            <div className="panel"><dt>Kills</dt><dd>{player.kills}</dd></div>
            <div className="panel"><dt>Deaths</dt><dd>{player.deaths}</dd></div>
            <div className="panel"><dt>Recorded assists</dt><dd>{player.assists}</dd></div>
            <div className="panel"><dt>Rounds with event involvement</dt><dd>{player.rounds_with_death_event_participation.length}</dd></div>
          </dl>
          <section className="panel evidence">
            <h3>Opening deaths</h3>
            {player.opening_deaths.length === 0 ? <p>No opening deaths attributed to this player.</p> :
              <ul>{player.opening_deaths.map((item) => <li key={item.event_ordinal}>
                <details>
                  <summary>Round {item.round_number}</summary>
                  <p>Recorded first death · Tick {item.tick} · Event #{item.event_ordinal}</p>
                </details>
              </li>)}</ul>}
          </section>
          <section className="panel coach">
            <div className="match">
              <h3>Review notes</h3>
              <button type="button" onClick={requestCoach}>Prepare review notes</button>
            </div>
            {coachStatus && <p role="status">{coachStatus}</p>}
            {report && (report.observations.length === 0
              ? <p>There is no opening-death evidence for this player.</p>
              : <>
                <p>{report.source === "model" ? "Model-selected review points" : "Rule-based review points"}</p>
                <ul>{report.observations.map((item) => <li key={item.evidence.event_ordinal}>
                  <strong>{item.observation}</strong>
                  <p>{item.suggested_review_action}</p>
                  <small>Tick {item.evidence.tick} · {item.uncertainty}</small>
                </li>)}</ul>
              </>)}
          </section>
        </>}
      </section>}
    </main>
  );
}
