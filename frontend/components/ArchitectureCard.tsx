import React from 'react';

interface ArchitectureCardProps {
  phase: string;
  title: string;
  description: string;
  technologies: string[];
  status: 'completed' | 'active' | 'upcoming';
}

export default function ArchitectureCard({
  phase,
  title,
  description,
  technologies,
  status,
}: ArchitectureCardProps) {
  const getStatusBadge = () => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">Completed</span>;
      case 'active':
        return <span className="badge badge-info">Current Phase</span>;
      case 'upcoming':
        return <span className="badge badge-warning">Next Phase</span>;
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--accent-indigo)', textTransform: 'uppercase' }}>
            {phase}
          </span>
          {getStatusBadge()}
        </div>

        <h3 style={{ fontSize: '1.15rem', fontWeight: '700', marginBottom: '0.5rem' }}>{title}</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', lineHeight: '1.6' }}>
          {description}
        </p>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
        {technologies.map((tech) => (
          <span
            key={tech}
            style={{
              fontSize: '0.7rem',
              padding: '0.2rem 0.5rem',
              borderRadius: '4px',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            {tech}
          </span>
        ))}
      </div>
    </div>
  );
}
