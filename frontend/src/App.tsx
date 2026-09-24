import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { KPIRibbon } from './components/KPIRibbon';
import { WatershedMap } from './components/WatershedMap';
import { WIIScorecard } from './components/WIIScorecard';
import { AdjudicationStudio } from './components/AdjudicationStudio';
import { LedgerExplorer } from './components/LedgerExplorer';
import { ReportGenerator } from './components/ReportGenerator';

import {
  MOCK_WATERSHEDS,
  MOCK_EPOCHS,
  MOCK_PHOTOS,
  MOCK_CLAIMS,
  MOCK_LEDGER,
} from './data/mockData';
import { Role, Watershed, SatelliteClaim, LedgerEntry } from './types';

export const App: React.FC = () => {
  const [currentRole, setCurrentRole] = useState<Role>('monitor');
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [watersheds, setWatersheds] = useState<Watershed[]>(MOCK_WATERSHEDS);
  const [selectedWatershed, setSelectedWatershed] = useState<Watershed>(MOCK_WATERSHEDS[0]);
  const [claims, setClaims] = useState<SatelliteClaim[]>(MOCK_CLAIMS);
  const [ledger, setLedger] = useState<LedgerEntry[]>(MOCK_LEDGER);
  const [ledgerValid, setLedgerValid] = useState<boolean>(true);

  // Adjudication handler that adds an immutable block to the ledger
  const handleAdjudicate = (claimId: string, decision: 'ACCEPT' | 'REJECT' | 'DEFER', notes: string) => {
    // 1. Update claim status
    setClaims((prevClaims) =>
      prevClaims.map((c) => {
        if (c.id === claimId) {
          return {
            ...c,
            status: decision === 'ACCEPT' ? 'PHOTO_CORROBORATED' : decision === 'REJECT' ? 'FLAGGED_MISMATCH' : 'UNVERIFIED',
            adjudication_decision: decision,
            adjudication_notes: notes,
          };
        }
        return c;
      })
    );

    // 2. Generate simulated SHA-256 hash chaining
    const lastBlock = ledger[ledger.length - 1];
    const seq = lastBlock ? lastBlock.sequence_number + 1 : 1;
    const prevHash = lastBlock ? lastBlock.chain_hash : '0000000000000000000000000000000000000000000000000000000000000000';
    
    // Simple deterministic hex generator for UI simulation
    const simpleHash = (str: string) => {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash |= 0;
      }
      return Math.abs(hash).toString(16).padStart(16, '0') + Math.abs(hash * 31).toString(16).padStart(48, 'a');
    };

    const payload = JSON.stringify({ seq, claimId, decision, role: currentRole, timestamp: new Date().toISOString() });
    const payloadHash = simpleHash(payload);
    const chainHash = simpleHash(payloadHash + prevHash);

    const newBlock: LedgerEntry = {
      sequence_number: seq,
      claim_id: claimId,
      officer_id: `usr-${currentRole}-01`,
      officer_name: currentRole === 'monitor' ? 'Dr. Rajesh Kulkarni (District Monitoring Officer)' : 'System Administrator',
      decision,
      decided_at: new Date().toISOString(),
      payload_hash: payloadHash,
      previous_hash: prevHash,
      chain_hash: chainHash,
    };

    setLedger((prev) => [...prev, newBlock]);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation */}
      <Navbar
        currentRole={currentRole}
        onRoleChange={setCurrentRole}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        ledgerValid={ledgerValid}
      />

      {/* Main Container */}
      <main style={{ flex: 1, maxWidth: 1600, width: '100%', margin: '0 auto', padding: '24px 24px 60px' }}>
        {/* KPI Ribbon shown across all tabs or dashboard */}
        <KPIRibbon
          watersheds={watersheds}
          totalLedgerBlocks={ledger.length}
        />

        {/* Tab Router */}
        {activeTab === 'dashboard' && (
          <>
            <WatershedMap
              watersheds={watersheds}
              selectedWatershed={selectedWatershed}
              onSelectWatershed={setSelectedWatershed}
              photos={MOCK_PHOTOS}
            />
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.3fr) minmax(0, 1fr)', gap: 24 }}>
              <WIIScorecard
                watershed={selectedWatershed}
                epochs={MOCK_EPOCHS}
              />
              <AdjudicationStudio
                claims={claims}
                currentRole={currentRole}
                onAdjudicate={handleAdjudicate}
              />
            </div>
          </>
        )}

        {activeTab === 'map' && (
          <WatershedMap
            watersheds={watersheds}
            selectedWatershed={selectedWatershed}
            onSelectWatershed={setSelectedWatershed}
            photos={MOCK_PHOTOS}
          />
        )}

        {activeTab === 'adjudication' && (
          <AdjudicationStudio
            claims={claims}
            currentRole={currentRole}
            onAdjudicate={handleAdjudicate}
          />
        )}

        {activeTab === 'wii' && (
          <WIIScorecard
            watershed={selectedWatershed}
            epochs={MOCK_EPOCHS}
          />
        )}

        {activeTab === 'ledger' && (
          <LedgerExplorer ledger={ledger} />
        )}

        {activeTab === 'reports' && (
          <ReportGenerator
            watershed={selectedWatershed}
            epochs={MOCK_EPOCHS}
            ledger={ledger}
          />
        )}
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(7, 11, 20, 0.95)',
        padding: '16px 24px',
        textAlign: 'center',
        fontSize: '0.75rem',
        color: '#64748b',
      }}>
        PRAMAAN SIH-26015 • Ministry of Rural Development (DoLR) • Deterministic Sentinel-2 + DRISHTI Cross-Validation Engine
      </footer>
    </div>
  );
};
