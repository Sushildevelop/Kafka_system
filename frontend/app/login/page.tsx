"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Chrome, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { demoLogin } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();

  function handleLogin() {
    demoLogin();
    router.push("/study-groups");
  }

  return (
    <main className="auth-page">
      <div className="grid-bg auth-bg" />
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="glass auth-shell">
        <section className="auth-story">
          <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Study AI</Link>
          <div className="auth-kicker"><Sparkles size={15} /> STUDY AI</div>
          <h1>Study together.<br /><span>Learn smarter.</span></h1>
          <p>Join a focused study workspace where your group, shared resources, and AI study companion work together.</p>
          <div className="auth-benefits">
            {["Real-time group conversations", "Files, images and video sharing", "AI-powered study assistance"].map((item) => (
              <div key={item}><CheckCircle2 size={17} />{item}</div>
            ))}
          </div>
        </section>

        <section className="auth-panel">
          <div className="auth-logo"><Chrome size={32} /></div>
          <div className="auth-panel-title">Welcome to Study AI</div>
          <p className="auth-panel-copy">Continue to your study workspace.</p>

          <button type="button" className="google-demo-button" onClick={handleLogin}>
            <span className="google-mark">G</span>
            <span>Continue with Google</span>
            <span className="google-arrow">→</span>
          </button>

          <p className="demo-note">Demo mode · clicking Continue with Google enters the study workspace.</p>
        </section>
      </motion.div>
    </main>
  );
}
