"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Chrome, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { demoLogin } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();

  function handleDemoLogin() {
    demoLogin();
    router.push("/study-groups");
  }

  return (
    <main className="auth-page">
      <div className="grid-bg auth-bg" />
      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.45 }}
        className="glass auth-shell"
      >
        <section className="auth-story">
          <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Study AI</Link>
          <div className="auth-kicker"><Sparkles size={15} /> STUDY AI</div>
          <h1>Study together.<br /><span>Learn smarter.</span></h1>
          <p>
            Enter your collaborative study space, talk with your group, share resources,
            and bring AI into the conversation.
          </p>
          <div className="auth-benefits">
            {[
              "Real-time group conversations",
              "Files, images and video sharing",
              "AI-powered study assistance",
            ].map((item) => (
              <div key={item}><CheckCircle2 size={17} />{item}</div>
            ))}
          </div>
        </section>

        <section className="auth-panel">
          <div className="auth-logo"><Chrome size={34} /></div>
          <div className="auth-panel-title">Welcome to Study AI</div>
          <p className="auth-panel-copy">Continue to your study workspace.</p>

          <button type="button" className="google-demo-button" onClick={handleDemoLogin}>
            <span className="google-mark">G</span>
            <span>Continue with Google</span>
            <span className="google-arrow">→</span>
          </button>

          <div className="auth-divider"><span>or</span></div>
          <button type="button" className="guest-button" onClick={handleDemoLogin}>
            Enter study workspace
          </button>

          <p className="demo-note">Demo mode · Google authentication is bypassed for this frontend prototype.</p>
        </section>
      </motion.div>
    </main>
  );
}
