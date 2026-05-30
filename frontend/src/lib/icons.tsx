// Meraklis — Icon. Maps the design's kebab-case lucide names to components.
import type { CSSProperties } from "react";
import {
  Activity, Gauge, Flag, Boxes, Building2, Scale, Megaphone, FileText, ListChecks,
  Cpu, MapPin, Search, ScanSearch, ArrowRight, Lock, FunctionSquare, WifiOff,
  GitCommitHorizontal, Terminal, Shield, ShieldCheck, ShieldAlert, Check, CheckCheck,
  Play, RotateCw, RotateCcw, Radio, TrendingDown, TrendingUp, Minus, HelpCircle,
  GitBranch, Info, Crosshair, User, UserCheck, ArrowRightCircle, Copy, Download, Link,
  Filter, X, Image, Map, HardDrive, Database, File, Circle, CheckCircle, AlertTriangle,
  Box, Ruler, Layers, ChevronRight, ChevronLeft, Network, ScrollText, LoaderCircle, PanelRightClose,
  CircleDollarSign,
  type LucideIcon,
} from "lucide-react";

const ICONS: Record<string, LucideIcon> = {
  activity: Activity, gauge: Gauge, flag: Flag, boxes: Boxes, "building-2": Building2,
  scale: Scale, megaphone: Megaphone, "file-text": FileText, "list-checks": ListChecks,
  cpu: Cpu, "map-pin": MapPin, search: Search, "scan-search": ScanSearch,
  "arrow-right": ArrowRight, lock: Lock, "function-square": FunctionSquare, "wifi-off": WifiOff,
  "git-commit-horizontal": GitCommitHorizontal, terminal: Terminal, shield: Shield,
  "shield-check": ShieldCheck, "shield-alert": ShieldAlert, check: Check, "check-check": CheckCheck,
  play: Play, "rotate-cw": RotateCw, "rotate-ccw": RotateCcw, radio: Radio,
  "trending-down": TrendingDown, "trending-up": TrendingUp, minus: Minus, "help-circle": HelpCircle,
  "git-branch": GitBranch, info: Info, crosshair: Crosshair, user: User, "user-check": UserCheck,
  "arrow-right-circle": ArrowRightCircle, copy: Copy, download: Download, link: Link,
  filter: Filter, x: X, image: Image, map: Map, "hard-drive": HardDrive, database: Database,
  file: File, circle: Circle, "check-circle": CheckCircle, "alert-triangle": AlertTriangle,
  box: Box, ruler: Ruler, layers: Layers, "chevron-right": ChevronRight, network: Network,
  "scroll-text": ScrollText, loader: LoaderCircle, "chevron-left": ChevronLeft,
  "panel-right-close": PanelRightClose, "circle-dollar-sign": CircleDollarSign,
};

export function Icon({
  name,
  size = 16,
  color,
  strokeWidth = 1.9,
  className = "",
  style,
}: {
  name: string;
  size?: number;
  color?: string;
  strokeWidth?: number;
  className?: string;
  style?: CSSProperties;
}) {
  const Cmp = ICONS[name] ?? Circle;
  return (
    <span className={"ico " + className} style={{ width: size, height: size, color, ...style }}>
      <Cmp size={size} strokeWidth={strokeWidth} />
    </span>
  );
}
