// On-device geo helpers for the "Near me" feature. No network, no reverse-geocode —
// we only compare the device's coordinates to building coordinates locally.
import type { CityBuilding } from "../api";

export function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLng = ((bLng - aLng) * Math.PI) / 180;
  const la1 = (aLat * Math.PI) / 180;
  const la2 = (bLat * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}

export interface NearBuilding {
  b: CityBuilding;
  km: number;
}

/** The n closest buildings (with a coordinate) to a point, nearest first. */
export function nearest(buildings: CityBuilding[], lat: number, lng: number, n = 8): NearBuilding[] {
  return buildings
    .filter((b) => b.lat != null && b.lng != null)
    .map((b) => ({ b, km: haversineKm(lat, lng, b.lat as number, b.lng as number) }))
    .sort((x, y) => x.km - y.km)
    .slice(0, n);
}

// Higher = worse. Used to surface the nearest *flagged* (higher-risk) building.
export const RISK_RANK: Record<string, number> = {
  Severe: 5, High: 4, Elevated: 3, Moderate: 2, Low: 1, Unknown: 0,
};

/** Among nearby buildings, the worst-risk one (ties broken by distance). */
export function nearestFlagged(near: NearBuilding[]): CityBuilding | null {
  const flagged = near.filter((x) => (RISK_RANK[x.b.risk_level || "Unknown"] ?? 0) >= 3);
  if (!flagged.length) return null;
  flagged.sort(
    (a, b) =>
      (RISK_RANK[b.b.risk_level || "Unknown"] - RISK_RANK[a.b.risk_level || "Unknown"]) ||
      (a.km - b.km),
  );
  return flagged[0].b;
}
