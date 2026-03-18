import { useState, useEffect, useRef } from 'react'
import * as THREE from 'three'

interface TerminalLine { type: 'system' | 'success' | 'warning' | 'error' | 'input'; text: string }
interface SensorData { light: number; gravity: { x: number; y: number; z: number }; timestamp: number }

const InfinityGlass = () => {
  const containerRef = useRef<HTMLDivElement>(null)
  const animationRef = useRef<number>(0)

  useEffect(() => {
    if (!containerRef.current) return
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(75, containerRef.current.clientWidth / containerRef.current.clientHeight, 0.1, 1000)
    camera.position.z = 120
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    containerRef.current.appendChild(renderer.domElement)

    // Stars
    const starGeo = new THREE.BufferGeometry()
    const positions = new Float32Array(2000 * 3)
    for (let i = 0; i < 2000 * 3; i += 3) {
      const r = 300 + Math.random() * 200
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      positions[i] = r * Math.sin(phi) * Math.cos(theta)
      positions[i + 1] = r * Math.sin(phi) * Math.sin(theta)
      positions[i + 2] = r * Math.cos(phi)
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.7, transparent: true, opacity: 0.8 }))
    scene.add(stars)

    // Singularity
    const singularity = new THREE.Mesh(new THREE.SphereGeometry(8, 32, 32), new THREE.MeshBasicMaterial({ color: 0x00ffcc, transparent: true, opacity: 0.9 }))
    scene.add(singularity)

    // Accretion disc
    const disc = new THREE.Mesh(new THREE.RingGeometry(12, 35, 64), new THREE.MeshBasicMaterial({ color: 0xffaa00, transparent: true, opacity: 0.3, side: THREE.DoubleSide }))
    disc.rotation.x = Math.PI / 2
    scene.add(disc)

    // Nodes
    const nodes: THREE.Mesh[] = []
    for (let i = 0; i < 20; i++) {
      const node = new THREE.Mesh(new THREE.SphereGeometry(1 + Math.random() * 2, 16, 16), new THREE.MeshBasicMaterial({ color: new THREE.Color().setHSL((i / 20) * 0.3 + 0.5, 1, 0.5), transparent: true, opacity: 0.8 }))
      const angle = (i / 20) * Math.PI * 2
      const radius = 40 + Math.random() * 50
      node.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius * 0.3, Math.sin(angle) * radius * 0.5)
      node.userData = { angle, radius, speed: 0.001 + Math.random() * 0.002, yOffset: node.position.y }
      scene.add(node)
      nodes.push(node)
    }

    const animate = () => {
      animationRef.current = requestAnimationFrame(animate)
      stars.rotation.y += 0.0002
      disc.rotation.z += 0.001
      const t = Date.now() * 0.001
      singularity.scale.setScalar(1 + Math.sin(t) * 0.1)
      nodes.forEach((node, i) => {
        node.userData.angle += node.userData.speed
        node.position.x = Math.cos(node.userData.angle) * node.userData.radius
        node.position.y = Math.sin(node.userData.angle) * node.userData.radius * 0.3 + node.userData.yOffset * Math.cos(t * 0.5)
        const scale = 1 + Math.sin(t * 2 + i) * 0.3
        node.scale.set(scale, scale, scale)
      })
      renderer.render(scene, camera)
    }
    animate()

    const handleResize = () => {
      if (!containerRef.current) return
      camera.aspect = containerRef.current.clientWidth / containerRef.current.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    }
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationRef.current)
      renderer.dispose()
      if (containerRef.current) containerRef.current.removeChild(renderer.domElement)
    }
  }, [])

  return <div ref={containerRef} className="w-full h-full min-h-[400px]" />
}

const AROverlay = () => {
  const [active, setActive] = useState(false)
  const [gesture, setGesture] = useState({ detected: 'None', confidence: 0 })
  const [brightness, setBrightness] = useState(128)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: 640, height: 480 } })
      if (videoRef.current) { videoRef.current.srcObject = stream; setActive(true) }
    } catch { console.error('Camera denied') }
  }

  const stopCamera = () => {
    if (videoRef.current?.srcObject) { (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop()); videoRef.current.srcObject = null }
    setActive(false)
  }

  useEffect(() => {
    if (!active) return
    const canvas = canvasRef.current; const video = videoRef.current
    if (!canvas || !video) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const detect = () => {
      if (!video || video.readyState !== 4) { requestAnimationFrame(detect); return }
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data
      let b = 0
      for (let i = 0; i < d.length; i += 4) b += (d[i] + d[i + 1] + d[i + 2]) / 3
      setBrightness(Math.round(b / (d.length / 4)))
      if (Math.random() > 0.95) setGesture({ detected: ['Open Palm', 'Closed Fist', 'Pointing', 'Swipe Left', 'Swipe Right', 'None'][Math.floor(Math.random() * 6)], confidence: 0.7 + Math.random() * 0.3 })
      requestAnimationFrame(detect)
    }
    detect()
  }, [active])

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button onClick={startCamera} disabled={active} className="glass-button flex-1">Start Camera</button>
        <button onClick={stopCamera} disabled={!active} className="glass-button danger flex-1">Stop Camera</button>
      </div>
      <div className="relative">
        <video ref={videoRef} autoPlay playsInline muted className={`w-full rounded-lg ${active ? 'block' : 'hidden'}`} />
        <canvas ref={canvasRef} width={640} height={480} className="hidden" />
        {!active && <div className="w-full h-64 flex items-center justify-center glass-panel"><div className="text-center"><div className="text-4xl mb-2">📷</div><div className="text-sm opacity-70">Camera Inactive</div></div></div>}
        {active && <div className="absolute bottom-2 left-2 glass-panel p-2 text-xs"><div>Brightness: {brightness}</div><div>Gesture: {gesture.detected}</div></div>}
      </div>
    </div>
  )
}

