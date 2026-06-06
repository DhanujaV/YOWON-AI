import type { ReactNode } from 'react'
import AnimatedGrid from '../effects/AnimatedGrid'
import ParticleField from '../effects/ParticleField'
import Header from './Header'

interface AppShellProps {
  children: ReactNode
  showHeader?: boolean
  particles?: boolean
  scan?: boolean
}

export default function AppShell({
  children,
  showHeader = true,
  particles = true,
}: AppShellProps) {
  return (
    <div className="min-h-screen relative">
      <AnimatedGrid />
      {particles && <ParticleField />}
      {showHeader && <Header />}
      <div className="relative z-10">{children}</div>
    </div>
  )
}
