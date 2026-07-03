import { useEffect, useRef } from 'react'

interface Particle {
  x: number
  y: number
  originX: number
  originY: number
  vx: number
  vy: number
  size: number
  color: string
  alpha: number
  targetAlpha: number
}

const COLORS = ['#00E5FF', '#00FFA3', '#7C3AED', '#00FFA3', '#00E5FF']

/**
 * Advanced Interactive Particle Field.
 * Particles drift organically, connect to near neighbors, and react dynamically
 * to mouse movements (pulled slightly towards or pushed away based on proximity).
 */
export default function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouseRef = useRef({ x: -1000, y: -1000, active: false })

  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) return

    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number
    let particles: Particle[] = []

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }

    const init = () => {
      particles = []
      // High-density but lightweight particle count
      const count = Math.min(65, Math.floor((window.innerWidth * window.innerHeight) / 22000))
      for (let i = 0; i < count; i++) {
        const x = Math.random() * canvas.width
        const y = Math.random() * canvas.height
        particles.push({
          x,
          y,
          originX: x,
          originY: y,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          size: Math.random() * 1.8 + 0.6,
          color: COLORS[Math.floor(Math.random() * COLORS.length)],
          alpha: Math.random() * 0.3 + 0.1,
          targetAlpha: Math.random() * 0.3 + 0.1,
        })
      }
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const mouse = mouseRef.current

      // Update & Draw Particles
      for (const p of particles) {
        // Base drift
        p.x += p.vx
        p.y += p.vy

        // Wrap around screen edges
        if (p.x < 0) { p.x = canvas.width; p.originX = canvas.width }
        if (p.x > canvas.width) { p.x = 0; p.originX = 0 }
        if (p.y < 0) { p.y = canvas.height; p.originY = canvas.height }
        if (p.y > canvas.height) { p.y = 0; p.originY = 0 }

        // Mouse interaction: gravity pull/push
        if (mouse.active) {
          const dx = mouse.x - p.x
          const dy = mouse.y - p.y
          const dist = Math.hypot(dx, dy)
          const maxInteractionDist = 180

          if (dist < maxInteractionDist) {
            // Force strength proportional to distance
            const force = (maxInteractionDist - dist) / maxInteractionDist
            const angle = Math.atan2(dy, dx)
            // Pull cyber particles gently toward mouse
            p.x += Math.cos(angle) * force * 0.6
            p.y += Math.sin(angle) * force * 0.6
            // Temporary glow increase
            p.alpha = Math.min(0.7, p.alpha + 0.02)
          } else {
            // Return to target alpha slowly
            p.alpha = p.alpha > p.targetAlpha ? p.alpha - 0.005 : p.targetAlpha
          }
        }

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = `${p.color}${Math.round(p.alpha * 255).toString(16).padStart(2, '0')}`
        ctx.fill()
      }

      // Draw connection lines
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const dist = Math.hypot(a.x - b.x, a.y - b.y)
          const connectionLimit = 130

          if (dist < connectionLimit) {
            let alpha = (1 - dist / connectionLimit) * 0.12
            // Increase connection line visibility near mouse
            if (mouse.active) {
              const mouseDistA = Math.hypot(mouse.x - a.x, mouse.y - a.y)
              const mouseDistB = Math.hypot(mouse.x - b.x, mouse.y - b.y)
              if (mouseDistA < 140 || mouseDistB < 140) {
                alpha *= 1.8
              }
            }
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.strokeStyle = `rgba(0, 229, 255, ${alpha})`
            ctx.lineWidth = 0.6
            ctx.stroke()
          }
        }
      }

      animId = requestAnimationFrame(draw)
    }

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = e.clientX
      mouseRef.current.y = e.clientY
      mouseRef.current.active = true
    }

    const handleMouseLeave = () => {
      mouseRef.current.active = false
    }

    resize()
    init()
    draw()

    window.addEventListener('resize', () => { resize(); init() })
    window.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none -z-10 opacity-70"
      aria-hidden="true"
    />
  )
}

