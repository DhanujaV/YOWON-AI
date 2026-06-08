import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight, Play, Zap, Radio, Shield, Clock, Layers, Sparkles,
  CheckCircle2, GitBranch, FileSearch,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import NeuralNetwork from '../components/landing/NeuralNetwork'
import AgentShowcase from '../components/landing/AgentShowcase'
import ScanLine from '../components/effects/ScanLine'
import NeuralOverlay from '../components/effects/NeuralOverlay'

const STATS = [
  { value: '10', label: 'AI Specialists', icon: Layers, color: 'text-violet-400' },
  { value: '6', label: 'Readiness Dimensions', icon: FileSearch, color: 'text-pink-400' },
  { value: '<5m', label: 'To Verdict', icon: Clock, color: 'text-amber-400' },
]

const FEATURES = [
  {
    icon: GitBranch,
    title: 'Repo & Code Analysis',
    desc: 'Architecture, quality signals, and deployment blockers from your GitHub repo.',
    gradient: 'from-violet-500/20 to-violet-500/5',
    iconColor: 'text-violet-400',
  },
  {
    icon: Shield,
    title: 'Security & Risk Jury',
    desc: 'OWASP-style review plus failure-mode forecasting before you ship.',
    gradient: 'from-pink-500/20 to-pink-500/5',
    iconColor: 'text-pink-400',
  },
  {
    icon: Sparkles,
    title: 'Executive Verdict',
    desc: 'A single deployment readiness score with clear accept, improve, or reject guidance.',
    gradient: 'from-amber-500/20 to-amber-500/5',
    iconColor: 'text-amber-400',
  },
]

export default function LandingPage() {
  return (
    <AppShell showHeader={false} particles>
      <div className="fixed inset-0 pointer-events-none -z-[5] bg-aurora-radial mission-control-bg" />
      <div className="hero-orb w-[420px] h-[420px] -top-32 -left-24 bg-violet-600/30" />
      <div className="hero-orb w-[360px] h-[360px] top-1/4 -right-20 bg-pink-600/25" />
      <div className="hero-orb w-[280px] h-[280px] bottom-32 left-1/3 bg-amber-500/15" />
      <ScanLine />
      <NeuralOverlay />

      <section className="relative min-h-screen flex flex-col items-center justify-center px-4 sm:px-6 pt-24 pb-20">
        <motion.div
          className="inline-flex items-center gap-2 glass-pill px-4 py-2 mb-8 border-violet-500/20"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Radio size={14} className="text-emerald-400 animate-pulse" />
          <span className="text-xs font-mono text-yowon-muted tracking-widest uppercase">
            Multi-Agent AI - Deployment Intelligence
          </span>
        </motion.div>

        <div className="w-full max-w-6xl mx-auto grid lg:grid-cols-2 gap-12 lg:gap-8 items-center">
          <div className="text-center lg:text-left">
            <motion.h1
              className="text-5xl sm:text-6xl lg:text-7xl font-bold font-display mb-4 tracking-tight leading-[1.05]"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.1 }}
            >
              <span className="gradient-text">YOWON AI</span>
            </motion.h1>

            <motion.p
              className="text-xl sm:text-2xl font-display gradient-text-subtle mb-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.25 }}
            >
              Know if you&apos;re ready to deploy before production does.
            </motion.p>

            <motion.p
              className="text-yowon-muted text-base sm:text-lg max-w-xl mx-auto lg:mx-0 mb-8 leading-relaxed"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.35 }}
            >
              Upload code, docs, and decks. Our AI jury runs in parallel across engineering,
              security, innovation, and risk, then delivers one clear deployment verdict.
            </motion.p>

            <motion.div
              className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start mb-10"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45 }}
            >
              <Link to="/submit" className="yowon-btn-primary flex items-center justify-center gap-2 text-base px-8">
                <Zap size={18} />
                Start Evaluation
                <ArrowRight size={16} />
              </Link>
              <Link to="/demo" className="yowon-btn-ghost">
                <Play size={16} className="text-amber-400" />
                View Demo
              </Link>
              <Link to="/jury" className="yowon-btn-ghost">
                <Shield size={16} className="text-cyan-300" />
                AI Jury
              </Link>
            </motion.div>

            <motion.div
              className="grid grid-cols-3 gap-3 max-w-md mx-auto lg:mx-0"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55 }}
            >
              {STATS.map(({ value, label, icon: Icon, color }) => (
                <div
                  key={label}
                  className="glass-card p-3 sm:p-4 text-center !rounded-xl border-white/[0.06]"
                >
                  <Icon size={16} className={`mx-auto mb-2 ${color}`} />
                  <p className="text-xl sm:text-2xl font-display font-bold text-yowon-text">{value}</p>
                  <p className="text-[10px] sm:text-xs text-yowon-muted mt-0.5 leading-tight">{label}</p>
                </div>
              ))}
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="relative"
          >
            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-violet-500/10 via-pink-500/10 to-amber-500/10 blur-2xl" />
            <div className="relative glass-card p-6 sm:p-8 neon-border">
              <p className="text-xs font-mono text-yowon-muted uppercase tracking-widest mb-4 text-center">
                Live agent mesh
              </p>
              <NeuralNetwork />
              <ul className="mt-6 space-y-2">
                {['Parallel specialist analysis', 'Cross-examined findings', 'Unified readiness score'].map(item => (
                  <li key={item} className="flex items-center gap-2 text-sm text-yowon-muted">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="py-16 px-4 sm:px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-4 sm:gap-6">
          {FEATURES.map(({ icon: Icon, title, desc, gradient, iconColor }, i) => (
            <motion.div
              key={title}
              className={`glass-card bg-gradient-to-br ${gradient} hover:border-white/15 transition-colors`}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <div className={`w-11 h-11 rounded-xl bg-white/5 flex items-center justify-center mb-4 ${iconColor}`}>
                <Icon size={22} />
              </div>
              <h3 className="font-display font-semibold text-lg text-yowon-text mb-2">{title}</h3>
              <p className="text-sm text-yowon-muted leading-relaxed">{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="py-20 px-4 sm:px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <motion.div
            className="text-center mb-12"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            <h2 className="text-2xl sm:text-3xl font-display font-bold text-yowon-text mb-3">
              Your AI Evaluation Jury
            </h2>
            <p className="text-yowon-muted max-w-lg mx-auto">
              Ten specialized agents analyze every dimension of deployment readiness in parallel.
            </p>
          </motion.div>
          <AgentShowcase />
        </div>
      </section>

      <section className="py-20 px-4 text-center border-t border-white/5">
        <motion.div
          className="glass-card max-w-2xl mx-auto p-10 relative overflow-hidden"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-violet-500 via-pink-500 to-amber-400" />
          <h2 className="text-2xl sm:text-3xl font-display font-bold mb-3">
            Ready for <span className="gradient-text">Deployment Intelligence</span>?
          </h2>
          <p className="text-yowon-muted mb-6 max-w-md mx-auto">
            Get a board-ready verdict in minutes, not weeks of manual review cycles.
          </p>
          <Link to="/submit" className="yowon-btn-primary inline-flex items-center gap-2">
            Launch Evaluation <ArrowRight size={16} />
          </Link>
          <Link to="/leaderboard" className="yowon-btn-ghost inline-flex items-center gap-2 ml-3 mt-3 sm:mt-0">
            View Rankings
          </Link>
        </motion.div>
      </section>
    </AppShell>
  )
}
