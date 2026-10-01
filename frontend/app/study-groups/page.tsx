"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowUpRight, MessageCircleMore, Plus, Search, Users } from "lucide-react";
import { api, getUser, logout, type AuthUser } from "@/lib/auth";

type Group = {
  group_id: string;
  name: string;
  owner_id: string;
  member_ids: string[];
  created_at: string;
  updated_at: string;
};

export default function StudyGroups() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [name, setName] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const currentUser = getUser();
    if (!currentUser) {
      window.location.href = "/login";
      return;
    }
    setUser(currentUser);

    api.fetch(`/study-groups?user_id=${encodeURIComponent(currentUser.user_id)}`)
      .then(async (response) => (response.ok ? response.json() : []))
      .then(setGroups)
      .catch(() => setGroups([]));
  }, []);

  async function createGroup() {
    const trimmedName = name.trim();
    if (!user || !trimmedName || loading) return;

    setLoading(true);
    try {
      const response = await api.fetch("/study-groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedName,
          owner_id: user.user_id,
          member_ids: [user.user_id],
        }),
      });

      if (!response.ok) return;

      const createdGroup: Group = await response.json();
      setGroups((current) => [createdGroup, ...current]);
      setName("");
      setOpen(false);
    } finally {
      setLoading(false);
    }
  }

  const visibleGroups = groups.filter((group) =>
    group.name.toLowerCase().includes(search.trim().toLowerCase())
  );

  return (
    <main className="groups-page">
      <div className="grid-bg groups-bg" />
      <header className="groups-header">
        <Link href="/" className="brand">Study<span>AI</span><b>.</b></Link>

        <div className="groups-header-actions">
          <div className="profile-chip">
            <div className="avatar-fallback">{user?.name?.slice(0, 1).toUpperCase() ?? "S"}</div>
            <span>{user?.name ?? "Study AI Student"}</span>
          </div>
          <Link href="/account" className="header-link">Account</Link>
          <button className="header-link logout-button" onClick={() => { logout(); window.location.href = "/login"; }}>Logout</button>
        </div>
      </header>

      <section className="groups-shell">
        <div className="groups-toolbar">
          <div>
            <div className="eyebrow">STUDY AI · WORKSPACE</div>
            <h1>Your study groups</h1>
            <p>Create or join focused spaces for learning, discussion, resources, and AI assistance.</p>
          </div>
          <button className="primary-action" onClick={() => setOpen((value) => !value)}>
            <Plus size={18} /> New group
          </button>
        </div>

        {open && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="create-group glass">
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && createGroup()}
              placeholder="e.g. Quantum Computing — Evening"
            />
            <button disabled={loading} onClick={createGroup}>{loading ? "Creating…" : "Create group"}</button>
          </motion.div>
        )}

        <div className="groups-search glass">
          <Search size={17} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search your study groups…" />
        </div>

        {visibleGroups.length === 0 ? (
          <div className="empty-state glass">
            <MessageCircleMore size={28} />
            <h2>{groups.length ? "No matching groups" : "No study groups yet"}</h2>
            <p>{groups.length ? "Try a different search term." : "Create your first group and start studying together."}</p>
          </div>
        ) : (
          <div className="groups-grid">
            {visibleGroups.map((group) => (
              <Link href={`/study-groups/${group.group_id}`} key={group.group_id}>
                <motion.article whileHover={{ y: -5 }} className="group-card glass">
                  <div className="group-card-top">
                    <div className="group-icon"><MessageCircleMore size={21} /></div>
                    <ArrowUpRight size={18} />
                  </div>
                  <h2>{group.name}</h2>
                  <p>Live study room for focused collaboration and shared learning.</p>
                  <div className="group-meta">
                    <span><Users size={14} /> {group.member_ids.length} members</span>
                    <span>Live</span>
                  </div>
                </motion.article>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
