"use client";

import React, { useState, useEffect, useRef } from "react";
import { FiX, FiCheck, FiEye, FiEyeOff, FiChevronDown } from "react-icons/fi";
import { fetchSettings, saveSettings } from "../lib/api";
import { ALL_PROVIDERS, findModel } from "./ModelPicker";

export default function AppSettingsDrawer({
  isOpen,
  onClose,
  currentModel,
  onUpdateDefaultModel,
  onProfileUpdate,
}) {
  const [userName, setUserName] = useState("");
  const [userEmail, setUserEmail] = useState("");

  // MUAPI Connection Credentials
  const [muapiApiKey, setMuapiApiKey] = useState("");
  const [muapiBaseUrl, setMuapiBaseUrl] = useState(
    "https://api.muapi.ai/api/v1",
  );
  const [composioApiKey, setComposioApiKey] = useState("");
  const [defaultModel, setDefaultModel] = useState("grok-4-5");
  const [showApiKey, setShowApiKey] = useState(false);
  const [showComposioKey, setShowComposioKey] = useState(false);
  const [modelDropOpen, setModelDropOpen] = useState(false);
  const modelDropRef = useRef(null);
  const [activeProvTab, setActiveProvTab] = useState("grok");

  const [savedField, setSavedField] = useState(null);

  useEffect(() => {
    if (isOpen) {
      // Load saved user profile
      const localName = localStorage.getItem("open_grok_user_name") || "";
      const localEmail = localStorage.getItem("open_grok_user_email") || "";

      setUserName(localName);
      setUserEmail(localEmail);

      // Load MUAPI settings from backend
      fetchSettings()
        .then((data) => {
          if (data) {
            setMuapiApiKey(data.muapi_api_key || "");
            setMuapiBaseUrl(
              data.muapi_base_url || "https://api.muapi.ai/api/v1",
            );
            setComposioApiKey(data.composio_api_key || "");
            setDefaultModel(data.default_model || "grok-4-5");
          }
        })
        .catch(console.error);
    }
  }, [isOpen]);

  // Close model dropdown when clicking outside
  useEffect(() => {
    function handleOutside(e) {
      if (modelDropRef.current && !modelDropRef.current.contains(e.target)) {
        setModelDropOpen(false);
      }
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  // Auto-switch provider tab when defaultModel changes
  useEffect(() => {
    const found = findModel(defaultModel);
    if (found) setActiveProvTab(found.provider.id);
  }, [defaultModel]);

  // Sync from external model change (e.g. chat header ModelPicker)
  useEffect(() => {
    if (currentModel && currentModel !== defaultModel) {
      setDefaultModel(currentModel);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentModel]);

  if (!isOpen) return null;

  const triggerSavedNotice = (field) => {
    setSavedField(field);
    setTimeout(() => setSavedField(null), 1500);
  };

  const handleSaveMuapiSettings = async (field = "muapi") => {
    try {
      await saveSettings({
        muapi_api_key: muapiApiKey,
        muapi_base_url: muapiBaseUrl,
        composio_api_key: composioApiKey,
        default_model: defaultModel,
        theme: "dark",
      });
      if (onUpdateDefaultModel && typeof onUpdateDefaultModel === "function") {
        onUpdateDefaultModel(defaultModel);
      }
      triggerSavedNotice(field);
    } catch (err) {
      console.error("Failed to save settings:", err);
    }
  };

  return (
    <aside className="w-96 md:w-[420px] h-screen bg-[#111113] border-l border-[#1c1c20] flex flex-col z-30 shadow-2xl animate-fade-in select-none font-sans text-zinc-100 flex-shrink-0">
      {/* Drawer Header */}
      <div className="p-5 border-b border-[#1c1c20] flex items-center justify-between">
        <h2 className="text-sm font-bold text-zinc-100 tracking-wide">
          App Settings
        </h2>
        <button
          suppressHydrationWarning={true}
          onClick={onClose}
          className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-[#1c1c20] transition"
          title="Close App Settings"
        >
          <FiX className="text-base" />
        </button>
      </div>

      {/* Drawer Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* Profile Card Section */}
        <div className="bg-[#18181b] border border-[#27272a] rounded-2xl p-5 space-y-4 shadow-sm">
          <div>
            <h3 className="text-sm font-bold text-zinc-100">Profile</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Shown in the sidebar. Saved as you go.
            </p>
          </div>

          <div className="space-y-3">
            <input
              suppressHydrationWarning={true}
              type="text"
              value={userName}
              onChange={(e) => {
                setUserName(e.target.value);
                localStorage.setItem("open_grok_user_name", e.target.value);
                if (onProfileUpdate) onProfileUpdate(e.target.value);
              }}
              placeholder="Your name"
              className="w-full bg-[#222226] border border-[#2e2e34] rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-400 transition font-sans"
            />

            <input
              suppressHydrationWarning={true}
              type="email"
              value={userEmail}
              onChange={(e) => {
                setUserEmail(e.target.value);
                localStorage.setItem("open_grok_user_email", e.target.value);
              }}
              placeholder="you@example.com"
              className="w-full bg-[#222226] border border-[#2e2e34] rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-400 transition font-sans"
            />
          </div>
        </div>

        {/* Connections Card Section */}
        <div className="bg-[#18181b] border border-[#27272a] rounded-2xl p-5 space-y-5 shadow-sm">
          <div>
            <h3 className="text-sm font-bold text-zinc-100">Connections</h3>
            <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
              Shared by all bots. Keys are stored locally and masked by default.
            </p>
          </div>

          {/* MUAPI API Key */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
              <span className="text-amber-400">•</span> MUAPI API Key
            </label>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  suppressHydrationWarning={true}
                  type={showApiKey ? "text" : "password"}
                  value={muapiApiKey}
                  onChange={(e) => setMuapiApiKey(e.target.value)}
                  placeholder="Paste MUAPI API Key..."
                  className="w-full bg-[#222226] border border-[#2e2e34] rounded-xl pl-3.5 pr-8 py-2.5 text-xs text-zinc-200 font-mono placeholder-zinc-500 focus:outline-none focus:border-zinc-400 transition"
                />
                <button
                  suppressHydrationWarning={true}
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition text-xs"
                >
                  {showApiKey ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
              <button
                suppressHydrationWarning={true}
                type="button"
                onClick={() => handleSaveMuapiSettings("muapi_key")}
                className="px-3.5 py-2.5 rounded-xl border border-[#33333a] bg-[#222226] hover:bg-[#2c2c34] text-xs font-medium text-zinc-300 hover:text-white transition flex items-center gap-1 flex-shrink-0"
              >
                <FiCheck
                  className={
                    savedField === "muapi_key"
                      ? "text-emerald-400"
                      : "text-zinc-400"
                  }
                />
                <span>{savedField === "muapi_key" ? "Saved" : "Save"}</span>
              </button>
            </div>
          </div>

          {/* Composio API Key */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
              <span className="text-cyan-400">•</span> Composio API Key
            </label>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  suppressHydrationWarning={true}
                  type={showComposioKey ? "text" : "password"}
                  value={composioApiKey}
                  onChange={(e) => setComposioApiKey(e.target.value)}
                  placeholder="Optional connector key..."
                  className="w-full bg-[#222226] border border-[#2e2e34] rounded-xl pl-3.5 pr-8 py-2.5 text-xs text-zinc-200 font-mono placeholder-zinc-500 focus:outline-none focus:border-zinc-400 transition"
                />
                <button
                  suppressHydrationWarning={true}
                  type="button"
                  onClick={() => setShowComposioKey(!showComposioKey)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition text-xs"
                  title={showComposioKey ? "Hide Composio key" : "Show Composio key"}
                >
                  {showComposioKey ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
              <button
                suppressHydrationWarning={true}
                type="button"
                onClick={() => handleSaveMuapiSettings("composio_key")}
                className="px-3.5 py-2.5 rounded-xl border border-[#33333a] bg-[#222226] hover:bg-[#2c2c34] text-xs font-medium text-zinc-300 hover:text-white transition flex items-center gap-1 flex-shrink-0"
              >
                <FiCheck
                  className={
                    savedField === "composio_key"
                      ? "text-emerald-400"
                      : "text-zinc-400"
                  }
                />
                <span>{savedField === "composio_key" ? "Saved" : "Save"}</span>
              </button>
            </div>
            <p className="text-[10px] leading-relaxed text-zinc-500">
              Enables live connector catalog and OAuth links in Marketplace. Leave blank to use the curated catalog only.
            </p>
          </div>

          {/* Default LLM Model — custom dropdown */}
          <div className="space-y-1.5" ref={modelDropRef}>
            <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
              <span className="text-purple-400">•</span> Default LLM Model
            </label>
            <div className="flex items-center gap-2">
              {/* Custom Dropdown Trigger */}
              <div className="relative flex-1">
                <button
                  suppressHydrationWarning={true}
                  type="button"
                  onClick={() => setModelDropOpen((v) => !v)}
                  className="w-full flex items-center justify-between bg-[#222226] border border-[#2e2e34] rounded-xl px-3.5 py-2.5 text-xs text-zinc-200 focus:outline-none focus:border-zinc-400 transition cursor-pointer font-sans"
                >
                  <div className="flex items-center gap-2">
                    {(() => {
                      const info = findModel(defaultModel);
                      return (
                        <>
                          <span
                            className="font-bold text-[11px]"
                            style={{
                              color: info?.provider?.color || "#a78bfa",
                            }}
                          >
                            {info?.provider?.icon || "Ø"}
                          </span>
                          <span className="truncate">
                            {info?.model?.name || defaultModel}
                          </span>
                        </>
                      );
                    })()}
                  </div>
                  <FiChevronDown
                    className={`text-zinc-400 transition-transform duration-200 ${modelDropOpen ? "rotate-180" : ""}`}
                  />
                </button>

                {/* Dropdown Popover */}
                {modelDropOpen && (
                  <div
                    className="absolute bottom-full mb-2 left-0 right-0 rounded-2xl shadow-2xl border border-[#2c2c34] z-50 flex overflow-hidden animate-fade-in"
                    style={{ background: "#141417" }}
                    suppressHydrationWarning={true}
                  >
                    {/* Provider Rail */}
                    <div className="w-11 bg-[#101013] border-r border-[#26262b] flex flex-col items-center py-2.5 gap-1 flex-shrink-0">
                      {ALL_PROVIDERS.map((prov) => {
                        const isSel = activeProvTab === prov.id;
                        return (
                          <button
                            key={prov.id}
                            suppressHydrationWarning={true}
                            type="button"
                            onClick={() => setActiveProvTab(prov.id)}
                            title={prov.name}
                            className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold transition-all"
                            style={
                              isSel
                                ? {
                                    background: `${prov.color}20`,
                                    color: prov.color,
                                    boxShadow: `0 0 0 1px ${prov.color}40`,
                                  }
                                : { color: "#71717a" }
                            }
                          >
                            {prov.icon}
                          </button>
                        );
                      })}
                    </div>

                    {/* Model List */}
                    <div className="flex-1 flex flex-col min-h-0">
                      {(() => {
                        const activeProv =
                          ALL_PROVIDERS.find((p) => p.id === activeProvTab) ||
                          ALL_PROVIDERS[0];
                        return (
                          <>
                            <div className="px-3 pt-3 pb-2 border-b border-[#1e1e22] flex-shrink-0">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className="font-bold text-sm"
                                  style={{ color: activeProv.color }}
                                >
                                  {activeProv.icon}
                                </span>
                                <span className="text-xs font-bold text-white">
                                  {activeProv.name}
                                </span>
                              </div>
                              <p className="text-[10px] text-zinc-500 mt-0.5">
                                {activeProv.models.length} models
                              </p>
                            </div>
                            <div
                              className="overflow-y-auto max-h-[200px] p-1.5 space-y-0.5"
                              style={{
                                scrollbarWidth: "thin",
                                scrollbarColor: "#27272a transparent",
                              }}
                            >
                              {activeProv.models.map((model) => {
                                const isCurrent = defaultModel === model.id;
                                return (
                                  <div
                                    key={model.id}
                                    onClick={() => {
                                      setDefaultModel(model.id);
                                      setModelDropOpen(false);
                                    }}
                                    className="px-2.5 py-1.5 rounded-lg cursor-pointer transition-all flex items-center justify-between text-[11px]"
                                    style={
                                      isCurrent
                                        ? {
                                            background: `${activeProv.color}1a`,
                                            color: activeProv.color,
                                            fontWeight: 600,
                                          }
                                        : { color: "#a1a1aa" }
                                    }
                                    onMouseEnter={(e) => {
                                      if (!isCurrent) {
                                        e.currentTarget.style.background =
                                          "#1e1e23";
                                        e.currentTarget.style.color = "#e4e4e7";
                                      }
                                    }}
                                    onMouseLeave={(e) => {
                                      if (!isCurrent) {
                                        e.currentTarget.style.background = "";
                                        e.currentTarget.style.color = "#a1a1aa";
                                      }
                                    }}
                                  >
                                    <div className="flex items-center gap-1.5 min-w-0">
                                      <span className="truncate">
                                        {model.name}
                                      </span>
                                      {model.tag && (
                                        <span
                                          className="text-[9px] px-1 py-0.5 rounded-full font-semibold flex-shrink-0"
                                          style={{
                                            background: `${activeProv.color}22`,
                                            color: activeProv.color,
                                          }}
                                        >
                                          {model.tag}
                                        </span>
                                      )}
                                    </div>
                                    {isCurrent && (
                                      <FiCheck
                                        className="flex-shrink-0 ml-1 text-xs"
                                        style={{ color: activeProv.color }}
                                      />
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}
              </div>

              <button
                suppressHydrationWarning={true}
                type="button"
                onClick={() => handleSaveMuapiSettings("muapi_model")}
                className="px-3.5 py-2.5 rounded-xl border border-[#33333a] bg-[#222226] hover:bg-[#2c2c34] text-xs font-medium text-zinc-300 hover:text-white transition flex items-center gap-1 flex-shrink-0"
              >
                <FiCheck
                  className={
                    savedField === "muapi_model"
                      ? "text-emerald-400"
                      : "text-zinc-400"
                  }
                />
                <span>{savedField === "muapi_model" ? "Saved" : "Save"}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
