import { motion } from 'framer-motion'

export default function ScanLine() {
  return (
    <motion.div
      className="fixed left-0 right-0 h-px pointer-events-none -z-10"
      style={{
        background:
          'linear-gradient(90deg, transparent, rgba(168,85,247,0.5), rgba(236,72,153,0.5), transparent)',
        boxShadow: '0 0 24px rgba(168,85,247,0.35)',
      }}
      animate={{ top: ['0%', '100%'] }}
      transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
    />
  )
}
