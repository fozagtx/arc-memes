import { loadFont } from "@remotion/google-fonts/Inter";
import { AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BRAND } from "../brand";

// The one beat no snapcn component covers: a token chart that rises, a bundle map that
// explains why, and the dump. Flat surfaces, hairline borders, sentence case — the
// library's own design rules. $MOONARC and every address here are fictional.
const { fontFamily } = loadFont("normal", { weights: ["400", "500", "600", "700"], subsets: ["latin"] });

const N = 90;
const SERIES = Array.from({ length: N }, (_, i) => {
  const trend = Math.pow(i / (N - 1), 1.6);
  return 0.08 + 0.8 * trend + 0.05 * (random(`p-${i}`) - 0.5);
});

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const out = Easing.bezier(0.2, 0.6, 0.35, 1);

export interface RugStoryProps {
  /** Frame (local) where the hidden-bundle beat starts. */
  revealAt: number;
  /** Frame (local) where the dump starts. */
  dumpAt: number;
}

export const RugStory: React.FC<RugStoryProps> = ({ revealAt, dumpAt }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200 } });
  const rise = interpolate(frame, [20, 150], [0.15, 1], { ...clamp, easing: out });
  const crash = interpolate(frame, [dumpAt + 15, dumpAt + 40], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
  const reveal = interpolate(frame, [revealAt, revealAt + 20], [0, 1], clamp);
  const bought = frame >= 150;
  const press = interpolate(frame, [140, 146, 152], [1, 0.96, 1], clamp);

  const pct = crash > 0 ? Math.round(69 - 161 * crash) : Math.round(69 * Math.max(0, (rise - 0.15) / 0.85));
  const mcap = crash > 0 ? Math.round(41 - 38 * crash) : Math.round(12 + 29 * Math.max(0, (rise - 0.15) / 0.85));
  const wallet = bought ? (crash > 0 ? 500 - 462 * interpolate(frame, [dumpAt + 15, dumpAt + 70], [0, 1], { ...clamp, easing: out }) : 500) : 500;
  const shake = crash > 0 && crash < 1 ? (random(`s-${frame}`) - 0.5) * 10 * (1 - crash) : 0;
  const lineColor = crash > 0 ? BRAND.down : BRAND.up;

  // chart geometry
  const cx = 64, cy = 210, cw = 700, ch = 330;
  const k = Math.max(2, Math.round(N * rise));
  const pts: [number, number][] = SERIES.slice(0, k).map((v, i) => [cx + (cw * 0.84 * i) / (N - 1), cy + ch * (1 - v)]);
  if (crash > 0) {
    const [lx, ly] = pts[pts.length - 1];
    for (let j = 1; j <= 10; j++) {
      const f = (j / 10) * crash;
      pts.push([lx + cw * 0.15 * f, ly + (cy + ch - 12 - ly) * Math.pow(f, 0.7)]);
    }
  }
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [ex, ey] = pts[pts.length - 1];

  const dim = 1 - 0.94 * reveal * (1 - interpolate(frame, [dumpAt - 10, dumpAt + 5], [0, 1], clamp));

  const nodes = [
    { x: 880, y: 470, label: "Wallet 1" },
    { x: 1040, y: 500, label: "Wallet 2" },
    { x: 1200, y: 470, label: "Wallet 3" },
  ];
  const funder = { x: 1040, y: 300 };
  const mapOn = frame >= revealAt && frame < dumpAt;

  return (
    <AbsoluteFill style={{ background: BRAND.page, fontFamily, color: BRAND.ink, transform: `translate(${shake}px, ${shake * 0.6}px)` }}>
      <div style={{ position: "absolute", left: 48, top: 28, fontSize: 14, color: BRAND.muted }}>
        Illustration · fictional token and addresses
      </div>

      {/* token card */}
      <div
        style={{
          position: "absolute", left: 40, top: 70, width: 740, height: 500, borderRadius: 16,
          background: BRAND.card, border: `1px solid ${BRAND.border}`, opacity: enter * dim,
          transform: `translateY(${(1 - enter) * 24}px)`,
        }}
      >
        <div style={{ position: "absolute", left: 28, top: 26, display: "flex", gap: 16, alignItems: "center" }}>
          <div style={{ width: 52, height: 52, borderRadius: 26, background: BRAND.accent, display: "grid", placeItems: "center", fontWeight: 700, fontSize: 24 }}>M</div>
          <div>
            <div style={{ fontSize: 34, fontWeight: 700, lineHeight: 1.1 }}>$MOONARC</div>
            <div style={{ fontSize: 16, color: BRAND.muted }}>Moon Arc · launched 4 minutes ago</div>
          </div>
        </div>
        <div style={{ position: "absolute", right: 28, top: 22, textAlign: "right" }}>
          <div style={{ fontSize: 34, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>${Math.max(3, mcap)}K</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: pct >= 0 ? BRAND.up : BRAND.down, fontVariantNumeric: "tabular-nums" }}>
            {pct >= 0 ? "+" : ""}{pct}% 24h
          </div>
        </div>
      </div>
      <svg width={1280} height={720} style={{ position: "absolute", opacity: enter * dim }}>
        <path d={d} fill="none" stroke={lineColor} strokeWidth={3.5} strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={ex} cy={ey} r={6} fill={lineColor} />
      </svg>

      {/* Sam's wallet + buy */}
      <div style={{ position: "absolute", left: 820, top: 70, width: 420, opacity: enter * (mapOn ? 1 - reveal : 1) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 18 }}>
          <div style={{ width: 48, height: 48, borderRadius: 24, background: "#27272a", border: `1px solid ${BRAND.border}`, display: "grid", placeItems: "center", fontWeight: 600 }}>S</div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 600 }}>Sam</div>
            <div style={{ fontSize: 15, color: BRAND.muted }}>New to Arc</div>
          </div>
        </div>
        <div style={{ borderRadius: 16, background: BRAND.card, border: `1px solid ${BRAND.border}`, padding: "22px 26px" }}>
          <div style={{ fontSize: 15, color: BRAND.muted }}>Wallet</div>
          <div style={{ fontSize: 54, fontWeight: 700, fontVariantNumeric: "tabular-nums", color: crash > 0 ? BRAND.down : BRAND.ink }}>
            ${wallet.toFixed(2)}
          </div>
          <div style={{ fontSize: 15, color: BRAND.muted }}>{bought ? "1.2M MOONARC" : "USDC · ready to trade"}</div>
        </div>
        <div
          style={{
            marginTop: 16, height: 64, borderRadius: 14, display: "grid", placeItems: "center", fontSize: 22, fontWeight: 600,
            background: bought ? "#1b1b1f" : BRAND.up, color: bought ? BRAND.muted : "#052e16", transform: `scale(${press})`,
            opacity: interpolate(frame, [60, 80], [0, 1], clamp),
          }}
        >
          {bought ? "Bought $500" : "Buy $500"}
        </div>
      </div>

      {/* what Sam can't see: the bundle map */}
      {mapOn && (
        <AbsoluteFill>
          <div style={{ position: "absolute", left: 64, top: 120, opacity: reveal }}>
            <div style={{ fontSize: 22, color: BRAND.muted, marginBottom: 6 }}>What Sam can't see</div>
            <div style={{ fontSize: 132, fontWeight: 700, lineHeight: 1, color: BRAND.down, fontVariantNumeric: "tabular-nums", opacity: interpolate(frame, [revealAt + 145, revealAt + 155], [0, 1], clamp) }}>
              {Math.round(33 * interpolate(frame, [revealAt + 150, revealAt + 200], [0, 1], { ...clamp, easing: out }))}%
            </div>
            <div style={{ fontSize: 30, fontWeight: 600, marginTop: 10, opacity: interpolate(frame, [revealAt + 150, revealAt + 170], [0, 1], clamp) }}>
              of the supply, held by one person
            </div>
          </div>
          <svg width={1280} height={720} style={{ position: "absolute" }}>
            {nodes.map((n, i) => {
              const p = interpolate(frame, [revealAt + 90 + i * 12, revealAt + 120 + i * 12], [0, 1], { ...clamp, easing: out });
              return <line key={n.label} x1={funder.x} y1={funder.y} x2={funder.x + (n.x - funder.x) * p} y2={funder.y + (n.y - funder.y) * p} stroke={BRAND.down} strokeWidth={2} />;
            })}
          </svg>
          {nodes.map((n, i) => {
            const p = spring({ frame: frame - revealAt - 25 - i * 10, fps, config: { damping: 200 } });
            return (
              <div key={n.label} style={{ position: "absolute", left: n.x - 70, top: n.y - 34, width: 140, textAlign: "center", opacity: p, transform: `scale(${0.9 + 0.1 * p})` }}>
                <div style={{ height: 68, borderRadius: 12, background: BRAND.card, border: `1px solid ${BRAND.down}`, display: "grid", placeItems: "center", fontSize: 18, fontWeight: 600 }}>{n.label}</div>
                <div style={{ fontSize: 14, color: BRAND.muted, marginTop: 8 }}>Bought in block 1</div>
              </div>
            );
          })}
          {(() => {
            const p = spring({ frame: frame - revealAt - 70, fps, config: { damping: 200 } });
            return (
              <div style={{ position: "absolute", left: funder.x - 120, top: funder.y - 40, width: 240, textAlign: "center", opacity: p }}>
                <div style={{ fontSize: 14, color: BRAND.muted, marginBottom: 8 }}>Same funder</div>
                <div style={{ height: 56, borderRadius: 12, background: "#2a1214", border: `1px solid ${BRAND.down}`, display: "grid", placeItems: "center", fontSize: 18, fontFamily: "monospace" }}>0x9f3…a11</div>
              </div>
            );
          })()}
        </AbsoluteFill>
      )}

      {/* the dump */}
      {crash > 0 && (
        <div
          style={{
            position: "absolute", left: 820, top: 440, width: 420, fontSize: 56, fontWeight: 700, color: BRAND.down,
            opacity: interpolate(frame, [dumpAt + 45, dumpAt + 55], [0, 1], clamp),
          }}
        >
          Rugged.
          <div style={{ fontSize: 20, fontWeight: 500, color: BRAND.muted }}>The bundle sold 12 minutes in.</div>
        </div>
      )}
    </AbsoluteFill>
  );
};
