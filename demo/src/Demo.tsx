import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { AgentSteps } from "@/components/snap-cn/agent-steps";
import { PunchLines } from "@/components/snap-cn/punch-lines";
import { ScreenRecording } from "@/components/snap-cn/screen-recording";
import { TerminalSimulator } from "@/components/snap-cn/terminal-simulator";
import { WordCaptions } from "@/components/snap-cn/word-captions";
import { WordmarkCut } from "@/components/snap-cn/wordmark-cut";
import { SnapCnUIProvider } from "@/lib/snap-cn-ui";
import { BRAND, THEME } from "./brand";
import captions from "./captions.json";
import timeline from "./timeline.json";
import { RugStory } from "./scenes/RugStory";

// Scene starts come from the measured voiceover (voiceover.py → timeline.json).
const at = (id: string) => {
  const i = timeline.findIndex((s) => s.id === id);
  return { from: timeline[i].from, until: i + 1 < timeline.length ? timeline[i + 1].from : 2400 };
};
const span = (a: string, b = a) => ({ from: at(a).from, durationInFrames: at(b).until - at(a).from });

// Argus screenshots are 1972×1093 (browser content, chrome already cropped off).
const SHOT_ASPECT = 1972 / 1093;

const FictionalTag: React.FC = () => (
  <div style={{ position: "absolute", left: 40, top: 24, fontSize: 14, color: BRAND.muted, fontFamily: "Inter" }}>
    Illustration · fictional token and addresses
  </div>
);

const EndLine: React.FC = () => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 60, opacity: o, fontFamily: "Inter", background: BRAND.page }}>
      <div style={{ fontSize: 64, fontWeight: 700, color: BRAND.ink, marginBottom: 12 }}>Arc Memecoin Intel</div>
      <div style={{ fontSize: 26, color: BRAND.muted, marginBottom: 30 }}>Know where your money goes, before it goes.</div>
      <div style={{ fontFamily: "monospace", fontSize: 24, color: BRAND.ink, background: BRAND.card, border: `1px solid ${BRAND.border}`, borderRadius: 10, padding: "12px 22px" }}>
        npx skills add fozagtx/arc-memes
      </div>
    </AbsoluteFill>
  );
};

export const Demo: React.FC = () => {
  const scan = span("s7_scan");
  const copyCa = 100;
  return (
    <SnapCnUIProvider mode="dark" theme={THEME}>
      <AbsoluteFill style={{ background: BRAND.page }}>
        {/* 1. Hook: the real launchpad on Arc */}
        <Sequence {...span("s1_arc")}>
          <ScreenRecording
            src={staticFile("argus-home.png")}
            sourceAspect={SHOT_ASPECT}
            camera={[
              { at: 20, duration: 60, zoom: 1.35, x: 0.36, y: 0.3 },
              { at: 150, duration: 60, zoom: 1.25, x: 0.5, y: 0.62 },
            ]}
          />
        </Sequence>

        {/* 2–4. Sam buys, the hidden bundle, the dump */}
        <Sequence {...span("s2_sam", "s4_rug")}>
          <RugStory revealAt={at("s3_hidden").from - at("s2_sam").from} dumpAt={at("s4_rug").from - at("s2_sam").from} />
        </Sequence>

        {/* 5. The problem */}
        <Sequence {...span("s5_problem")}>
          <PunchLines
            mode="dark"
            script="Every single day. | Bundled launches. | No community. / No trust. | New people come to build. / They get drained."
            styles="slide,punch,slide,slide"
            sizes="0.8,1.3,1,0.8"
            holds="62,66,74,105"
            accentBeat={2}
            accentColor={BRAND.down}
          />
        </Sequence>

        {/* 6. Install: the real command and its real output */}
        <Sequence {...span("s6_install")}>
          <TerminalSimulator
            intro="Add *Arc Memecoin Intel* to your agent"
            command={{ managers: ["npx"], text: "npx skills add fozagtx/arc-memes" }}
            lines={[
              { text: "npx skills add fozagtx/arc-memes", type: "command" },
              { text: "Cloning repository...", type: "log" },
              { text: "Found 1 skill: arc-memecoin-intel", type: "log" },
              { text: "Installed for Claude Code and Codex", type: "success" },
            ]}
          />
        </Sequence>

        {/* 7a. Copy any contract address from the launchpad */}
        <Sequence from={scan.from} durationInFrames={copyCa}>
          <ScreenRecording
            src={staticFile("argus-token.png")}
            sourceAspect={SHOT_ASPECT}
            camera={[{ at: 10, duration: 40, zoom: 2.2, x: 0.17, y: 0.25 }]}
          />
        </Sequence>
        {/* 7b. The agent scans it */}
        <Sequence from={scan.from + copyCa} durationInFrames={scan.durationInFrames - copyCa}>
          <AbsoluteFill style={{ transform: "scale(1.6)", top: 20 }}>
          <AgentSteps
            mode="dark"
            glowRadius={0}
            query="Scan 0x5ad1…c0de before I buy"
            steps={[
              { running: "Reading transfers…", done: "Read 1,284 transfers" },
              { running: "Finding the pool…", done: "Found the USDC pool" },
              { running: "Tracing early buyers…", done: "3 buyers share one funder", icon: "globe" },
              { running: "Checking liquidity…", done: "LP not burned, can be pulled" },
              { running: "Scoring risk…", done: "Scored" },
            ]}
            result="Critical · 82/100 · 33% bundled"
            queryHold={0.9}
            stepHold={1.25}
            finalHold={0.6}
          />
          </AbsoluteFill>
          <FictionalTag />
        </Sequence>

        {/* 8. Sam scans first this time */}
        <Sequence {...span("s8_save")}>
          <PunchLines
            mode="dark"
            script="This time, / Sam scans first. | Critical risk. | Sam keeps / the $500."
            styles="slide,punch,slide"
            sizes="0.9,1.3,1"
            holds="70,60,115"
            accentBeat={3}
            accentColor={BRAND.up}
          />
        </Sequence>

        {/* 9. Name + install */}
        <Sequence {...span("s9_cta")}>
          <Sequence durationInFrames={78}>
            <WordmarkCut mode="dark" word="Arc Intel" dotFrom={BRAND.accent} dotTo={BRAND.accentSoft} />
          </Sequence>
          <Sequence from={78}>
            <EndLine />
          </Sequence>
        </Sequence>

        <Audio src={staticFile("voiceover.wav")} />
        <WordCaptions captions={captions} preset="clean" mode="dark" fontSize={30} accentColor={BRAND.accentSoft} />
      </AbsoluteFill>
    </SnapCnUIProvider>
  );
};
