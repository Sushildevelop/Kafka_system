"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowUpRight, BrainCircuit, Check, Edit3, MessageCircleMore, MoreHorizontal, Plus, Search, Trash2, Users, X, Sparkles } from "lucide-react";
import { api, getUser, logout, type AuthUser } from "@/lib/auth";

type Group={group_id:string;name:string;owner_id:string;member_ids:string[];created_at:string;updated_at:string};
const accents=["cyan","violet","pink","green"];

export default function StudyGroups(){
  const [user,setUser]=useState<AuthUser|null>(null),[groups,setGroups]=useState<Group[]>([]),[name,setName]=useState(""),[editing,setEditing]=useState<Group|null>(null),[editName,setEditName]=useState(""),[memberId,setMemberId]=useState(""),[menu,setMenu]=useState(""),[search,setSearch]=useState(""),[loading,setLoading]=useState(false),[error,setError]=useState("");

  async function loadGroups(id:string){
    try{const r=await api.fetch("/study-groups?user_id="+encodeURIComponent(id));if(r.ok)setGroups(await r.json());else setError("Could not load your study groups.");}
    catch{setError("Could not connect to Study AI.");}
  }
  useEffect(()=>{const u=getUser();if(!u){location.href="/login";return}setUser(u);loadGroups(u.user_id)},[]);

  async function createGroup(){
    const n=name.trim();if(!user||!n||loading)return;setLoading(true);setError("");
    try{
      const r=await api.fetch("/study-groups",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:n,owner_id:user.user_id,member_ids:[user.user_id]})});
      if(!r.ok){
        let detail="";
        try{const body=await r.json();detail=typeof body?.detail==="string"?body.detail:body?.detail?JSON.stringify(body.detail):"";}catch{}
        throw new Error("Could not create the group ("+r.status+"): "+(detail||"The API returned an error."));
      }
      const created:Group=await r.json();setGroups(v=>[created,...v]);setName("");
    }catch(e){setError(e instanceof Error?e.message:"Could not create the group.");}finally{setLoading(false)}
  }
  function startEdit(g:Group){setEditing(g);setEditName(g.name);setMenu("")}
  async function saveEdit(){
    if(!user||!editing||!editName.trim()||loading)return;setLoading(true);setError("");
    try{const r=await api.fetch("/study-groups/"+editing.group_id+"?user_id="+encodeURIComponent(user.user_id),{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:editName.trim()})});
      if(!r.ok)throw new Error(r.status===403?"Only the group owner can edit this group.":"Could not update the group.");const updated:Group=await r.json();setGroups(v=>v.map(g=>g.group_id===updated.group_id?updated:g));setEditing(null);
    }catch(e){setError(e instanceof Error?e.message:"Could not update the group.");}finally{setLoading(false)}
  }
  async function addMember(){
    if(!user||!editing||!memberId.trim()||loading)return;setLoading(true);setError("");
    try{const r=await api.fetch("/study-groups/"+editing.group_id+"/members?user_id="+encodeURIComponent(user.user_id),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_id:memberId.trim()})});
      if(!r.ok)throw new Error(r.status===403?"Only the group owner can add members.":"Could not add the member.");const updated:Group=await r.json();setGroups(v=>v.map(g=>g.group_id===updated.group_id?updated:g));setEditing(updated);setMemberId("");
    }catch(e){setError(e instanceof Error?e.message:"Could not add the member.");}finally{setLoading(false)}
  }
  async function removeMember(member:string){
    if(!user||!editing||loading)return;setLoading(true);setError("");
    try{const r=await api.fetch("/study-groups/"+editing.group_id+"/members/"+encodeURIComponent(member)+"?user_id="+encodeURIComponent(user.user_id),{method:"DELETE"});
      if(!r.ok)throw new Error(r.status===403?"Only the owner can remove another member.":"Could not remove the member.");const updated:Group=await r.json();setGroups(v=>v.map(g=>g.group_id===updated.group_id?updated:g));setEditing(updated);
    }catch(e){setError(e instanceof Error?e.message:"Could not remove the member.");}finally{setLoading(false)}
  }
  async function deleteGroup(g:Group){
    if(!user||g.owner_id!==user.user_id||loading)return;if(!confirm("Delete “"+g.name+"”? This removes the group."))return;
    setLoading(true);setError("");
    try{const r=await api.fetch("/study-groups/"+g.group_id+"?user_id="+encodeURIComponent(user.user_id),{method:"DELETE"});
      if(!r.ok)throw new Error(r.status===403?"Only the group owner can delete this group.":"Could not delete the group.");setGroups(v=>v.filter(x=>x.group_id!==g.group_id));setMenu("");
    }catch(e){setError(e instanceof Error?e.message:"Could not delete the group.");}finally{setLoading(false)}
  }
  const visible=useMemo(()=>groups.filter(g=>g.name.toLowerCase().includes(search.trim().toLowerCase())),[groups,search]);

  return <main className="groups-page"><div className="grid-bg groups-bg"/>
    <header className="groups-header"><Link href="/" className="brand">Study<span>AI</span><b>.</b></Link>
      <div className="groups-header-actions"><Link href="/account" className="header-link">Account</Link><div className="profile-chip"><div className="avatar-fallback">{user?.name?.[0]?.toUpperCase()??"S"}</div><span>{user?.name??"Study AI Student"}</span></div><button className="header-link" onClick={()=>{logout();location.href="/login"}}>Logout</button></div>
    </header>
    <section className="groups-shell">
      <div className="groups-hero"><div><div className="eyebrow"><Sparkles size={13}/> STUDY AI · COLLABORATION OS</div><h1>Study better.<br/><span>Together.</span></h1><p>Build focused rooms for your courses, projects and exam preparation. Every group comes with live chat and an AI study companion.</p></div><div className="workspace-orb"><BrainCircuit size={42}/><span>{groups.length} active spaces</span></div></div>
      <div className="group-stat-row"><div className="mini-stat glass"><b>{groups.length}</b><span>Study spaces</span></div><div className="mini-stat glass"><b>{groups.reduce((n,g)=>n+g.member_ids.length,0)}</b><span>Member seats</span></div><div className="mini-stat glass"><b>AI</b><span>Learning companion</span></div></div>
      <div className="groups-controls"><div className="groups-search glass"><Search size={17}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search study spaces…"/>{search&&<button onClick={()=>setSearch("")}><X size={15}/></button>}</div><div className="create-inline glass"><input value={name} onChange={e=>setName(e.target.value)} onKeyDown={e=>e.key==="Enter"&&createGroup()} placeholder="Name a new study group…"/><button onClick={createGroup} disabled={!name.trim()||loading}><Plus size={17}/><span>{loading?"Creating…":"Create group"}</span></button></div></div>
      {error&&<div className="group-error glass">{error}<button onClick={()=>setError("")}><X size={15}/></button></div>}
      {visible.length===0?<div className="empty-state glass"><BrainCircuit size={32}/><h2>{groups.length?"No matching spaces":"Your study workspace is empty"}</h2><p>{groups.length?"Try another search.":"Create your first study group and bring your learning team together."}</p></div>:
      <div className="groups-grid">{visible.map((g,i)=><motion.article key={g.group_id} whileHover={{y:-6}} className={"group-card group-card-"+accents[i%accents.length]+" glass"}>
        <div className="group-card-top"><div className="group-icon"><MessageCircleMore size={21}/></div><div className="group-menu-wrap"><button className="icon-button" onClick={()=>setMenu(menu===g.group_id?"":g.group_id)}><MoreHorizontal size={18}/></button>{menu===g.group_id&&<div className="group-menu"><button onClick={()=>startEdit(g)}><Edit3 size={15}/> Edit group</button>{g.owner_id===user?.user_id&&<button className="danger" onClick={()=>deleteGroup(g)}><Trash2 size={15}/> Delete group</button>}</div>}</div></div>
        <Link href={"/study-groups/"+g.group_id}><div className="group-live"><i/> LIVE STUDY ROOM</div><h2>{g.name}</h2><p>Focused collaboration, shared resources, persistent discussion and AI-assisted learning.</p></Link>
        <div className="group-card-footer"><span><Users size={14}/> {g.member_ids.length} members</span><Link href={"/study-groups/"+g.group_id}><span>Open room <ArrowUpRight size={15}/></span></Link></div>
      </motion.article>)}</div>}
      {editing&&<div className="modal-backdrop" onMouseDown={e=>e.currentTarget===e.target&&setEditing(null)}><motion.div initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} className="edit-modal glass"><div className="modal-head"><div><span className="eyebrow">GROUP SETTINGS</span><h2>Edit study group</h2></div><button onClick={()=>setEditing(null)}><X size={18}/></button></div><label>Group name<input autoFocus value={editName} onChange={e=>setEditName(e.target.value)} onKeyDown={e=>e.key==="Enter"&&saveEdit()}/></label><div className="member-manager"><div className="member-manager-head"><b>Members</b><span>{editing.member_ids.length} total</span></div><div className="member-list">{editing.member_ids.map((member,i)=><div className="member-row" key={member}><span><i>{(member===user?.user_id?"You":member).slice(0,1).toUpperCase()}</i>{member===user?.user_id?"You":member}</span>{member!==editing.owner_id&&<button onClick={()=>removeMember(member)}><Trash2 size={13}/></button>}</div>)}</div><div className="add-member-row"><input value={memberId} onChange={e=>setMemberId(e.target.value)} onKeyDown={e=>e.key==="Enter"&&addMember()} placeholder="User ID to add…"/><button onClick={addMember} disabled={!memberId.trim()||loading}>Add</button></div></div><div className="modal-actions"><button className="secondary-button" onClick={()=>setEditing(null)}>Cancel</button><button className="primary-action" onClick={saveEdit} disabled={!editName.trim()||loading}><Check size={17}/> Save changes</button></div></motion.div></div>}
    </section>
  </main>
}