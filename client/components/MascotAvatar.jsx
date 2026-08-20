'use client';

import React from 'react';

export default function MascotAvatar({ type = 'blue', size = 'md', className = '' }) {
  const sizeClasses = {
    sm: 'w-7 h-7 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
  };

  const currentSize = sizeClasses[size] || sizeClasses.md;

  if (type === 'warning' || type === 'alert') {
    return (
      <div
        className={`${currentSize} rounded-xl bg-[#222226] border border-[#2e2e34] flex items-center justify-center flex-shrink-0 shadow-inner ${className}`}
      >
        <span className="text-amber-500 font-extrabold text-lg leading-none font-mono">!</span>
      </div>
    );
  }

  if (type === 'pink') {
    return (
      <div className={`${currentSize} flex items-center justify-center flex-shrink-0 ${className}`}>
        <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-md">
          <defs>
            <linearGradient id="pinkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f43f5e" />
              <stop offset="100%" stopColor="#be123c" />
            </linearGradient>
          </defs>
          {/* Triangular blob shape with rounded corners */}
          <path
            d="M 50 12 C 60 12, 88 65, 84 76 C 80 87, 20 87, 16 76 C 12 65, 40 12, 50 12 Z"
            fill="url(#pinkGrad)"
          />
          {/* Left Eye */}
          <circle cx="43" cy="52" r="7" fill="#ffffff" />
          <circle cx="41" cy="52" r="3.5" fill="#0f172a" />
          <circle cx="40" cy="50" r="1.2" fill="#ffffff" />
          {/* Right Eye */}
          <circle cx="62" cy="54" r="6" fill="#ffffff" />
          <circle cx="60" cy="54" r="3" fill="#0f172a" />
          <circle cx="59" cy="53" r="1" fill="#ffffff" />
        </svg>
      </div>
    );
  }

  // Default: Blue mascot avatar
  return (
    <div className={`${currentSize} flex items-center justify-center flex-shrink-0 ${className}`}>
      <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-md">
        <defs>
          <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#1d4ed8" />
          </linearGradient>
        </defs>
        {/* Triangular blob shape with rounded corners */}
        <path
          d="M 50 12 C 60 12, 88 65, 84 76 C 80 87, 20 87, 16 76 C 12 65, 40 12, 50 12 Z"
          fill="url(#blueGrad)"
        />
        {/* Left Eye */}
        <circle cx="43" cy="52" r="7" fill="#ffffff" />
        <circle cx="41" cy="52" r="3.5" fill="#0f172a" />
        <circle cx="40" cy="50" r="1.2" fill="#ffffff" />
        {/* Right Eye */}
        <circle cx="62" cy="54" r="6" fill="#ffffff" />
        <circle cx="60" cy="54" r="3" fill="#0f172a" />
        <circle cx="59" cy="53" r="1" fill="#ffffff" />
      </svg>
    </div>
  );
}
