import { motion } from 'framer-motion'

/**
 * 3D Synthwave/Cyberpunk Perspective Grid Floor & Ceiling.
 * Creates an immersive 3D infinite space that moves, giving a high-end customized feel.
 */
export default function AnimatedGrid() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-20 bg-[#07070a]">
      {/* Radial ambient glow orbs */}
      <div
        className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full opacity-[0.09] mix-blend-screen"
        style={{
          background: 'radial-gradient(circle, rgba(0,229,255,0.8) 0%, transparent 70%)',
          filter: 'blur(100px)',
        }}
      />
      <div
        className="absolute bottom-10 right-1/4 w-[600px] h-[600px] rounded-full opacity-[0.07] mix-blend-screen"
        style={{
          background: 'radial-gradient(circle, rgba(124,58,237,0.7) 0%, transparent 70%)',
          filter: 'blur(100px)',
        }}
      />

      {/* 3D Perspective Grid Container */}
      <div className="absolute inset-0" style={{ perspective: '450px', perspectiveOrigin: '50% 50%' }}>
        
        {/* Floor Grid */}
        <motion.div
          className="absolute inset-x-0 bottom-0 h-[60%] opacity-40"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0, 229, 255, 0.08) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0, 229, 255, 0.08) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
            transformOrigin: '50% 0%',
            transform: 'rotateX(75deg) scale(3) translateY(-10%)',
          }}
          animate={{ backgroundPositionY: ['0px', '40px'] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        />

        {/* Ceiling Grid */}
        <motion.div
          className="absolute inset-x-0 top-0 h-[50%] opacity-[0.15]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(124, 58, 237, 0.08) 1px, transparent 1px),
              linear-gradient(90deg, rgba(124, 58, 237, 0.08) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
            transformOrigin: '50% 100%',
            transform: 'rotateX(-75deg) scale(3) translateY(10%)',
          }}
          animate={{ backgroundPositionY: ['0px', '-40px'] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
        />
      </div>

      {/* Horizon glow divider line */}
      <div className="absolute inset-x-0 top-[50%] h-px bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent shadow-[0_0_15px_rgba(0,229,255,0.5)]" />

      {/* Vignette overlays to blur and darken edges for depth */}
      <div className="absolute inset-0 bg-gradient-to-t from-[#09090B] via-transparent to-[#09090B] opacity-90" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#09090B] via-transparent to-[#09090B] opacity-40" />
    </div>
  )
}

