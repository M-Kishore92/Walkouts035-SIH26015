import React from 'react';
import { Watershed } from '../types';

interface KPIRibbonProps {
  watersheds: Watershed[];
  totalLedgerBlocks: number;
}

export const KPIRibbon: React.FC<KPIRibbonProps> = ({ watersheds, totalLedgerBlocks }) => {
  // Aggregate KPIs
  const totalArea = watersheds.reduce((sum, w) => sum + w.area_ha, 0);
  const avgWii = watersheds.reduce((sum, w) => sum + w.current_wii, 0) / (watersheds.length || 1);
  const totalWaterGain = watersheds.reduce((sum, w) => sum + (w.water_current_ha - w.water_baseline_ha), 0);
  const totalDegradedReduction = watersheds.reduce((sum, w) => sum + (w.degraded_baseline_ha - w.degraded_current_ha), 0);
  const avgCorroboration = watersheds.reduce((sum, w) => sum + w.photo_corroboration_rate, 0) / (watersheds.length || 1);

  const kpis = [
    {
      title: 'District WII Index',
      value: avgWii.toFixed(1),
      subtitle: 'Cohort Benchmark (Nanded)',
      change: '+24.6% vs Baseline',
      changePositive: true,
      color: '#10b981',
      icon: '🌊',
      glow: 'rgba(16, 185, 129, 0.2)',
    },
    {
      title: 'Surface Water Extent',
      value: `+${totalWaterGain.toFixed(1)} ha`,
      subtitle: 'Permanent & Seasonal Storage',
      change: '+48.2% expansion',
      changePositive: true,
      color: '#06b6d4',
      icon: '💧',
      glow: 'rgba(6, 182, 212, 0.2)',
    },
    {
      title: 'Degraded Land Restored',
      value: `${totalDegradedReduction.toFixed(1)} ha`,
      subtitle: 'Treated via Trenches & Bunds',
      change: '-36.4% degraded area',
      changePositive: true,
      color: '#f59e0b',
      icon: '🌱',
      glow: 'rgba(245, 158, 11, 0.2)',
    },
    {
      title: 'DRISHTI Ground Truth',
      value: `${avgCorroboration.toFixed(1)}%`,
      subtitle: 'Photo-Corroborated Claims',
      change: '82 Geo-Photos Verified',
      changePositive: true,
      color: '#8b5cf6',
      icon: '📸',
      glow: 'rgba(139, 92, 246, 0.2)',
    },
    {
      title: 'Cryptographic Ledger',
      value: `#${totalLedgerBlocks} Blocks`,
      subtitle: 'Tamper-Evident SHA-256 Chain',
      change: '100% Chain Integrity',
      changePositive: true,
      color: '#38bdf8',
      icon: '🛡️',
      glow: 'rgba(56, 189, 248, 0.2)',
    },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
      gap: 16,
      marginBottom: 24,
    }}>
      {kpis.map((kpi, idx) => (
        <div
          key={idx}
          className="glass-panel"
          style={{
            padding: '20px 22px',
            position: 'relative',
            overflow: 'hidden',
            borderTop: `3px solid ${kpi.color}`,
          }}
        >
          <div style={{
            position: 'absolute',
            top: 14,
            right: 18,
            fontSize: '1.6rem',
            opacity: 0.85,
          }}>
            {kpi.icon}
          </div>
          <div style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
            {kpi.title}
          </div>
          <div style={{
            fontSize: '1.9rem',
            fontWeight: 800,
            color: '#f8fafc',
            marginTop: 4,
            letterSpacing: '-0.02em',
          }}>
            {kpi.value}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10, fontSize: '0.75rem' }}>
            <span style={{ color: '#64748b' }}>{kpi.subtitle}</span>
            <span style={{
              color: kpi.changePositive ? '#34d399' : '#f87171',
              fontWeight: 600,
              background: kpi.changePositive ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
              padding: '2px 8px',
              borderRadius: 6,
            }}>
              {kpi.change}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};