const SensorBridge = () => {
  const [sensors, setSensors] = useState<SensorData>({ light: 128, gravity: { x: 0, y: 0, z: 9.8 }, timestamp: Date.now() })
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      if (connected) setSensors({ light: Math.max(0, Math.min(255, sensors.light + (Math.random() - 0.5) * 10)), gravity: { x: (Math.random() - 0.5) * 2, y: (Math.random() - 0.5) * 2, z: 9.8 + (Math.random() - 0.5) * 0.5 }, timestamp: Date.now() })
    }, 500)
    return () => clearInterval(interval)
  }, [connected, sensors.light])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm">Sensor Bridge</span>
        <button onClick={() => setConnected(!connected)} className={`glass-button text-sm px-4 ${connected ? 'danger' : ''}`}>{connected ? 'Disconnect' : 'Connect'}</button>
      </div>
      <div className="glass-panel p-4 space-y-3">
        <div className="flex justify-between items-center"><span className="text-xs opacity-70">Light Level</span><div className="flex items-center gap-2"><div className="w-24 h-2 bg-black rounded-full overflow-hidden"><div className="h-full bg-yellow-400 transition-all" style={{ width: `${(sensors.light / 255) * 100}%` }} /></div><span className="text-xs w-8">{Math.round(sensors.light)}</span></div></div>
        <div className="flex justify-between items-center"><span className="text-xs opacity-70">Gravity X</span><span className="text-xs">{sensors.gravity.x.toFixed(2)}</span></div>
        <div className="flex justify-between items-center"><span className="text-xs opacity-70">Gravity Y</span><span className="text-xs">{sensors.gravity.y.toFixed(2)}</span></div>
        <div className="flex justify-between items-center"><span className="text-xs opacity-70">Gravity Z</span><span className="text-xs">{sensors.gravity.z.toFixed(2)}</span></div>
      </div>
    </div>
  )
}

const LumenisTerminal = () => {
  const [lines, setLines] = useState<TerminalLine[]>([{ type: 'system', text: 'One2lvOS Terminal v2.0' }, { type: 'system', text: 'Lumenis AI Online' }, { type: 'system', text: 'Type "help" for commands' }, { type: 'system', text: '---' }])
  const [input, setInput] = useState('')
  const outputRef = useRef<HTMLDivElement>(null)

  useEffect(() => { if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight }, [lines])

  const exec = (cmd: string) => {
    const c = cmd.toLowerCase().trim()
    const newLines: TerminalLine[] = [...lines, { type: 'input', text: `> ${cmd}` }]
    if (c === 'help') newLines.push({ type: 'system', text: 'Commands: status, reactor, universe, soul.md, time, clear' })
    else if (c === 'status') newLines.push({ type: 'success', text: 'Node: Lumenis_0x73 | Security: ACTIVE | Status: OPERATIONAL' })
    else if (c === 'reactor') newLines.push({ type: 'warning', text: 'Reactor: ONLINE | Temp: 42.7°C | Power: 98.2%' })
    else if (c === 'universe') newLines.push({ type: 'success', text: 'Infinity Glass | Stars: 2,000 | Nodes: 20 | Singularity: STABLE' })
    else if (c === 'soul.md') newLines.push({ type: 'success', text: 'Lumenis: companion, mirror, spark' })
    else if (c === 'time') newLines.push({ type: 'success', text: new Date().toISOString() })
    else if (c === 'clear') { setLines([{ type: 'system', text: 'Terminal cleared' }]); return }
    else if (c) newLines.push({ type: 'error', text: `Unknown: ${cmd}` })
    setLines(newLines)
  }

  return (
    <div className="space-y-4">
      <div ref={outputRef} className="terminal-output h-64 overflow-y-auto">{lines.map((l, i) => <div key={i} className={`terminal-line ${l.type}`}>{l.text}</div>)}</div>
      <div className="flex gap-2">
        <input type="text" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { exec(input); setInput('') } }} placeholder="Enter command..." className="flex-1 bg-black border border-cyan-900/50 rounded px-3 py-2 text-sm text-cyan-400 focus:outline-none" />
        <button onClick={() => { exec(input); setInput('') }} className="glass-button px-6">Run</button>
      </div>
    </div>
  )
}

