import { useState } from "react";
import { learn, type Project } from "../api/learn";
import { useLoad } from "../hooks";
import { Button, Badge } from "../components/ui";
import { ErrorBox, Empty, Loading } from "../components/States";

function ProjectCard({ project, refresh }: { project: Project; refresh: () => void }) {
  const [text,setText]=useState(project.submission_text ?? "");
  const [url,setUrl]=useState(project.submission_url ?? "");
  const [scores,setScores]=useState<Record<string,number>>(project.reflection_scores ?? {});
  const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  const act=async(fn:()=>Promise<unknown>)=>{setBusy(true);setError("");try{await fn();refresh();}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  return <article className="card"><div className="page-head"><div><Badge>{project.level}</Badge><h2>{project.title}</h2><p className="muted">{project.subject_title}</p></div><Badge>{project.status.replaceAll("_"," ")}</Badge></div>
    <p>{project.objective}</p><p className="muted">Skills: {project.skills.join(", ")}</p><h3>Milestones</h3>
    {project.milestones.map((m,i)=><label className="option" key={i}><input type="checkbox" checked={project.milestones_done.includes(i)} disabled={busy} onChange={e=>act(()=>learn.milestone(project.id,i,e.target.checked))}/><span>{m}</span></label>)}
    <p><strong>Deliverables:</strong> {project.deliverables}</p>
    <form onSubmit={e=>{e.preventDefault();act(()=>learn.submitProject(project.id,{text,url:url || undefined,rubric_scores:Object.fromEntries(project.rubric.map(c=>[c,scores[c]??0]))}));}}>
      <label className="field">Your work and reflection<textarea required minLength={80} rows={5} value={text} onChange={e=>setText(e.target.value)} placeholder="Explain your approach, results, and what you learned…"/></label>
      <label className="field">Evidence link (optional)<input type="url" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://…"/></label>
      <h3>Self-assessment</h3><p className="muted small">Evidence is saved to your portfolio. This is a self-review, not an independently verified grade.</p>
      {project.rubric.map((criterion,i)=><label className="field" key={i}>{criterion}<select value={scores[criterion] ?? 0} onChange={e=>setScores({...scores,[criterion]:Number(e.target.value)})}>{[0,1,2,3].map(n=><option key={n} value={n}>{n} / 3</option>)}</select></label>)}
      {error && <ErrorBox message={error}/>}<Button type="submit" loading={busy}>Save project submission</Button>
      {project.evaluation_note && <p className="sticky-note">{project.evaluation_note}</p>}
    </form></article>;
}
export default function ProjectsPage(){const {data,error,loading,reload}=useLoad(learn.projects);const [subject,setSubject]=useState("");if(loading)return <Loading/>;if(error||!data)return <ErrorBox message={error??"Projects unavailable"} onRetry={reload}/>;
return <div className="page"><header className="page-head"><div><h1>Build your skill portfolio</h1><p className="muted">Practical projects from Basic to Extreme, with milestones and saved evidence.</p></div><select aria-label="Filter projects by subject" value={subject} onChange={e=>setSubject(e.target.value)}><option value="">All subjects</option>{Array.from(new Set(data.projects.map(p=>p.subject_title))).map(s=><option key={s}>{s}</option>)}</select></header>{data.projects.length===0&&<Empty title="No projects available"/>}<div className="grid-2">{data.projects.filter(p=>!subject||p.subject_title===subject).map(p=><ProjectCard key={p.id} project={p} refresh={reload}/>)}</div></div>}
