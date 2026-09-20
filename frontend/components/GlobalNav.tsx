'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/navigation';
import { usePathname } from 'next/navigation';
import { Search, Database, Layers, Sparkles, BookOpen, Compass, Info } from 'lucide-react';
import { getHealthStatus } from '../lib/api';

export default function GlobalNav() {
  const pathname = usePathname();
  const [systemOnline, setSystemOnline] = useState<boolean>(true);

  useEffect(() => {
    getHealthStatus()
      .then((h) => setSystemOnline(h?.status === 'ok'))
      .catch(() => setSystemOnline(false));
  }, []);

  const navLinks = [
    { href: '/explore', label: 'Explore', icon: Compass },
    { href: '/connections', label: 'Connections', icon: Layers },
    { href: '/collections', label: 'Collections', icon: BookOpen },
    { href: '/about', label: 'About', icon: Info },
  ];

  return (
    <header
      style={{
        borderBottom: '1px solid var(--color-paper-border)',
        backgroundColor: 'var(--color-paper-base)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div
        className="container-research"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          height: '68px',
        }}
      >
        {/* Brand Masthead */}
        <a
          href="/"
          style={{
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'baseline',
            gap: '0.6rem',
          }}
        >
          <span
            className="font-display"
            style={{
              fontSize: '1.5rem',
              fontWeight: 600,
              letterSpacing: '0.04em',
              color: 'var(--color-ink-primary)',
              textTransform: 'uppercase',
            }}
          >
            The Intelligent Archive
          </span>
          <span
            style={{
              fontSize: '0.75rem',
              color: 'var(--color-ink-muted)',
              fontStyle: 'italic',
              fontFamily: 'Cormorant Garamond, serif',
            }}
          >
            Connected Memory
          </span>
        </a>

        {/* Primary Navigation Links */}
        <nav style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {navLinks.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <a
                key={item.href}
                href={item.href}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.45rem 0.85rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.875rem',
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? 'var(--color-accent-oxblood)' : 'var(--color-ink-secondary)',
                  backgroundColor: isActive ? 'var(--color-accent-oxblood-subtle)' : 'transparent',
                  textDecoration: 'none',
                  transition: 'all 0.15s ease',
                }}
              >
                <Icon size={15} color={isActive ? 'var(--color-accent-oxblood)' : 'var(--color-ink-muted)'} />
                {item.label}
              </a>
            );
          })}
        </nav>

        {/* Quick Search & System Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <a
            href="/explore"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.6rem',
              padding: '0.45rem 0.9rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-paper-border)',
              backgroundColor: 'var(--color-paper-surface)',
              color: 'var(--color-ink-muted)',
              fontSize: '0.8rem',
              textDecoration: 'none',
              cursor: 'pointer',
            }}
          >
            <Search size={14} />
            <span>Search archive...</span>
            <kbd
              style={{
                background: 'var(--color-paper-elevated)',
                padding: '0.1rem 0.35rem',
                borderRadius: '3px',
                fontSize: '0.7rem',
                fontFamily: 'monospace',
                border: '1px solid var(--color-paper-border)',
              }}
            >
              ⌘K
            </kbd>
          </a>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.75rem',
              color: systemOnline ? 'var(--color-ink-secondary)' : 'var(--color-accent-oxblood)',
              borderLeft: '1px solid var(--color-paper-border)',
              paddingLeft: '0.8rem',
            }}
            title="PostgreSQL 16 & pgvector Live Engine"
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: systemOnline ? '#2D8A4E' : '#C53030',
                display: 'inline-block',
              }}
            />
            <span>{systemOnline ? 'Archive Live' : 'Connecting'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