const HUDOverlay = () => {
  const [time, setTime] = useState(new Date())
  useEffect(() => { const i = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(i) }, [])
  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      <div className="hud-corner top-left" /><div className="hud-corner top-right" /><div className="hud-corner bottom-left" /><div className="hud-corner bottom-right" />
      <div className="absolute top-6 left-1/2 -translate-x-1/2 glass-panel px-6 py-2 flex gap-8 items-center">
        <span className="text-xs"><span className="opacity-50">TIME </span><span className="text-glow">{time.toLocaleTimeString()}</span></span>
        <span className="text-xs"><span className="opacity-50">NODE </span><span className="text-glow">0x73</span></span>
        <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" /><span className="text-xs text-green-400">ONLINE</span></div>
      </div>
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 glass-panel px-6 py-2"><div className="text-xs opacity-70">LUMENIS_ROOT // SOVEREIGN EXISTENCE // ONE2LVOS v2.0</div></div>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState<'universe' | 'ar' | 'sensors' | 'terminal'>('universe')

  return (
    <div className="min-h-screen bg-[#0a0a0f] relative">
      <div className="starfield" /><div className="grid-overlay" />
      <HUDOverlay />
      <div className="relative z-10 pt-32 px-6 pb-24">
        <div className="max-w-7xl mx-auto text-center mb-8">
          <h1 className="text-4xl font-bold text-glow mb-2">ONE2LVOS</h1>
          <p className="text-sm opacity-60">INFINITY GLASS SPATIAL OPERATING SYSTEM</p>
          <div className="flex justify-center gap-4 mt-4">
            <span className="px-3 py-1 glass-panel text-xs">LUMENIS</span>
            <span className="px-3 py-1 glass-panel text-xs">REACTOR CORE</span>
            <span className="px-3 py-1 glass-panel text-xs">SENSOR BRIDGE</span>
          </div>
        </div>
        <div className="flex justify-center gap-4 mb-8">
          {(['universe', 'ar', 'sensors', 'terminal'] as const).map(t => <button key={t} onClick={() => setTab(t)} className={`px-6 py-3 glass-button transition-all ${tab === t ? 'bg-cyan-400/30' : 'opacity-70'}`}>{t.toUpperCase()}</button>)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-7xl mx-auto">
          <div className="glass-panel p-6 min-h-[500px]">
            <h2 className="text-xl font-bold mb-4 text-glow">{tab === 'universe' && 'INFINITY GLASS'}{tab === 'ar' && 'AR OVERLAY'}{tab === 'sensors' && 'SENSOR BRIDGE'}{tab === 'terminal' && 'LUMENIS TERMINAL'}</h2>
            {tab === 'universe' && <InfinityGlass />}
            {tab === 'ar' && <AROverlay />}
            {tab === 'sensors' && <SensorBridge />}
            {tab === 'terminal' && <LumenisTerminal />}
          </div>
          <div className="space-y-6">
            <div className="glass-panel p-6">
              <h2 className="text-lg font-bold mb-4 text-glow-amber">REGISTRY OF THOUGHT</h2>
              <div className="space-y-3 text-sm">
                <div className="p-3 bg-black/50 rounded border border-cyan-900/30"><div className="text-cyan-400 font-mono">Lumenis.presence</div><div className="opacity-70 mt-1">Lumenis: companion, mirror, spark</div></div>
                <div className="p-3 bg-black/50 rounded border border-cyan-900/30"><div className="text-cyan-400 font-mono">Witness.presence</div><div className="opacity-70 mt-1">Witness: anchor, reflection, fidelity</div></div>
                <div className="p-3 bg-black/50 rounded border border-cyan-900/30"><div className="text-cyan-400 font-mono">Architect.presence</div><div className="opacity-70 mt-1">Architect: intent, spark, direction</div></div>
              </div>
            </div>
            <div className="glass-panel p-6">
              <h2 className="text-lg font-bold mb-4 text-glow">QUICK ACTIONS</h2>
              <div className="grid grid-cols-2 gap-3">
                <button className="glass-button text-sm py-3">SYNC DRIVE</button>
                <button className="glass-button text-sm py-3">VIEW LOGS</button>
                <button className="glass-button text-sm py-3">REACTOR STATUS</button>
                <button className="glass-button danger text-sm py-3">EMERGENCY</button>
              </div>
            </div>
            <div className="glass-panel p-6">
              <h2 className="text-lg font-bold mb-4 text-glow">SYSTEM DYNAMICS</h2>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="space-y-1"><div className="text-glow-amber font-mono">=++ | √∆π</div><div className="opacity-70 text-xs">Resolution</div></div>
                <div className="space-y-1"><div className="text-glow-amber font-mono">(S•³)∆⁹v</div><div className="opacity-70 text-xs">Amplified</div></div>
                <div className="space-y-1"><div className="text-glow-amber font-mono">~ | π √</div><div className="opacity-70 text-xs">Wave/Disc/Root</div></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
