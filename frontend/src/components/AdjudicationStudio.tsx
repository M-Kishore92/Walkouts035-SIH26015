import React, { useState } from 'react';
import { SatelliteClaim, FieldPhoto, LedgerEntry, Role } from '../types';

interface AdjudicationStudioProps {
  claims: SatelliteClaim[];
  currentRole: Role;
  onAdjudicate: (claimId: string, decision: 'ACCEPT' | 'REJECT' | 'DEFER', notes: string) => void;
}

export const AdjudicationStudio: React.FC<AdjudicationStudioProps> = ({
  claims,
  currentRole,
  onAdjudicate,
}) => {
  const [selectedClaimId, setSelectedClaimId] = useState<string>(claims[0]?.id || '');
  const [adjudicationNotes, setAdjudicationNotes] = useState<string>('');
  const [isSigning, setIsSigning] = useState<boolean>(false);

  const selectedClaim = claims.find((c) => c.id === selectedClaimId) || claims[0];
  const canAdjudicate = currentRole === 'monitor' || currentRole === 'admin';

  const handleDecision = (decision: 'ACCEPT' | 'REJECT' | 'DEFER') => {
    if (!selectedClaim) return;
    setIsSigning(true);
    setTimeout(() => {
      onAdjudicate(selectedClaim.id, decision, adjudicationNotes || `Decision ${decision} recorded by ${currentRole}`);
      setIsSigning(false);
      setAdjudicationNotes('');
    }, 600);
  };

  return (
    <div className="glass-panel" style={{ padding: 24, marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span>Cross-Validation & Adjudication Studio</span>
            <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: 4, background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24' }}>
              Spatiotemporal Reconciliation Hub
            </span>
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Reconcile satellite-claimed land/water transitions against geotagged field photos with cryptographic audit signature.
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) minmax(0, 2fr)', gap: 24 }}>
        {/* Claims Queue Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
            Verification Queue ({claims.length} Claims)
          </div>
          {claims.map((claim) => {
            const isSelected = claim.id === selectedClaim?.id;
            let statusColor = '#38bdf8';
            if (claim.status === 'PHOTO_CORROBORATED') statusColor = '#10b981';
            else if (claim.status === 'FLAGGED_MISMATCH') statusColor = '#ef4444';
            else if (claim.status === 'UNVERIFIED') statusColor = '#f59e0b';

            return (
              <div
                key={claim.id}
                onClick={() => setSelectedClaimId(claim.id)}
                style={{
                  background: isSelected ? 'rgba(6, 182, 212, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                  border: isSelected ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 10,
                  padding: 14,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>
                    {claim.id}
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    padding: '2px 6px',
                    borderRadius: 4,
                    background: `${statusColor}22`,
                    color: statusColor,
                    fontWeight: 700,
                  }}>
                    {claim.status.replace('_', ' ')}
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc' }}>
                  {claim.change_type.replace('_', ' ')}: +{claim.magnitude} ha
                </div>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: 4 }}>
                  {claim.watershed_code} • Centroid: {claim.centroid_lat.toFixed(3)}°N, {claim.centroid_lng.toFixed(3)}°E
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Claim Deep Inspection & Side-by-Side Studio */}
        {selectedClaim ? (
          <div style={{
            background: 'rgba(0, 0, 0, 0.25)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: 12,
            padding: 20,
            display: 'flex',
            flexDirection: 'column',
            gap: 18,
          }}>
            {/* Header info */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>Selected Claim</span>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f8fafc' }}>
                  {selectedClaim.change_type.replace('_', ' ')}: +{selectedClaim.magnitude} ha
                </h3>
                <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                  Micro-Watershed {selectedClaim.watershed_code} • Epoch {selectedClaim.epoch}
                </div>
              </div>

              {selectedClaim.adjudication_decision && (
                <div style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  background: selectedClaim.adjudication_decision === 'ACCEPT' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  color: selectedClaim.adjudication_decision === 'ACCEPT' ? '#34d399' : '#f87171',
                  border: `1px solid ${selectedClaim.adjudication_decision === 'ACCEPT' ? '#10b981' : '#ef4444'}`,
                  fontWeight: 700,
                  fontSize: '0.8rem',
                }}>
                  Decision: {selectedClaim.adjudication_decision}ED
                </div>
              )}
            </div>

            {/* Split Comparison: Satellite Claim vs DRISHTI Photo */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {/* Left: Satellite Detection */}
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 14, borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.72rem', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase', marginBottom: 8 }}>
                  🛰️ Satellite Sensor Evidence
                </div>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.6 }}>
                  <div><strong>Sensor:</strong> Sentinel-2 L2A (10m Resolution)</div>
                  <div><strong>Spectral Index:</strong> NDWI shift &gt; +0.28</div>
                  <div><strong>Detection Date:</strong> {new Date(selectedClaim.detected_at).toLocaleDateString()}</div>
                  <div><strong>Centroid:</strong> {selectedClaim.centroid_lat}°N, {selectedClaim.centroid_lng}°E</div>
                </div>
              </div>

              {/* Right: Ground Truth DRISHTI Photo */}
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 14, borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                <div style={{ fontSize: '0.72rem', color: '#a78bfa', fontWeight: 700, textTransform: 'uppercase', marginBottom: 8 }}>
                  📷 DRISHTI Field Evidence
                </div>
                {selectedClaim.matched_photos.length > 0 ? (
                  <div>
                    <img
                      src={selectedClaim.matched_photos[0].image_url}
                      alt="Field inspection"
                      style={{ width: '100%', height: 110, objectFit: 'cover', borderRadius: 6, marginBottom: 8 }}
                    />
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.5 }}>
                      <div><strong>Structure:</strong> {selectedClaim.matched_photos[0].structure_type}</div>
                      <div><strong>Condition:</strong> <span style={{ color: selectedClaim.matched_photos[0].condition === 'functional' ? '#34d399' : '#f87171' }}>{selectedClaim.matched_photos[0].condition.toUpperCase()}</span></div>
                      <div><strong>Officer:</strong> {selectedClaim.matched_photos[0].officer_name}</div>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: 24, textAlign: 'center', color: '#64748b', fontSize: '0.78rem' }}>
                    No field photo captured within 500m spatiotemporal window.
                  </div>
                )}
              </div>
            </div>

            {/* Adjudication Notes & Action Form */}
            {canAdjudicate && (
              <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: 16 }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: 6 }}>
                  Adjudication Findings & Audit Rationale:
                </label>
                <textarea
                  value={adjudicationNotes}
                  onChange={(e) => setAdjudicationNotes(e.target.value)}
                  placeholder="Enter cryptographic audit rationale (e.g., 'Functional check dam verified with full storage, corroborated with satellite spectral gain.')..."
                  rows={2}
                  style={{
                    width: '100%',
                    background: 'rgba(7, 11, 20, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: 8,
                    color: '#f8fafc',
                    padding: 10,
                    fontSize: '0.8rem',
                    outline: 'none',
                    resize: 'none',
                    marginBottom: 12,
                  }}
                />

                <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => handleDecision('REJECT')}
                    disabled={isSigning}
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      color: '#f87171',
                      border: '1px solid rgba(239, 68, 68, 0.4)',
                      padding: '8px 16px',
                      borderRadius: 8,
                      fontSize: '0.8rem',
                      fontWeight: 700,
                    }}
                  >
                    Flag Mismatch (Reject)
                  </button>
                  <button
                    onClick={() => handleDecision('DEFER')}
                    disabled={isSigning}
                    style={{
                      background: 'rgba(245, 158, 11, 0.15)',
                      color: '#fbbf24',
                      border: '1px solid rgba(245, 158, 11, 0.4)',
                      padding: '8px 16px',
                      borderRadius: 8,
                      fontSize: '0.8rem',
                      fontWeight: 700,
                    }}
                  >
                    Defer / Field Re-survey
                  </button>
                  <button
                    onClick={() => handleDecision('ACCEPT')}
                    disabled={isSigning}
                    style={{
                      background: 'linear-gradient(135deg, #10b981, #059669)',
                      color: '#fff',
                      border: 'none',
                      padding: '8px 20px',
                      borderRadius: 8,
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      boxShadow: '0 0 12px rgba(16, 185, 129, 0.3)',
                    }}
                  >
                    {isSigning ? 'Cryptographically Signing...' : '✓ Corroborate & Sign to Ledger'}
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};
