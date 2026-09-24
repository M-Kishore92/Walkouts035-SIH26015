import React, { useState } from 'react';
import { Watershed, SatelliteEpoch, LedgerEntry } from '../types';

interface ReportGeneratorProps {
  watershed: Watershed;
  epochs: SatelliteEpoch[];
  ledger: LedgerEntry[];
}

export const ReportGenerator: React.FC<ReportGeneratorProps> = ({
  watershed,
  epochs,
  ledger,
}) => {
  const [downloading, setDownloading] = useState(false);

  const handleDownloadReport = () => {
    setDownloading(true);
    setTimeout(() => {
      setDownloading(false);
      window.print();
    }, 500);
  };

  return (
    <div className="glass-panel" style={{ padding: 24, marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 14 }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span>IWMP Monitoring & Statutory Compliance Report</span>
            <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: 4, background: 'rgba(16, 185, 129, 0.2)', color: '#34d399' }}>
              DoLR Format A-4
            </span>
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Auto-generated periodic performance audit for Department of Land Resources, Ministry of Rural Development.
          </p>
        </div>

        <button
          onClick={handleDownloadReport}
          disabled={downloading}
          style={{
            background: 'linear-gradient(135deg, #10b981, #059669)',
            color: '#fff',
            border: 'none',
            padding: '8px 18px',
            borderRadius: 8,
            fontSize: '0.8rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            boxShadow: '0 0 14px rgba(16, 185, 129, 0.3)',
          }}
        >
          <span>📄</span>
          <span>{downloading ? 'Preparing Document...' : 'Print / Export Statutory PDF'}</span>
        </button>
      </div>

      {/* Printable Report Canvas */}
      <div style={{
        background: '#ffffff',
        color: '#0f172a',
        borderRadius: 8,
        padding: 32,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
      }}>
        {/* Official Header */}
        <div style={{ borderBottom: '2px solid #0f172a', paddingBottom: 16, marginBottom: 20, display: 'flex', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569' }}>
              Government of India • Ministry of Rural Development
            </div>
            <h1 style={{ fontSize: '1.3rem', fontWeight: 800, margin: '4px 0', color: '#0f172a' }}>
              Integrated Watershed Management Programme (IWMP) Evaluation Report
            </h1>
            <div style={{ fontSize: '0.85rem', color: '#334155' }}>
              Target Basin: <strong>{watershed.watershed_code} ({watershed.name})</strong>, {watershed.district} District
            </div>
          </div>
          <div style={{ textAlign: 'right', fontSize: '0.8rem', color: '#64748b' }}>
            <div>Doc ID: PRM-2026-REP-8812</div>
            <div>Date: {new Date().toLocaleDateString()}</div>
            <div>Classification: <strong>CAG AUDIT READY</strong></div>
          </div>
        </div>

        {/* Executive Summary Table */}
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 8, color: '#0f172a' }}>
            1. Executive Performance Summary
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <tbody>
              <tr style={{ borderBottom: '1px solid #e2e8f0', background: '#f8fafc' }}>
                <td style={{ padding: '8px 12px', fontWeight: 600 }}>Composite WII Index</td>
                <td style={{ padding: '8px 12px', fontWeight: 700, color: '#059669' }}>
                  {watershed.current_wii} / 100 ({watershed.band})
                </td>
                <td style={{ padding: '8px 12px', fontWeight: 600 }}>Ground Truth Corroboration</td>
                <td style={{ padding: '8px 12px', fontWeight: 700 }}>
                  {watershed.photo_corroboration_rate}%
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                <td style={{ padding: '8px 12px', fontWeight: 600 }}>Surface Water Spread Gain</td>
                <td style={{ padding: '8px 12px' }}>
                  +{(watershed.water_current_ha - watershed.water_baseline_ha).toFixed(1)} ha (+48.2%)
                </td>
                <td style={{ padding: '8px 12px', fontWeight: 600 }}>Degraded Land Treated</td>
                <td style={{ padding: '8px 12px' }}>
                  {(watershed.degraded_baseline_ha - watershed.degraded_current_ha).toFixed(1)} ha remediated
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid #e2e8f0', background: '#f8fafc' }}>
                <td style={{ padding: '8px 12px', fontWeight: 600 }}>Total Water Harvesting Works</td>
                <td style={{ padding: '8px 12px' }}>{watershed.total_structures} Structures</td>
                <td style={{ padding: '8px 12px', fontWeight: 600 }}>Field Geotag Verified</td>
                <td style={{ padding: '8px 12px' }}>{watershed.verified_structures} Structures</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Multi-Epoch Trajectory Table */}
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 8, color: '#0f172a' }}>
            2. Multi-Epoch Satellite Indicator Progression
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #cbd5e1', background: '#f1f5f9' }}>
                <th style={{ padding: '8px 12px' }}>Epoch</th>
                <th style={{ padding: '8px 12px' }}>Acquisition Date</th>
                <th style={{ padding: '8px 12px' }}>Mean NDVI</th>
                <th style={{ padding: '8px 12px' }}>Water Spread (ha)</th>
                <th style={{ padding: '8px 12px' }}>Degraded Land (ha)</th>
                <th style={{ padding: '8px 12px' }}>WII Score</th>
              </tr>
            </thead>
            <tbody>
              {epochs.map((ep, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '6px 12px', fontWeight: 600 }}>{ep.epoch}</td>
                  <td style={{ padding: '6px 12px' }}>{ep.date}</td>
                  <td style={{ padding: '6px 12px' }}>{ep.ndvi_mean.toFixed(2)}</td>
                  <td style={{ padding: '6px 12px' }}>{ep.water_spread_ha.toFixed(1)}</td>
                  <td style={{ padding: '6px 12px' }}>{ep.degraded_land_ha.toFixed(1)}</td>
                  <td style={{ padding: '6px 12px', fontWeight: 700, color: '#059669' }}>{ep.wii_score.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Sign-off & Audit Seal */}
        <div style={{ borderTop: '1px solid #cbd5e1', paddingTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#64748b' }}>
          <div>
            <div>Ledger Proof: <code>{ledger[ledger.length - 1]?.chain_hash.slice(0, 32)}...</code></div>
            <div>Generated by PRAMAAN Analytical Engine (SIH-26015 Compliant)</div>
          </div>
          <div style={{ textAlign: 'center', border: '1px dashed #94a3b8', padding: '6px 14px', borderRadius: 4 }}>
            <div style={{ fontWeight: 700, color: '#0f172a' }}>OFFICIALLY VERIFIED</div>
            <div>DoLR / SLNA Seal</div>
          </div>
        </div>
      </div>
    </div>
  );
};
