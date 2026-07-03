/**
 * NeuralOverlay — subtle diagonal circuit lines on the page background.
 * Pure CSS, lightweight.
 */
export default function NeuralOverlay() {
  return (
    <div
      className="fixed inset-0 pointer-events-none -z-[6] opacity-[0.025]"
      aria-hidden="true"
      style={{
        backgroundImage: `
          repeating-linear-gradient(
            45deg,
            rgba(0,229,255,0.9) 0px,
            rgba(0,229,255,0.9) 1px,
            transparent 1px,
            transparent 80px
          ),
          repeating-linear-gradient(
            -45deg,
            rgba(0,255,163,0.9) 0px,
            rgba(0,255,163,0.9) 1px,
            transparent 1px,
            transparent 120px
          )
        `,
      }}
    />
  )
}
