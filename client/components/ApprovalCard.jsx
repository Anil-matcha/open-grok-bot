'use client';

import React, { useState } from 'react';
import { FiShield, FiTerminal, FiCheck, FiX, FiAlertTriangle } from 'react-icons/fi';

export default function ApprovalCard({ approval, onRespond }) {
  const [status, setStatus] = useState('pending'); // pending, allowed, denied
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleAction = async (action) => {
    setIsSubmitting(true);
    setError('');
    try {
      if (onRespond) {
        await onRespond(approval.requestId, action);
      }
      setStatus(action === 'allow' ? 'allowed' : 'denied');
    } catch (err) {
      setError(err?.message || 'Could not submit this decision.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="my-3 p-4 rounded-2xl glass-panel border border-amber-500/30 bg-slate-900/80 shadow-xl max-w-xl">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-3">
        <div className="flex items-center gap-2 text-amber-400">
          <FiShield className="text-lg animate-pulse" />
          <span className="text-xs font-bold uppercase tracking-wider">Permission Broker Request</span>
        </div>
        <span className="text-[10px] font-mono bg-amber-500/10 text-amber-300 px-2 py-0.5 rounded border border-amber-500/20">
          {approval.tool || 'terminal.execute'}
        </span>
      </div>

      <div className="flex items-start gap-3 my-2">
        <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-amber-400 border border-slate-700 flex-shrink-0">
          <FiTerminal className="text-base" />
        </div>
        <div>
          <p className="text-xs font-medium text-slate-200">{approval.summary}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Agent is requesting permission to execute an action on your environment.
          </p>
        </div>
      </div>

      {status === 'pending' ? (
        <div className="flex items-center justify-end gap-2 mt-4 pt-2 border-t border-slate-800/60">
          <button
            disabled={isSubmitting}
            onClick={() => handleAction('deny')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 border border-slate-700 hover:border-rose-500/40 text-xs font-semibold transition disabled:opacity-50"
          >
            <FiX className="text-sm" />
            <span>Deny</span>
          </button>
          <button
            disabled={isSubmitting}
            onClick={() => handleAction('allow')}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/30 transition disabled:opacity-50"
          >
            <FiCheck className="text-sm" />
            <span>Allow Execution</span>
          </button>
          {error && <span className="text-[10px] text-rose-400">{error}</span>}
        </div>
      ) : (
        <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-800/60 text-xs">
          <span className="text-slate-400">Status:</span>
          <span
            className={`font-semibold flex items-center gap-1 px-2 py-0.5 rounded ${
              status === 'allowed'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
            }`}
          >
            {status === 'allowed' ? <FiCheck /> : <FiX />}
            {status === 'allowed' ? 'Approved' : 'Denied'}
          </span>
        </div>
      )}
    </div>
  );
}
