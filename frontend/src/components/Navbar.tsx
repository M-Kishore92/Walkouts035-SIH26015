import React from 'react';
import { Role } from '../types';

interface NavbarProps {
  currentRole: Role;
  onRoleChange: (role: Role) => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
  ledgerValid: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentRole,
  onRoleChange,
  activeTab,
  onTabChange,
  ledgerValid,
}) => {
  const tabs = [
    { id: 'dashboard', label: 'Overview', icon: '📊' },
    { id: 'map', label: 'Watershed Map', icon: '🗺️' },
    { id: 'adjudication', label: 'Adjudication Studio', icon: '⚖️', badge: '1 Dispute' },
    { id: 'wii', label: 'WII Scoreboard', icon: '📈' },
    { id: 'ledger', label: 'Audit Ledger', icon: '⛓️' },
    { id: 'reports', label: 'IWMP Reports', icon: '📄' },
  ];

  return (
    <header style={{
      background: 'rgba(7, 11, 20, 0.85)',
      backdropFilter: 'blur(20px)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      padding: '0 24px',
    }}>
      <div style={{
        maxWidth: 1600,
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 68,
      }}>
        {/* Brand & Emblem */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 42,
            height: 42,
            borderRadius: 10,
            background: 'linear-gradient(135deg, #06b6d4, #10b981)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)',
            fontSize: '1.25rem',
            fontWeight: 800,
            color: '#fff',
          }}>
            प्र
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
                PRAMAAN
              </span>
              <span style={{
                fontSize: '0.7rem',
                padding: '2px 6px',
                borderRadius: 4,
                background: 'rgba(6, 182, 212, 0.2)',
                color: '#38bdf8',
                fontWeight: 700,
                border: '1px solid rgba(6, 182, 212, 0.4)',
              }}>
                SIH-26015
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Watershed Intelligence & Cryptographic Audit Platform • Nanded Pilot
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                style={{
                  background: isActive ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                  border: isActive ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid transparent',
                  borderRadius: 8,
                  padding: '8px 14px',
                  color: isActive ? '#38bdf8' : '#94a3b8',
                  fontSize: '0.85rem',
                  fontWeight: isActive ? 600 : 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.badge && (
                  <span style={{
                    fontSize: '0.65rem',
                    padding: '1px 6px',
                    borderRadius: 10,
                    background: 'rgba(239, 68, 68, 0.25)',
                    color: '#f87171',
                    border: '1px solid rgba(239, 68, 68, 0.5)',
                  }}>
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right Section: System Status & Role Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Cryptographic Ledger Health */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            borderRadius: 8,
            background: ledgerValid ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.15)',
            border: ledgerValid ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.4)',
            fontSize: '0.75rem',
          }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: ledgerValid ? '#10b981' : '#ef4444',
              boxShadow: ledgerValid ? '0 0 8px #10b981' : '0 0 8px #ef4444',
            }} />
            <span style={{ color: ledgerValid ? '#34d399' : '#f87171', fontWeight: 600 }}>
              {ledgerValid ? 'Ledger Chain: Intact' : 'Ledger Compromised'}
            </span>
          </div>

          {/* User Role Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Role:</span>
            <select
              value={currentRole}
              onChange={(e) => onRoleChange(e.target.value as Role)}
              style={{
                background: 'rgba(16, 26, 47, 0.9)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: 8,
                color: '#f8fafc',
                padding: '6px 10px',
                fontSize: '0.8rem',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="monitor">District Monitoring Officer</option>
              <option value="field_officer">Field Verification Officer</option>
              <option value="planner">State Directorate Planner</option>
              <option value="auditor">CAG Performance Auditor</option>
              <option value="admin">System Administrator</option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
