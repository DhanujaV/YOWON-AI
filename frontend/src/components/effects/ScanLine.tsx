/**
 * ScanLine — a subtle moving scan line across the page.
 * Pure CSS animation, respects prefers-reduced-motion.
 */
export default function ScanLine() {
  return (
    <div
      className="fixed inset-x-0 top-0 h-px pointer-events-none z-[1] opacity-0 [animation:scan_6s_linear_infinite]"
      aria-hidden="true"
      style={{
        background: 'linear-gradient(90deg, transparent 0%, rgba(0,229,255,0.35) 50%, transparent 100%)',
        animation: 'scan 6s linear infinite',
      }}
    />
  )
}
