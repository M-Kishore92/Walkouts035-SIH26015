import React from 'react';
import { Watershed, SatelliteEpoch } from '../types';

interface WIIScorecardProps {
  watershed: Watershed;
  epochs: SatelliteEpoch[];
}

export const WIIScorecard: React.FC<WIIScorecardProps> = ({ watershed, epochs }) => {
  // Breakdown calculations based on WII engine weights
  const ndviNorm = Math.min(1, Math.max(0, (watershed.ndvi_current - 0.20) / 0.40));
  const waterNorm = Math.min(1, Math.max(0, (watershed.water_current_ha - 10) / 70));
  const degradedNorm = 1 - Math.min(1, Math.max(0, (watershed.degraded_current_ha - 30) / 130));
  const photoNorm = watershed.photo_corroboration_rate / 100;

  const components = [
    { name: 'Vegetation Biomass (NDVI)', weight: 30, score: (ndviNorm * 100).toFixed(1), weighted: (0.30 * ndviNorm * 100).toFixed(1), color: '#10b981' },
    { name: 'Surface Water Extent (NDWI)', weight: 30, score: (waterNorm * 100).toFixed(1), weighted: (0.30 * waterNorm * 100).toFixed(1), color: '#06b6d4' },
    { name: 'Degraded Land Remediation', weight: 25, score: (degradedNorm * 100).toFixed(1), weighted: (0.25 * degradedNorm * 100).toFixed(1), color: '#f59e0b' },
    { name: 'DRISHTI Photo Corroboration', weight: 15, score: (photoNorm * 100).toFixed(1), weighted: (0.15 * photoNorm * 100).toFixed(1), color: '#8b5cf6' },
  ];

  return (
    <div className="glass-panel" style={{ padding: 24, marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
            Watershed Impact Index (WII) Mathematical Decomposition
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Pure functional evaluation according to MoRD-IWMP guidelines. Zero subjective bias.
          </p>
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: 8,
          background: 'rgba(16, 185, 129, 0.15)',
          padding: '6px 16px',
          borderRadius: 8,
          border: '1px solid rgba(16, 185, 129, 0.3)',
        }}>
          <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>COMPOSITE WII:</span>
          <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#10b981' }}>{watershed.current_wii}</span>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>/ 100</span>
        </div>
      </div>

      {/* Grid: Component Weights & Multi-Epoch Trendline */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1.2fr) minmax(340px, 1fr)', gap: 24 }}>
        {/* WII Formula Components Breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {components.map((c, i) => (
            <div key={i} style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 14, borderRadius: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: 6 }}>
                <span style={{ fontWeight: 600, color: '#f8fafc' }}>{c.name}</span>
                <span style={{ color: '#94a3b8' }}>
                  Weight: <strong style={{ color: '#fff' }}>{c.weight}%</strong> | Score: <strong style={{ color: c.color }}>{c.score}</strong>
                </span>
              </div>
              {/* Progress Bar */}
              <div style={{ height: 8, background: 'rgba(255, 255, 255, 0.08)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${c.score}%`,
                  background: c.color,
                  borderRadius: 4,
                  transition: 'width 0.5s ease',
                }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4, fontSize: '0.72rem', color: '#64748b' }}>
                Contribution: +{c.weighted} pts to total WII
              </div>
            </div>
          ))}
        </div>

        {/* Multi-Epoch Progression Timeline */}
        <div style={{
          background: 'rgba(0, 0, 0, 0.25)',
          padding: 18,
          borderRadius: 12,
          border: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', marginBottom: 4 }}>
              Multi-Epoch Trajectory (2022 - 2026)
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: 16 }}>
              6-Epoch longitudinal evaluation tracking restoration impact
            </div>
          </div>

          {/* SVG Trendline */}
          <div style={{ height: 160, position: 'relative' }}>
            <svg viewBox="0 0 360 140" style={{ width: '100%', height: '100%' }}>
              {/* Grid lines */}
              <line x1="0" y1="20" x2="360" y2="20" stroke="rgba(255,255,255,0.06)" strokeDasharray="3,3" />
              <line x1="0" y1="70" x2="360" y2="70" stroke="rgba(255,255,255,0.06)" strokeDasharray="3,3" />
              <line x1="0" y1="120" x2="360" y2="120" stroke="rgba(255,255,255,0.06)" strokeDasharray="3,3" />

              {/* Area gradient under curve */}
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Path calculation */}
              {(() => {
                const points = epochs.map((e, idx) => {
                  const x = (idx / (epochs.length - 1)) * 340 + 10;
                  const y = 130 - (e.wii_score / 100) * 110;
                  return `${x},${y}`;
                });
                const d = `M ${points.join(' L ')}`;
                const areaD = `M 10,130 L ${points.join(' L ')} L 350,130 Z`;

                return (
                  <>
                    <path d={areaD} fill="url(#areaGrad)" />
                    <path d={d} fill="none" stroke="#10b981" strokeWidth="2.5" />
                    {epochs.map((e, idx) => {
                      const x = (idx / (epochs.length - 1)) * 340 + 10;
                      const y = 130 - (e.wii_score / 100) * 110;
                      return (
                        <g key={idx}>
                          <circle cx={x} cy={y} r="4" fill="#070b14" stroke="#10b981" strokeWidth="2" />
                          <text x={x} y={y - 8} fill="#34d399" fontSize="9" fontWeight="bold" textAnchor="middle">
                            {e.wii_score.toFixed(0)}
                          </text>
                        </g>
                      );
                    })}
                  </>
                );
              })()}
            </svg>
          </div>

          {/* Epoch labels */}
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#64748b' }}>
            {epochs.map((e, i) => (
              <span key={i}>{e.epoch.split(' ')[0]}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
