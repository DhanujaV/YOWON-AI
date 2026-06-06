import { motion } from 'framer-motion'

const NODES = [
  { x: 50, y: 30 }, { x: 150, y: 60 }, { x: 250, y: 25 },
  { x: 350, y: 70 }, { x: 450, y: 40 }, { x: 100, y: 120 },
  { x: 200, y: 140 }, { x: 300, y: 110 }, { x: 400, y: 130 },
  { x: 250, y: 180 },
]

const EDGES = [
  [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [1, 6], [2, 7],
  [3, 8], [5, 6], [6, 7], [7, 8], [6, 9], [7, 9], [8, 9],
]

const NODE_COLORS = ['#A855F7', '#EC4899', '#F59E0B', '#14B8A6', '#A855F7']

export default function NeuralNetwork() {
  return (
    <div className="relative w-full max-w-xl mx-auto h-48 sm:h-56">
      <svg viewBox="0 0 500 200" className="w-full h-full">
        <defs>
          <radialGradient id="node-glow">
            <stop offset="0%" stopColor="#EC4899" stopOpacity="1" />
            <stop offset="100%" stopColor="#A855F7" stopOpacity="0" />
          </radialGradient>
        </defs>

        {EDGES.map(([a, b], i) => (
          <motion.line
            key={i}
            x1={NODES[a].x}
            y1={NODES[a].y}
            x2={NODES[b].x}
            y2={NODES[b].y}
            stroke="rgba(168,85,247,0.3)"
            strokeWidth="1"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1, opacity: [0.2, 0.65, 0.2] }}
            transition={{
              pathLength: { duration: 2, delay: i * 0.1 },
              opacity: { duration: 3, repeat: Infinity, delay: i * 0.15 },
            }}
          />
        ))}

        {NODES.map((node, i) => (
          <motion.g key={i}>
            <motion.circle
              cx={node.x}
              cy={node.y}
              r="12"
              fill="url(#node-glow)"
              animate={{ opacity: [0.4, 0.9, 0.4], scale: [1, 1.2, 1] }}
              transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.2 }}
            />
            <circle cx={node.x} cy={node.y} r="3" fill={NODE_COLORS[i % NODE_COLORS.length]} />
          </motion.g>
        ))}
      </svg>
    </div>
  )
}
