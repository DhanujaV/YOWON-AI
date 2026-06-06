import { motion } from 'framer-motion'

export default function NeuralOverlay() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10 opacity-20">
      <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="neural-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#A855F7" stopOpacity="0.6" />
            <stop offset="50%" stopColor="#EC4899" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#F59E0B" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        {[
          'M50,50 L200,120 L350,80 L500,150',
          'M100,200 L250,180 L400,220 L550,190',
          'M80,350 L220,300 L380,340 L520,310',
        ].map((path, i) => (
          <motion.path
            key={i}
            d={path}
            fill="none"
            stroke="url(#neural-grad)"
            strokeWidth="1"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: [0.3, 0.7, 0.3] }}
            transition={{
              pathLength: { duration: 3, delay: i * 0.5 },
              opacity: { duration: 4, repeat: Infinity, delay: i * 0.3 },
            }}
          />
        ))}
      </svg>
    </div>
  )
}
