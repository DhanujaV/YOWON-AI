import { motion } from 'framer-motion'

export default function AnimatedGrid() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
      <div className="absolute inset-0 grid-bg opacity-50" />
      <motion.div
        className="absolute inset-0 opacity-25"
        style={{
          backgroundImage:
            'linear-gradient(90deg, transparent 0%, rgba(168,85,247,0.1) 35%, rgba(236,72,153,0.08) 65%, transparent 100%)',
          backgroundSize: '200% 100%',
        }}
        animate={{ backgroundPosition: ['0% 0%', '200% 0%'] }}
        transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-sentinel-bg via-transparent to-sentinel-bg" />
    </div>
  )
}
