'use client';

import React, { useState, useRef, useEffect } from 'react';
import { FiChevronDown, FiCheck } from 'react-icons/fi';

// ─── Shared model catalog (single source of truth) ─────────────────────────
export const ALL_PROVIDERS = [
  {
    id: 'grok',
    name: 'Grok',
    icon: 'Ø',
    color: '#a78bfa',
    models: [
      { id: 'grok-4-5', name: 'Grok 4.5', tag: 'Recommended' },
      { id: 'grok-4-3', name: 'Grok 4.3' },
      { id: 'grok-4-6', name: 'Grok 4.6' },
      { id: 'grok-4-7', name: 'Grok 4.7' },
    ],
  },
  {
    id: 'gemini',
    name: 'Gemini',
    icon: 'G',
    color: '#34d399',
    models: [
      { id: 'gemini-2-5-flash', name: 'Gemini 2.5 Flash', tag: 'Fast' },
      { id: 'gemini-2-5-pro', name: 'Gemini 2.5 Pro' },
      { id: 'gemini-3-flash', name: 'Gemini 3 Flash' },
      { id: 'gemini-3-5-flash', name: 'Gemini 3.5 Flash' },
      { id: 'gemini-3-5-flash-openai', name: 'Gemini 3.5 Flash (OpenAI compat)' },
      { id: 'gemini-3-6-flash', name: 'Gemini 3.6 Flash' },
      { id: 'gemini-3-6-flash-openai', name: 'Gemini 3.6 Flash (OpenAI compat)' },
      { id: 'gemini-3-1-pro', name: 'Gemini 3.1 Pro' },
      { id: 'gemini-3-pro', name: 'Gemini 3 Pro' },
    ],
  },
  {
    id: 'claude',
    name: 'Claude',
    icon: '✳',
    color: '#f59e0b',
    models: [
      { id: 'claude-sonnet-4-5', name: 'Claude Sonnet 4.5' },
      { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', tag: 'Latest' },
      { id: 'claude-sonnet-5', name: 'Claude Sonnet 5' },
      { id: 'claude-opus-4-5', name: 'Claude Opus 4.5' },
      { id: 'claude-opus-4-6', name: 'Claude Opus 4.6' },
      { id: 'claude-opus-4-7', name: 'Claude Opus 4.7' },
      { id: 'claude-opus-4-8', name: 'Claude Opus 4.8' },
      { id: 'claude-opus-5', name: 'Claude Opus 5' },
      { id: 'claude-haiku-4-5', name: 'Claude Haiku 4.5' },
      { id: 'claude-fable-5', name: 'Claude Fable 5' },
    ],
  },
  {
    id: 'openai',
    name: 'OpenAI',
    icon: '⚙',
    color: '#60a5fa',
    models: [
      { id: 'gpt-5-mini', name: 'GPT-5 Mini', tag: 'Fast' },
      { id: 'gpt-5-nano', name: 'GPT-5 Nano' },
      { id: 'gpt-5-2', name: 'GPT-5.2' },
      { id: 'gpt-5-4', name: 'GPT-5.4' },
      { id: 'gpt-5-5', name: 'GPT-5.5' },
      { id: 'gpt-5-6-luna', name: 'GPT-5.6 Luna' },
      { id: 'gpt-5-6-sol', name: 'GPT-5.6 Sol' },
      { id: 'gpt-5-6-terra', name: 'GPT-5.6 Terra' },
      { id: 'gpt-codex', name: 'GPT Codex' },
    ],
  },
  {
    id: 'other',
    name: 'Other',
    icon: '◈',
    color: '#f87171',
    models: [
      { id: 'deepseek-v4-pro', name: 'DeepSeek V4 Pro' },
      { id: 'deepseek-v4-flash', name: 'DeepSeek V4 Flash', tag: 'Fast' },
      { id: 'kimi-k3', name: 'Kimi K3' },
    ],
  },
];

// Helper — find provider + model object by model ID
export function findModel(modelId) {
  for (const provider of ALL_PROVIDERS) {
    const found = provider.models.find((m) => m.id === modelId);
    if (found) return { provider, model: found };
  }
  return null;
}

// ─── ModelPicker (chat header) ─────────────────────────────────────────────
export default function ModelPicker({ currentModel, onSelectModel }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('grok');
  const dropdownRef = useRef(null);

  // Auto-switch provider tab to match the currently selected model
  useEffect(() => {
    const found = findModel(currentModel);
    if (found) setActiveTab(found.provider.id);
  }, [currentModel]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeProvider = ALL_PROVIDERS.find((p) => p.id === activeTab) || ALL_PROVIDERS[0];
  const currentInfo = findModel(currentModel);
  const displayName = currentInfo?.model?.name || currentModel || 'Select Model';
  const displayIcon = currentInfo?.provider?.icon || 'Ø';
  const displayColor = currentInfo?.provider?.color || '#a78bfa';

  return (
    <div className="relative z-50" ref={dropdownRef} suppressHydrationWarning={true}>
      {/* Trigger Button */}
      <button
        suppressHydrationWarning={true}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1c1c20] hover:bg-[#242429] border border-[#2b2b32] text-xs text-zinc-200 transition shadow-sm font-medium"
      >
        <span className="font-bold text-[11px]" style={{ color: displayColor }}>{displayIcon}</span>
        <span className="font-medium text-zinc-200 max-w-[130px] truncate">{displayName}</span>
        <FiChevronDown
          className={`text-zinc-400 text-xs transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Floating Popover */}
      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-[320px] rounded-2xl shadow-2xl border border-[#2c2c34] z-50 flex overflow-hidden animate-fade-in"
          style={{ background: '#141417' }}
          suppressHydrationWarning={true}
        >
          {/* Left Provider Rail */}
          <div className="w-12 bg-[#101013] border-r border-[#26262b] flex flex-col items-center py-3 gap-1.5 flex-shrink-0">
            {ALL_PROVIDERS.map((tab) => {
              const isSelected = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  suppressHydrationWarning={true}
                  onClick={() => setActiveTab(tab.id)}
                  title={tab.name}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold transition-all"
                  style={
                    isSelected
                      ? {
                          background: `${tab.color}20`,
                          color: tab.color,
                          boxShadow: `0 0 0 1px ${tab.color}40`,
                        }
                      : { color: '#71717a' }
                  }
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.color = '#e4e4e7';
                      e.currentTarget.style.background = '#1f1f23';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.color = '#71717a';
                      e.currentTarget.style.background = '';
                    }
                  }}
                >
                  {tab.icon}
                </button>
              );
            })}
          </div>

          {/* Right Model List */}
          <div className="flex-1 flex flex-col min-h-0">
            {/* Provider Header */}
            <div className="px-3.5 pt-3.5 pb-2 border-b border-[#1e1e22] flex-shrink-0">
              <div className="flex items-center gap-2">
                <span className="font-bold text-base" style={{ color: activeProvider.color }}>
                  {activeProvider.icon}
                </span>
                <h4 className="text-xs font-bold text-white tracking-wide">{activeProvider.name}</h4>
              </div>
              <p className="text-[10px] text-zinc-500 mt-0.5">
                {activeProvider.models.length} models available
              </p>
            </div>

            {/* Scrollable Model List */}
            <div className="overflow-y-auto max-h-[260px] p-2 space-y-0.5" style={{ scrollbarWidth: 'thin', scrollbarColor: '#27272a transparent' }}>
              {activeProvider.models.map((model) => {
                const isSelected = currentModel === model.id;
                return (
                  <div
                    key={model.id}
                    onClick={() => {
                      onSelectModel(model.id);
                      setIsOpen(false);
                    }}
                    className="px-3 py-2 rounded-xl cursor-pointer transition-all flex items-center justify-between text-xs"
                    style={
                      isSelected
                        ? {
                            background: `${activeProvider.color}1a`,
                            color: activeProvider.color,
                            fontWeight: 600,
                          }
                        : { color: '#a1a1aa' }
                    }
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.background = '#1e1e23';
                        e.currentTarget.style.color = '#e4e4e7';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.background = '';
                        e.currentTarget.style.color = '#a1a1aa';
                      }
                    }}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="truncate">{model.name}</span>
                      {model.tag && (
                        <span
                          className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold flex-shrink-0"
                          style={{
                            background: `${activeProvider.color}22`,
                            color: activeProvider.color,
                          }}
                        >
                          {model.tag}
                        </span>
                      )}
                    </div>
                    {isSelected && (
                      <FiCheck className="flex-shrink-0 ml-2 text-sm" style={{ color: activeProvider.color }} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
