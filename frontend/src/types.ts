export type Role = 'monitor' | 'field_officer' | 'planner' | 'auditor' | 'admin';

export type WIIBand = 'CRITICAL' | 'POOR' | 'MODERATE' | 'GOOD' | 'EXCELLENT';

export type ValidationStatus = 
  | 'PHOTO_CORROBORATED' 
  | 'PARTIALLY_CORROBORATED' 
  | 'UNVERIFIED' 
  | 'FLAGGED_MISMATCH';

export interface Watershed {
  id: string;
  watershed_code: string;
  name: string;
  block: string;
  district: string;
  state: string;
  area_ha: number;
  center: [number, number]; // [lat, lng]
  polygon: [number, number][]; // list of [lat, lng] points
  current_wii: number;
  band: WIIBand;
  ndvi_current: number;
  ndvi_baseline: number;
  water_current_ha: number;
  water_baseline_ha: number;
  degraded_current_ha: number;
  degraded_baseline_ha: number;
  photo_corroboration_rate: number;
  total_structures: number;
  verified_structures: number;
}

export interface SatelliteEpoch {
  epoch: string; // T0, T1, T2, T3, T4, T5
  date: string;
  ndvi_mean: number;
  water_spread_ha: number;
  degraded_land_ha: number;
  wii_score: number;
  cloud_cover_pct: number;
}

export interface FieldPhoto {
  id: string;
  watershed_id: string;
  claim_id?: string;
  structure_type: string;
  condition: 'functional' | 'damaged' | 'silted' | 'under_construction';
  confidence: number;
  blur_score: number;
  timestamp: string;
  officer_name: string;
  lat: number;
  lng: number;
  image_url: string;
  azimuth_deg: number;
  is_tamper_flagged: boolean;
}

export interface SatelliteClaim {
  id: string;
  watershed_id: string;
  watershed_code: string;
  epoch: string;
  change_type: 'WATER_INCREASE' | 'VEGETATION_INCREASE' | 'DEGRADED_REDUCTION' | 'LULC_SHIFT';
  magnitude: number; // e.g. +8.2 ha or +0.14 NDVI
  centroid_lat: number;
  centroid_lng: number;
  detected_at: string;
  status: ValidationStatus;
  adjudication_decision?: 'ACCEPT' | 'REJECT' | 'DEFER';
  adjudication_notes?: string;
  matched_photos: FieldPhoto[];
}

export interface LedgerEntry {
  sequence_number: number;
  claim_id: string;
  officer_id: string;
  officer_name: string;
  decision: 'ACCEPT' | 'REJECT' | 'DEFER';
  decided_at: string;
  payload_hash: string;
  previous_hash: string;
  chain_hash: string;
}
