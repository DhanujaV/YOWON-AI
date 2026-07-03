import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight, Zap, Radio, Shield, Clock, Layers, Sparkles,
  CheckCircle2, GitBranch, FileSearch, Trophy, Scale, Network,
  Cpu, Lock, Globe, Gavel, Brain, Lightbulb, Presentation,
  ChevronRight,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import NeuralNetwork from '../components/landing/NeuralNetwork'
import AgentShowcase from '../components/landing/AgentShowcase'
import ScanLine from '../components/effects/ScanLine'
import NeuralOverlay from '../components/effects/NeuralOverlay'

const STATS = [
  { value: '8',   label: 'Council Agents',       icon: Layers,      color: 'text-cyan-300' },
  { value: '6',   label: 'Readiness Dimensions', icon: FileSearch,  color: 'text-emerald-400' },
  { value: '<5m', label: 'To Verdict',            icon: Clock,       color: 'text-violet-400' },
]

const FEATURES = [
  {
    icon: GitBranch,
    title: 'Repository Intelligence',
    desc: 'Deep architecture analysis, code quality signals, and deployment blockers from your GitHub repo.',
    accentColor: 'rgba(0,229,255,0.18)',
    iconColor: 'text-cyan-300',
    iconBg: 'rgba(0,229,255,0.10)',
  },
  {
    icon: Shield,
    title: 'Sentinel Security Audit',
    desc: 'OWASP-style review, secret detection, dependency scanning, and failure-mode forecasting.',
    accentColor: 'rgba(239,68,68,0.18)',
    iconColor: 'text-red-400',
    iconBg: 'rgba(239,68,68,0.10)',
  },
  {
    icon: Sparkles,
    title: 'Executive Verdict',
    desc: 'A single deployment readiness score with clear accept, improve, or reject guidance — board-ready.',
    accentColor: 'rgba(124,58,237,0.22)',
    iconColor: 'text-violet-400',
    iconBg: 'rgba(124,58,237,0.12)',
  },
]

const DNA_BARS = [
  { label: 'Architecture', value: 84, color: '#00E5FF' },
  { label: 'Security',     value: 76, color: '#EF4444' },
  { label: 'Novelty',      value: 68, color: '#00FFA3' },
  { label: 'Evidence',     value: 72, color: '#7C3AED' },
]

const AGENTS = [
  { icon: Brain,        name: 'Coordinator', color: '#00E5FF', role: 'Context Builder' },
  { icon: Cpu,          name: 'Forge',        color: '#22D3EE', role: 'Architecture' },
  { icon: Lock,         name: 'Sentinel',     color: '#EF4444', role: 'Security' },
  { icon: Lightbulb,   name: 'Visionary',    color: '#00FFA3', role: 'Innovation' },
  { icon: Globe,        name: 'Guardian',     color: '#00FFA3', role: 'Risk' },
  { icon: Presentation, name: 'Showcase',     color: '#7C3AED', role: 'Pitch' },
  { icon: Gavel,        name: 'YOWON Prime',  color: '#7C3AED', role: 'Chief Judge' },
]

const READINESS_STEPS = [
  { step: '01', label: 'Evidence Gathering',  done: true  },
  { step: '02', label: 'Architecture Review', done: true  },
  { step: '03', label: 'Security Audit',      done: true  },
  { step: '04', label: 'Deployment Verdict',  done: false },
]

const fadeUp = {
  hidden:  { opacity: 0, y: 24 },
  visible: (i: number = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.5 } }),
}

