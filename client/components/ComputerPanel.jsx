'use client';

import React, { useState } from 'react';
import { 
  FiMonitor, 
  FiPlay, 
  FiPause, 
  FiRefreshCw, 
  FiExternalLink, 
  FiTerminal, 
  FiCpu, 
  FiHardDrive,
  FiActivity
} from 'react-icons/fi';

export default function ComputerPanel({ bot, onBackToChat }) {
  const [isRunning, setIsRunning] = useState(true);
  const [activeTab, setActiveTab] = useState('preview'); // preview, logs


  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-slate-950/80 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between glass-panel p-4 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center text-xl">
            <FiMonitor />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              Agent Cloud Computer
              <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded font-mono border border-emerald-500/30 flex items-center gap-1">
                <FiActivity className="animate-pulse" /> Active
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Dedicated Linux Desktop box assigned to <span className="text-slate-200 font-semibold">{bot?.name || 'Agent'}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${
              isRunning
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/30 hover:bg-amber-500/30'
                : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/30'
            }`}
          >
            {isRunning ? <FiPause /> : <FiPlay />}
            <span>{isRunning ? 'Pause Machine' : 'Resume Machine'}</span>
          </button>
          <a
            href="https://box.ascii.dev"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/20 transition"
          >
            <span>Take Over (VNC)</span>
            <FiExternalLink />
          </a>
        </div>
      </div>

      {/* Screen Preview & Terminal */}
      <div className="flex-1 grid grid-cols-3 gap-6 min-h-0">
        {/* Computer Screen Stream */}
        <div className="col-span-2 glass-panel rounded-2xl border border-slate-800 flex flex-col overflow-hidden shadow-2xl relative">
          <div className="p-3 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              Live Display (1920x1080 @ 60FPS)
            </div>
              <span className="text-[10px] font-mono text-slate-500">Box ID: box-linux-01</span>
          </div>

          <div className="flex-1 bg-slate-950 flex flex-col items-center justify-center relative p-6">
            {/* Simulated Desktop Preview Graphic */}
            <div className="w-full h-full rounded-xl border border-slate-800/80 bg-gradient-to-br from-slate-900 via-slate-950 to-blue-950/40 p-4 flex flex-col justify-between shadow-2xl relative overflow-hidden">
              <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800/60 pb-2">
                <span className="font-mono text-cyan-400">Ubuntu 24.04 LTS — Agent Terminal</span>
                <span>CPU: 12% | RAM: 1.4 GB / 8.0 GB</span>
              </div>

              <div className="font-mono text-xs text-emerald-400 space-y-1 my-auto">
                <p className="text-slate-400">[open-grok-bot-harness] Connecting to agent cloud box...</p>
                <p>[system] Initializing Chrome browser & CUA driver interface</p>
                <p className="text-blue-400">$ pnpm run build --filter desktop</p>
                <p className="text-emerald-400">✓ Compiled successfully in 1.4s (314 modules)</p>
                <p className="text-amber-400">$ node server/index.js --port 8799</p>
                <p className="animate-pulse">_</p>
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-slate-800/60">
                <span>Composio OAuth: Connected</span>
                <span>Resolution: 1080p</span>
              </div>
            </div>
          </div>
        </div>

        {/* Machine Stats & Diagnostics */}
        <div className="space-y-4 flex flex-col">
          <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-3">
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <FiCpu className="text-blue-400" /> System Specs
            </h3>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between text-slate-400">
                <span>Provider:</span>
                <span className="text-slate-200 font-mono">Cloud Box (Linux)</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Architecture:</span>
                <span className="text-slate-200 font-mono">x86_64 / 4 vCPU</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Memory:</span>
                <span className="text-slate-200 font-mono">8 GB RAM</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Storage:</span>
                <span className="text-slate-200 font-mono">50 GB NVMe</span>
              </div>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-3 flex-1 flex flex-col">
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <FiTerminal className="text-purple-400" /> Active Processes
            </h3>

            <div className="flex-1 font-mono text-[11px] text-slate-400 bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5 overflow-y-auto">
              <div className="text-emerald-400 flex items-center justify-between">
                <span>python3 app/main.py</span>
                <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1 rounded">RUNNING</span>
              </div>
              <div className="text-blue-400 flex items-center justify-between">
                <span>node server/index.js</span>
                <span className="text-[9px] bg-blue-500/20 text-blue-400 px-1 rounded">LISTEN</span>
              </div>
              <div className="text-slate-400 flex items-center justify-between">
                <span>chrome --headless</span>
                <span className="text-[9px] bg-slate-800 text-slate-400 px-1 rounded">IDLE</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
