import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CircuitBoard, Radio, Trophy, LayoutDashboard } from 'lucide-react'

const NAV_LINKS = [
  { to: '/leaderboard', label: 'Rankings', icon: Trophy },
  { to: '/jury',        label: 'AI Jury',  icon: LayoutDashboard },
]

export default function Header() {
  const { pathname } = useLocation()

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-yowon-bg/85 backdrop-blur-2xl">
      {/* Subtle top glow line */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">

        {/* Wordmark */}
        <Link to="/" className="flex items-center gap-2.5 shrink-0 group">
          <motion.div
            className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 via-emerald-400 to-violet-600 flex items-center justify-center"
            whileHover={{ scale: 1.08 }}
            style={{ boxShadow: '0 0 14px rgba(0,229,255,0.30)' }}
          >
            <CircuitBoard size={16} className="text-[#04111F]" />
          </motion.div>
          <div className="leading-none">
            <span className="font-display font-bold text-base text-white tracking-tight">
              YOWON AI
            </span>
            <p className="text-[9px] font-mono text-yowon-muted tracking-[0.22em] uppercase hidden sm:block mt-0.5">
              AI Operating System
            </p>
          </div>
        </Link>

        {/* Center Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => {
            const active = pathname.startsWith(to)
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? 'bg-cyan-300/10 text-cyan-200 border border-cyan-300/20'
                    : 'text-yowon-muted hover:text-white hover:bg-white/[0.05]'
                }`}
              >
                <Icon size={14} />
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden sm:flex items-center gap-2 glass-pill px-3 py-1.5 border-cyan-300/15">
            <Radio size={11} className="text-emerald-400 animate-pulse" />
            <span className="text-[10px] font-mono text-yowon-muted tracking-[0.18em] uppercase">
              LIVE
            </span>
          </div>

          {pathname !== '/submit' && (
            <Link
              to="/submit"
              className="yowon-btn-primary yowon-btn-sm"
            >
              New Evaluation
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