export default function LandingPage() {
  const [progress, setProgress] = useState(3)
  const [loaded, setLoaded] = useState(false)

  // Simulation loading progress
  useEffect(() => {
    if (progress < 100) {
      const timeout = setTimeout(() => {
        setProgress(prev => {
          const next = prev + Math.floor(Math.random() * 20) + 8
          return next > 100 ? 100 : next
        })
      }, 150 + Math.random() * 150)
      return () => clearTimeout(timeout)
    } else {
      const timeout = setTimeout(() => {
        setLoaded(true)
      }, 500)
      return () => clearTimeout(timeout)
    }
  }, [progress])

  if (!loaded) {
    return (
      <div className="fixed inset-0 z-50 bg-[#06070a] flex items-center justify-center select-none overflow-hidden">
        {/* Minimal Bottom Left Ticker */}
        <div className="absolute bottom-16 left-16 flex flex-col gap-2 z-10 text-left font-mono">
          {/* Animated line indicator */}
          <div className="w-20 h-px bg-white/20 relative overflow-hidden">
            <motion.div
              className="absolute inset-y-0 left-0 bg-[#00FFA3]"
              initial={{ width: '0%' }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.15 }}
            />
          </div>
          <span className="text-[10px] text-yowon-muted uppercase tracking-[0.25em]">
            AI Council Booting
          </span>
          <span className="text-3xl font-light text-white font-sans mt-1">
            {progress}%
          </span>
        </div>

        {/* Outer Frame border trace */}
        <div className="absolute inset-6 border border-white/[0.04] rounded-[24px] pointer-events-none" />
      </div>
    )
  }

  return (
    <AppShell showHeader={false} particles>
      <div className="fixed inset-0 pointer-events-none -z-[5] bg-aurora-radial mission-control-bg" />
      <ScanLine />
      <NeuralOverlay />

      {/* =========================================
          HERO
      ========================================= */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-4 sm:px-6 pt-20 pb-12">

        {/* Top bar */}
        <motion.div
          className="w-full max-w-7xl mx-auto flex items-center justify-between mb-12"
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 via-emerald-400 to-violet-600 flex items-center justify-center"
              style={{ boxShadow: '0 0 14px rgba(0,229,255,0.30)' }}>
              <Shield size={16} className="text-[#04111F]" />
            </div>
            <span className="font-display font-bold text-white tracking-tight">YOWON AI</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/jury"        className="yowon-btn-ghost yowon-btn-sm hidden sm:flex">AI Jury</Link>
            <Link to="/leaderboard" className="yowon-btn-ghost yowon-btn-sm hidden sm:flex">Rankings</Link>
            <Link to="/submit"      className="yowon-btn-primary yowon-btn-sm">Start Evaluation</Link>
          </div>
        </motion.div>

        {/* Hero grid */}
        <div className="w-full max-w-7xl mx-auto grid lg:grid-cols-2 gap-10 lg:gap-8 items-center">

          {/* Left: Copy */}
          <div>
            <motion.div
              className="inline-flex items-center gap-2 glass-pill px-3.5 py-1.5 mb-6"
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <Radio size={12} className="text-emerald-400 animate-pulse" />
              <span className="text-[10px] font-mono text-yowon-muted tracking-[0.22em] uppercase">
                Enterprise AI Evaluation Network
              </span>
            </motion.div>

            <motion.h1
              className="text-5xl sm:text-6xl lg:text-7xl font-black tracking-tight leading-[1.02] mb-4"
              style={{ fontFamily: "'Space Grotesk', sans-serif" }}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
            >
              <span className="gradient-text">YOWON AI</span>
            </motion.h1>

            <motion.p
              className="text-xl sm:text-2xl font-medium gradient-text-subtle mb-4 leading-snug"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.28 }}
            >
              Autonomous AI Jury Platform
            </motion.p>

            <motion.p
              className="text-yowon-muted text-base sm:text-lg max-w-lg mb-8 leading-relaxed"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.38 }}
            >
              Judge-grade project intelligence for teams that need a defensible verdict,
              benchmark context, and a clear action path from prototype to enterprise deployment.
            </motion.p>

            <motion.div
              className="flex flex-col sm:flex-row gap-3 mb-10"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.48 }}
            >
              <Link to="/submit"
                className="yowon-btn-primary flex items-center gap-2 text-sm">
                <Zap size={16} />
                Start Evaluation
                <ArrowRight size={15} />
              </Link>
              <Link to="/demo" className="yowon-btn-ghost text-sm">
                View Demo Report
              </Link>
              <Link to="/jury" className="yowon-btn-ghost text-sm">
                <Shield size={14} className="text-emerald-400" />
                AI Jury
              </Link>
            </motion.div>

            {/* Stats strip */}
            <motion.div
              className="grid grid-cols-3 gap-3 max-w-sm"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.58 }}
            >
              {STATS.map(({ value, label, icon: Icon, color }) => (
                <div key={label} className="metric-card !p-3.5 text-center">
                  <Icon size={14} className={`mx-auto mb-2 ${color}`} />
                  <p className="text-xl font-black tracking-tight text-white"
                    style={{ fontFamily: "'Space Grotesk', sans-serif" }}>{value}</p>
                  <p className="text-[10px] text-yowon-muted mt-0.5 leading-tight">{label}</p>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right: Network card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="cyber-glow-card"
          >
            <div className="cyber-glow-inner !p-6">
              <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/60 to-transparent pointer-events-none" />
              <p className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.25em] mb-4 text-center">
                Judge Simulation Network
              </p>
              <NeuralNetwork />
              <ul className="mt-5 grid grid-cols-3 gap-2">
                {AGENTS.slice(0, 3).map(item => (
                  <li key={item.name} className="flex items-center gap-2 text-xs text-yowon-muted">
                    <CheckCircle2 size={12} className="text-emerald-400 shrink-0" />
                    {item.name}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        </div>
      </section>

      {/* =========================================
          BENTO GRID — Overview Dashboard
      ========================================= */}
      <section className="px-4 sm:px-6 pb-16">
        <div className="max-w-7xl mx-auto">

          {/* Row 1 */}
          <div className="grid lg:grid-cols-12 gap-4 mb-4">

            {/* Project DNA — large card */}
            <motion.div
              className="glass-card lg:col-span-5 accent-emerald"
              variants={fadeUp} initial="hidden" whileInView="visible"
              viewport={{ once: true }}
            >
              <div className="module-header">
                <div className="icon-wrap"><Network size={16} className="text-emerald-400" /></div>
                <div className="label-group">
                  <span className="eyebrow">Live Analysis</span>
                  <span className="title">Project DNA</span>
                </div>
              </div>
              <div className="space-y-3">
                {DNA_BARS.map(item => (
                  <div key={item.label}>
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-yowon-muted font-medium">{item.label}</span>
                      <span className="font-mono font-bold" style={{ color: item.color }}>{item.value}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ background: item.color }}
                        initial={{ width: 0 }}
                        whileInView={{ width: `${item.value}%` }}
                        viewport={{ once: true }}
                        transition={{ duration: 1, ease: 'easeOut', delay: 0.1 }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Benchmark */}
            <motion.div
              className="glass-card lg:col-span-3"
              variants={fadeUp} custom={1} initial="hidden" whileInView="visible"
              viewport={{ once: true }}
            >
              <div className="module-header mb-3">
                <div className="icon-wrap"><Scale size={16} className="text-emerald-400" /></div>
                <div className="label-group">
                  <span className="eyebrow">Global</span>
                  <span className="title">Benchmark</span>
                </div>
              </div>
              <p className="text-4xl font-black tracking-tight text-white mb-1"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}>Top 12%</p>
              <p className="text-xs text-yowon-muted leading-relaxed">
                Global readiness percentile after rubric calibration across all submitted projects.
              </p>
            </motion.div>

            {/* Ranking */}
            <motion.div
              className="glass-card lg:col-span-2"
              variants={fadeUp} custom={2} initial="hidden" whileInView="visible"
              viewport={{ once: true }}
            >
              <div className="module-header mb-3">
                <div className="icon-wrap"><Trophy size={16} className="text-violet-400" /></div>
                <div className="label-group">
                  <span className="eyebrow">Position</span>
                  <span className="title">Ranking</span>
                </div>
              </div>
              <p className="text-4xl font-black tracking-tight text-white mb-1"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}>#48</p>
              <p className="text-xs text-yowon-muted">Among comparable submissions</p>
            </motion.div>

            {/* CTA card */}
            <motion.div
              className="glass-card lg:col-span-2 accent-violet flex flex-col justify-between"
              variants={fadeUp} custom={3} initial="hidden" whileInView="visible"
              viewport={{ once: true }}
            >
              <div>
                <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-2">
                  Ready?
                </p>
                <p className="text-sm font-semibold text-white leading-snug">
                  Get your verdict in minutes
                </p>
              </div>
              <Link to="/submit"
                className="mt-4 flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-violet-500/15 border border-violet-500/25 text-violet-300 text-xs font-semibold hover:bg-violet-500/22 transition-all">
                Start Now
                <ChevronRight size={14} />
              </Link>
            </motion.div>
          </div>

          {/* Row 2: Readiness Ladder + Agent cards */}
          <div className="grid lg:grid-cols-12 gap-4">

            {/* Readiness Ladder */}
            <motion.div
              className="glass-card lg:col-span-4"
              variants={fadeUp} initial="hidden" whileInView="visible"
              viewport={{ once: true }}
            >
              <div className="module-header">
                <div className="icon-wrap text-cyan-300">
                  <CheckCircle2 size={16} className="text-cyan-300" />
                </div>
                <div className="label-group">
                  <span className="eyebrow">Evaluation Path</span>
                  <span className="title">Readiness Ladder</span>
                </div>
              </div>
              <div className="space-y-2">
                {READINESS_STEPS.map(({ step, label, done }) => (
                  <div key={step}
                    className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                      done
                        ? 'border-emerald-500/20 bg-emerald-500/[0.06]'
                        : 'border-white/[0.06] bg-white/[0.02]'
                    }`}>
                    <span className="font-mono text-[10px] font-bold"
                      style={{ color: done ? '#34D399' : '#52525B' }}>{step}</span>
                    <span className={`text-sm font-medium ${done ? 'text-white' : 'text-yowon-muted'}`}>
                      {label}
                    </span>
                    {done && <CheckCircle2 size={13} className="ml-auto text-emerald-400 shrink-0" />}
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Agent Network strip */}
            <motion.div
              className="glass-card lg:col-span-8"
              variants={fadeUp} custom={1} initial="hidden" whileInView="visible"
              viewport={{ once: true }}
            >
              <div className="module-header">
                <div className="icon-wrap"><Brain size={16} className="text-cyan-300" /></div>
                <div className="label-group">
                  <span className="eyebrow">AI Council</span>
                  <span className="title">Jury Agents</span>
                </div>
              </div>
              <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
                {AGENTS.map(({ icon: Icon, name, color, role }) => (
                  <div key={name} className="flex flex-col items-center gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-white/10 transition-all group cursor-default">
                    <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                      style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
                      <Icon size={16} style={{ color }} />
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] font-semibold text-white leading-tight">{name}</p>
                      <p className="text-[9px] text-yowon-muted mt-0.5">{role}</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* =========================================
          FEATURES
      ========================================= */}
      <section className="py-16 px-4 sm:px-6 border-t border-white/[0.05]">
        <div className="max-w-7xl mx-auto">
          <motion.div
            className="mb-10"
            initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <p className="text-[10px] font-mono uppercase tracking-[0.28em] text-yowon-muted mb-2">Capabilities</p>
            <h2 className="text-2xl sm:text-3xl font-bold text-white" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Enterprise-Grade Evaluation
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-4">
            {FEATURES.map(({ icon: Icon, title, desc, accentColor, iconColor, iconBg }, i) => (
              <motion.div
                key={title}
                className="glass-card group"
                style={{ borderColor: accentColor }}
                variants={fadeUp} custom={i} initial="hidden"
                whileInView="visible" viewport={{ once: true }}
                whileHover={{ y: -2 }}
              >
                <div className="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent pointer-events-none rounded-[inherit]" />
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${iconColor}`}
                  style={{ background: iconBg, border: `1px solid ${accentColor}` }}>
                  <Icon size={20} />
                </div>
                <h3 className="font-semibold text-white mb-2"
                  style={{ fontFamily: "'Space Grotesk', sans-serif" }}>{title}</h3>
                <p className="text-sm text-yowon-muted leading-relaxed">{desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* =========================================
          AGENT SHOWCASE
      ========================================= */}
      <section className="py-16 px-4 sm:px-6 border-t border-white/[0.05]">
        <div className="max-w-7xl mx-auto">
          <motion.div
            className="text-center mb-10"
            initial={{ opacity: 0 }} whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            <p className="text-[10px] font-mono uppercase tracking-[0.28em] text-yowon-muted mb-2">The Council</p>
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3"
              style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Your AI Evaluation Jury
            </h2>
            <p className="text-yowon-muted max-w-lg mx-auto text-sm">
              The Council analyzes every dimension of deployment readiness in parallel.
            </p>
          </motion.div>
          <AgentShowcase />
        </div>
      </section>

      {/* =========================================
          CTA
      ========================================= */}
      <section className="py-20 px-4 text-center border-t border-white/[0.05]">
        <motion.div
          className="glass-card max-w-2xl mx-auto !p-10 accent-violet relative overflow-hidden"
          initial={{ opacity: 0, scale: 0.97 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
        >
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-violet-400/60 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-b from-violet-500/[0.04] to-transparent pointer-events-none" />

          <div className="relative z-10">
            <Sparkles className="mx-auto mb-4 text-violet-400" size={32} />
            <h2 className="text-2xl sm:text-3xl font-bold mb-3 text-white"
              style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Ready for{' '}
              <span className="gradient-text">Deployment Intelligence</span>?
            </h2>
            <p className="text-yowon-muted mb-7 max-w-md mx-auto text-sm leading-relaxed">
              Get a board-ready verdict in minutes, not weeks of manual review cycles.
              Enterprise-grade AI analysis at hackathon speed.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link to="/submit" className="yowon-btn-primary flex items-center gap-2">
                Launch Evaluation <ArrowRight size={16} />
              </Link>
              <Link to="/leaderboard" className="yowon-btn-ghost text-sm">
                View Rankings
              </Link>
            </div>
          </div>
        </motion.div>
      </section>
    </AppShell>
  )
}

