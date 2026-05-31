import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip, ZoomControl, useMap } from "react-leaflet";
import type { CityBuilding } from "../api";
import { BAND_COLOR } from "./MapCity";

// Flies the Leaflet view to the user's location when "Near me" resolves.
function Recenter({ me }: { me: { lat: number; lng: number } | null }) {
  const map = useMap();
  useEffect(() => { if (me) map.flyTo([me.lat, me.lng], 15); }, [me, map]);
  return null;
}

// The OpenHome interactive map, brought into Meraklis: a zoomable / pannable dark
// slippy map (CARTO dark_all — dark basemap *with* street names) and translucent
// risk-coloured building markers. Buildings sit at their real lat/long.
export function MapView({ buildings, minScore, includeUnknown, demoRsns, mostSevereRsn, me, nearRsns, onPick }: {
  buildings: CityBuilding[];
  minScore: number;
  includeUnknown: boolean;
  demoRsns: Set<string>;
  mostSevereRsn: string | null;
  me?: { lat: number; lng: number } | null;
  nearRsns?: Set<string>;
  onPick: (input: { address?: string; rsn?: string | null }) => void;
}) {
  const visible = useMemo(
    () => buildings.filter((b) => b.lat != null && b.lng != null && (b.score != null ? b.score >= minScore : includeUnknown)),
    [buildings, minScore, includeUnknown],
  );
  return (
    <MapContainer
      center={[43.70, -79.38]} zoom={11} minZoom={9} maxZoom={18}
      preferCanvas zoomControl={false} attributionControl={false}
      style={{ height: "100%", width: "100%", background: "#05070a" }}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
        subdomains="abcd" maxZoom={20}
      />
      <ZoomControl position="bottomright" />
      <Recenter me={me ?? null} />
      {me && (
        <CircleMarker center={[me.lat, me.lng]} radius={8}
          pathOptions={{ color: "#ffffff", fillColor: "#4aa3ff", fillOpacity: 0.9, weight: 2 }}>
          <Tooltip direction="top" offset={[0, -4]} opacity={1}>You are here</Tooltip>
        </CircleMarker>
      )}
      {visible.map((b) => {
        const col = BAND_COLOR[b.risk_level || "Unknown"] || BAND_COLOR.Unknown;
        const isSevere = b.rsn === mostSevereRsn;
        const emph = isSevere || demoRsns.has(b.rsn) || !!nearRsns?.has(b.rsn);
        return (
          <CircleMarker
            key={b.rsn}
            center={[b.lat as number, b.lng as number]}
            radius={emph ? 8 : 5}
            pathOptions={{
              color: isSevere ? "#ffffff" : col,
              fillColor: col,
              fillOpacity: emph ? 0.8 : 0.45,
              weight: emph ? 2 : 1,
            }}
            eventHandlers={{ click: () => onPick({ address: b.address, rsn: b.rsn }) }}
          >
            <Tooltip direction="top" offset={[0, -4]} opacity={1}>
              <span style={{ fontWeight: 700 }}>{b.address}</span>
              <br />
              City score {b.score ?? "—"} · grade {b.grade ?? "—"} · {b.risk_level}
              {isSevere && " · most severe city-wide"}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
