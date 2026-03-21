import './index.css'

/**
 * Octant AI — Root Application Component.
 *
 * Placeholder for Section 1 scaffolding. The full three-panel layout
 * (LeftPanel, CenterPanel, RightPanel) with PULSE WebSocket state
 * management will be built in Section 14.
 */
function App() {
  return (
    <div className="min-h-screen bg-oct-deep flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-oct-text mb-4">
          🧭 Octant AI
        </h1>
        <p className="text-oct-text-dim text-lg">
          Autonomous Quantitative Research Workbench
        </p>
        <div className="mt-8 w-3 h-3 rounded-full bg-oct-green mx-auto animate-pulse-green" />
      </div>
    </div>
  )
}

export default App
