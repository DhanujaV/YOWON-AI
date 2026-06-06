import { Link, useLocation } from 'react-router-dom'
import { Shield, Radio } from 'lucide-react'
import { motion } from 'framer-motion'

export default function Header() {
  const { pathname } = useLocation()
  const isLanding = pathname === '/'

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-sentinel-bg/75 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <motion.div
            className="w-9 h-9 rounded-lg bg-gradient-to-br from-violet-500 via-pink-500 to-amber-400 flex items-center justify-center shadow-glow-violet"
            whileHover={{ scale: 1.05 }}
          >
            <Shield size={18} className="text-white" />
          </motion.div>
          <div>
            <span className="font-display font-bold text-lg text-sentinel-text tracking-tight">
              Project Sentinel
            </span>
            {!isLanding && (
              <p className="text-[10px] text-sentinel-muted font-mono tracking-widest uppercase hidden sm:block">
                Deployment Readiness Intelligence
              </p>
            )}
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 glass-pill px-3 py-1.5 border-emerald-500/20">
            <Radio size={12} className="text-emerald-400 animate-pulse" />
            <span className="text-xs font-mono text-sentinel-muted">SYSTEM ONLINE</span>
          </div>
          {pathname !== '/submit' && (
            <Link to="/submit" className="sentinel-btn-primary text-sm py-2 px-4">
              Start Evaluation
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
