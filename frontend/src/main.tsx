import { createRoot } from "react-dom/client";
import App from "./App";
import "leaflet/dist/leaflet.css";
import "./index.css";

// Note: no <StrictMode> — react-three-fiber's Canvas does not behave well under
// React 19 StrictMode's double-mount (renders an empty scene). The rest of the
// app is StrictMode-clean; this is purely to keep the 3D city reliable.
createRoot(document.getElementById("root")!).render(<App />);
