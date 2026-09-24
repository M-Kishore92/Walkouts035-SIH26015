import React, { useState } from 'react';
import { Watershed, FieldPhoto, WIIBand } from '../types';

interface WatershedMapProps {
  watersheds: Watershed[];
  selectedWatershed: Watershed;
  onSelectWatershed: (w: Watershed) => void;
  photos: FieldPhoto[];
}

export const WatershedMap: React.FC<WatershedMapProps> = ({
  watersheds,
  selectedWatershed,
  onSelectWatershed,
  photos,
}) => {
  const [activeLayer, setActiveLayer] = useState<'standard' | 'ndvi' | 'water' | 'photos'>('ndvi');
  const [selectedPhoto, setSelectedPhoto] = useState<FieldPhoto | null>(null);

  // SVG Projection bounding box for Nanded pilot area
  // Lat: 18.5 to 19.0, Lng: 77.0 to 77.8
  const minLat = 18.45;
  const maxLat = 19.05;
  const minLng = 77.05;
  const maxLng = 77.80;

  const projectPoint = (lat: number, lng: number, width = 760, height = 480): [number, number] => {
    const x = ((lng - minLng) / (maxLng - minLng)) * width;
    const y = height - ((lat - minLat) / (maxLat - minLat)) * height;
    return [x, y];
  };

  const getBandColor = (band: WIIBand) => {
    switch (band) {
      case 'EXCELLENT': return '#10b981';
      case 'GOOD': return '#06b6d4';
      case 'MODERATE': return '#eab308';
      case 'POOR': return '#f97316';
      case 'CRITICAL': return '#ef4444';
      default: return '#64748b';
    }
  };

  return (
    <div className="glass-panel" style={{ padding: 24, marginBottom: 24 }}>
      {/* Map Header with Layer Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span>Spatial Watershed GIS Explorer</span>
            <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: 4, background: 'rgba(6, 182, 212, 0.2)', color: '#38bdf8' }}>
              EPSG:4326 • Sentinel-2 + DRISHTI
            </span>
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Interactive micro-watershed boundaries, multi-spectral indices, and ground-truth camera vectors.
          </p>
        </div>

        {/* Layer Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(0, 0, 0, 0.3)', padding: 4, borderRadius: 8 }}>
          {[
            { id: 'ndvi', label: 'NDVI Vegetation', icon: '🌿' },
            { id: 'water', label: 'NDWI Water Spread', icon: '💧' },
            { id: 'photos', label: 'DRISHTI Ground Truth', icon: '📷' },
            { id: 'standard', label: 'Boundary & WII', icon: '🗺️' },
          ].map((layer) => (
            <button
              key={layer.id}
              onClick={() => setActiveLayer(layer.id as any)}
              style={{
                background: activeLayer === layer.id ? 'rgba(6, 182, 212, 0.25)' : 'transparent',
                border: activeLayer === layer.id ? '1px solid rgba(6, 182, 212, 0.5)' : '1px solid transparent',
                borderRadius: 6,
                padding: '6px 12px',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: activeLayer === layer.id ? '#38bdf8' : '#94a3b8',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span>{layer.icon}</span>
              <span>{layer.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Map View & Details Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(320px, 1fr)', gap: 20 }}>
        {/* Interactive GIS Canvas */}
        <div style={{
          position: 'relative',
          background: 'radial-gradient(ellipse at center, #0f1c33 0%, #080d1a 100%)',
          borderRadius: 12,
          border: '1px solid rgba(255, 255, 255, 0.1)',
          overflow: 'hidden',
          minHeight: 480,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          {/* Top-left Coordinate & Epoch Stamp */}
          <div style={{
            position: 'absolute',
            top: 14,
            left: 16,
            zIndex: 10,
            background: 'rgba(7, 11, 20, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: 6,
            padding: '6px 10px',
            fontSize: '0.72rem',
            fontFamily: 'var(--font-mono)',
            color: '#94a3b8',
          }}>
            <div>LAT 18.552°N • LON 77.581°E</div>
            <div style={{ color: '#38bdf8', fontWeight: 600 }}>EPOCH: T5 (MARCH 2026) • SEN-2 L2A</div>
          </div>

          {/* SVG Map Canvas */}
          <svg viewBox="0 0 760 480" style={{ width: '100%', height: '100%', cursor: 'crosshair' }}>
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
              </pattern>
              <linearGradient id="ndviGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#065f46" stopOpacity="0.7" />
                <stop offset="100%" stopColor="#10b981" stopOpacity="0.85" />
              </linearGradient>
              <linearGradient id="waterGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#0369a1" stopOpacity="0.7" />
                <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.9" />
              </linearGradient>
            </defs>

            <rect width="760" height="480" fill="url(#grid)" />

            {/* Watershed Polygons */}
            {watersheds.map((ws) => {
              const points = ws.polygon.map(([lat, lng]) => projectPoint(lat, lng).join(',')).join(' ');
              const [cx, cy] = projectPoint(ws.center[0], ws.center[1]);
              const isSelected = selectedWatershed.id === ws.id;
              const bandColor = getBandColor(ws.band);

              let fillColor = 'rgba(255, 255, 255, 0.05)';
              if (activeLayer === 'ndvi') fillColor = 'url(#ndviGrad)';
              else if (activeLayer === 'water') fillColor = 'url(#waterGrad)';
              else fillColor = `${bandColor}22`;

              return (
                <g key={ws.id} onClick={() => onSelectWatershed(ws)} style={{ cursor: 'pointer' }}>
                  <polygon
                    points={points}
                    fill={fillColor}
                    stroke={isSelected ? '#38bdf8' : bandColor}
                    strokeWidth={isSelected ? 3 : 1.5}
                    strokeDasharray={isSelected ? 'none' : '4,2'}
                    style={{ transition: 'all 0.3s ease' }}
                  />
                  {/* Watershed Center Marker & Label */}
                  <circle cx={cx} cy={cy} r={isSelected ? 6 : 4} fill={bandColor} />
                  <text
                    x={cx}
                    y={cy - 12}
                    fill="#f8fafc"
                    fontSize="11"
                    fontWeight="700"
                    textAnchor="middle"
                    style={{ textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}
                  >
                    {ws.watershed_code}
                  </text>
                  <text
                    x={cx}
                    y={cy + 18}
                    fill={bandColor}
                    fontSize="9"
                    fontWeight="600"
                    textAnchor="middle"
                  >
                    WII: {ws.current_wii} ({ws.band})
                  </text>
                </g>
              );
            })}

            {/* DRISHTI Geo-tagged Photos Pins */}
            {(activeLayer === 'photos' || activeLayer === 'standard') && photos.map((p) => {
              const [px, py] = projectPoint(p.lat, p.lng);
              const isSelected = selectedPhoto?.id === p.id;
              return (
                <g key={p.id} onClick={(e) => { e.stopPropagation(); setSelectedPhoto(p); }} style={{ cursor: 'pointer' }}>
                  <circle cx={px} cy={py} r={isSelected ? 10 : 7} fill="#8b5cf6" stroke="#fff" strokeWidth={1.5} />
                  <text x={px} y={py + 3} fill="#fff" fontSize="8" fontWeight="bold" textAnchor="middle">
                    📷
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Map Legend */}
          <div style={{
            position: 'absolute',
            bottom: 14,
            left: 16,
            background: 'rgba(7, 11, 20, 0.9)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: 8,
            padding: '8px 12px',
            fontSize: '0.7rem',
            display: 'flex',
            gap: 12,
            alignItems: 'center',
          }}>
            <span style={{ color: '#94a3b8', fontWeight: 600 }}>WII Bands:</span>
            <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#10b981' }} />
              EXCELLENT (&gt;70)
            </span>
            <span style={{ color: '#06b6d4', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#06b6d4' }} />
              GOOD (56-70)
            </span>
            <span style={{ color: '#eab308', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#eab308' }} />
              MODERATE (41-55)
            </span>
            <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: '#ef4444' }} />
              CRITICAL (&lt;25)
            </span>
          </div>
        </div>

        {/* Selected Watershed / Photo Drawer */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Micro-Watershed Profile Card */}
          <div className="glass-panel" style={{ padding: 18, borderLeft: `4px solid ${getBandColor(selectedWatershed.band)}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span className={`badge-pill badge-${selectedWatershed.band.toLowerCase()}`}>
                  {selectedWatershed.band}
                </span>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f8fafc', marginTop: 6 }}>
                  {selectedWatershed.watershed_code}
                </h3>
                <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                  {selectedWatershed.name}, {selectedWatershed.block} Block
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>WII Score</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: getBandColor(selectedWatershed.band) }}>
                  {selectedWatershed.current_wii}
                </div>
              </div>
            </div>

            <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: '0.78rem' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 8, borderRadius: 6 }}>
                <div style={{ color: '#64748b' }}>Catchment Area</div>
                <div style={{ fontWeight: 700, color: '#f8fafc' }}>{selectedWatershed.area_ha} ha</div>
              </div>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 8, borderRadius: 6 }}>
                <div style={{ color: '#64748b' }}>Photo Corroboration</div>
                <div style={{ fontWeight: 700, color: '#34d399' }}>{selectedWatershed.photo_corroboration_rate}%</div>
              </div>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 8, borderRadius: 6 }}>
                <div style={{ color: '#64748b' }}>Water Spread Gain</div>
                <div style={{ fontWeight: 700, color: '#38bdf8' }}>
                  +{(selectedWatershed.water_current_ha - selectedWatershed.water_baseline_ha).toFixed(1)} ha
                </div>
              </div>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 8, borderRadius: 6 }}>
                <div style={{ color: '#64748b' }}>Degraded Reduced</div>
                <div style={{ fontWeight: 700, color: '#fbbf24' }}>
                  -{(selectedWatershed.degraded_baseline_ha - selectedWatershed.degraded_current_ha).toFixed(1)} ha
                </div>
              </div>
            </div>
          </div>

          {/* Photo Inspection Popover if selected */}
          {selectedPhoto && (
            <div className="glass-panel" style={{ padding: 16, border: '1px solid rgba(139, 92, 246, 0.4)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#a78bfa' }}>
                  DRISHTI GROUND TRUTH #{selectedPhoto.id}
                </span>
                <button
                  onClick={() => setSelectedPhoto(null)}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '0.8rem' }}
                >
                  ✕
                </button>
              </div>
              <img
                src={selectedPhoto.image_url}
                alt="Structure"
                style={{ width: '100%', height: 130, objectFit: 'cover', borderRadius: 8, marginBottom: 8 }}
              />
              <div style={{ fontSize: '0.78rem' }}>
                <div style={{ fontWeight: 700, color: '#f8fafc' }}>{selectedPhoto.structure_type}</div>
                <div style={{ color: '#94a3b8', marginTop: 2 }}>Condition: <strong style={{ color: selectedPhoto.condition === 'functional' ? '#34d399' : '#f87171' }}>{selectedPhoto.condition}</strong></div>
                <div style={{ color: '#64748b', fontSize: '0.72rem', marginTop: 4 }}>
                  Officer: {selectedPhoto.officer_name} • Laplacian Blur: {selectedPhoto.blur_score} (Sharp)
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
