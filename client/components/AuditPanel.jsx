'use client';

import React, { useEffect, useState } from 'react';
import { FiAlertCircle, FiClock, FiRefreshCw, FiShield } from 'react-icons/fi';
import { fetchAuditEvents } from '../lib/api';

function formatTimestamp(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function eventTone(event) {
  if (event.includes('failed') || event.includes('denied') || event.includes('expired')) {
    return 'text-rose-300 bg-rose-500/10 border-rose-500/20';
  }
  if (event.includes('completed') || event.includes('allow')) {
    return 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20';
  }
  return 'text-blue-300 bg-blue-500/10 border-blue-500/20';
}

export default function AuditPanel() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadEvents = async () => {
    setLoading(true);
    setError('');
    try {
      setEvents(await fetchAuditEvents(200));
    } catch (err) {
      setError(err.message || 'Could not load audit events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const recentEvents = [...events].reverse();

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-[#09090b] font-sans text-zinc-100">
      <div className="px-6 py-4 border-b border-[#18181c] flex items-center justify-between flex-shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <FiShield className="text-cyan-400" />
            <h2 className="text-sm font-bold tracking-wide">Audit Trail</h2>
          </div>
          <p className="text-[11px] text-zinc-500 mt-0.5">
            Local record of approvals, workspace tools, and connector actions.
          </p>
        </div>
        <button
          type="button"
          onClick={loadEvents}
          className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-[#1e1e22] transition"
          title="Refresh audit trail"
        >
          <FiRefreshCw className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {error && (
        <div className="mx-6 mt-4 rounded-xl border border-rose-500/20 bg-rose-500/[0.07] px-4 py-3 text-xs text-rose-300 flex items-center gap-2">
          <FiAlertCircle /> {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        {loading && events.length === 0 ? (
          <div className="py-16 text-center text-sm text-zinc-600">Loading audit events…</div>
        ) : recentEvents.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[#27272a] py-16 text-center">
            <FiClock className="mx-auto text-2xl text-zinc-700" />
            <p className="mt-3 text-sm text-zinc-500">No audit events yet.</p>
            <p className="mt-1 text-xs text-zinc-600">Approved workspace actions will appear here.</p>
          </div>
        ) : (
          <div className="rounded-2xl border border-[#1e1e22] overflow-hidden">
            {recentEvents.map((item, index) => {
              const event = item.event || item.type || 'event';
              return (
                <div
                  key={`${item.created_at || 'event'}-${item.request_id || item.connector || index}`}
                  className={`px-4 py-3.5 ${index > 0 ? 'border-t border-[#1a1a1e]' : ''} bg-[#0d0d10]`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${eventTone(event)}`}>
                          {event}
                        </span>
                        {item.tool && <span className="text-xs text-zinc-300 truncate">{item.tool}</span>}
                        {item.connector && <span className="text-xs text-zinc-300 truncate">{item.connector}</span>}
                      </div>
                      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-zinc-600">
                        {item.request_id && <span>request: {item.request_id}</span>}
                        {item.thread_id && <span>thread: {item.thread_id}</span>}
                        {typeof item.removed === 'number' && <span>removed: {item.removed}</span>}
                      </div>
                    </div>
                    <time className="flex-shrink-0 text-[10px] text-zinc-600">{formatTimestamp(item.created_at)}</time>
                  </div>
                  {item.error && <p className="mt-2 text-[11px] text-rose-300">{item.error}</p>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
