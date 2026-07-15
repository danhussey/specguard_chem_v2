import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background, Kicker, useEnter, useSceneFade } from "../components";
import { theme } from "../theme";

const FAMILIES = ["All", "Kinase", "GPCR"];
const KINDS = ["LO", "VS"];

const STATS = [
  { value: "50", label: "assays scored", tag: "live" },
  { value: "46", label: "distinct targets", tag: "live" },
  { value: "722", label: "targets in source", tag: "available" },
  { value: "IC50 · Ki · EC50", label: "endpoints", tag: "live" },
];

export const CoverageScene: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = useSceneFade(durationInFrames);
  const head = useEnter(4);
  const grid = useEnter(24);
  const stats = useEnter(56);

  const cell = (kind: string, fam: string, idx: number) => {
    const live = kind === "LO" && fam === "All";
    const en = spring({
      frame: frame - (30 + idx * 6),
      fps,
      config: { damping: 200 },
    });
    return (
      <div
        key={kind + fam}
        style={{
          height: 132,
          borderRadius: 14,
          border: live
            ? `3px solid ${theme.accent}`
            : `2px dashed ${theme.border}`,
          background: live ? "rgba(57,135,229,0.14)" : "transparent",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          opacity: en,
          transform: `scale(${interpolate(en, [0, 1], [0.85, 1])})`,
        }}
      >
        <div
          style={{
            fontSize: 30,
            fontWeight: 700,
            color: live ? theme.accent : theme.inkFaint,
          }}
        >
          {kind} · {fam}
        </div>
        <div
          style={{
            fontSize: 22,
            color: live ? theme.inkMuted : theme.inkFaint,
            textTransform: "uppercase",
            letterSpacing: 2,
          }}
        >
          {live ? "live now" : "roadmap"}
        </div>
      </div>
    );
  };

  return (
    <Background>
      <AbsoluteFill style={{ opacity: fade, padding: "80px 130px" }}>
        <div style={{ ...head, textAlign: "center" }}>
          <Kicker>What we built · coverage</Kicker>
          <div style={{ fontSize: 62, fontWeight: 700, marginTop: 16 }}>
            Task kind × target family
          </div>
        </div>

        <div
          style={{
            ...grid,
            marginTop: 50,
            display: "grid",
            gridTemplateColumns: `140px repeat(${FAMILIES.length}, 1fr)`,
            gap: 20,
            alignItems: "center",
          }}
        >
          <div />
          {FAMILIES.map((f) => (
            <div
              key={f}
              style={{
                textAlign: "center",
                fontSize: 27,
                color: theme.inkMuted,
                fontWeight: 600,
              }}
            >
              {f}
            </div>
          ))}
          {KINDS.map((k, ki) => (
            <React.Fragment key={k}>
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: theme.inkMuted,
                  textAlign: "right",
                  paddingRight: 8,
                }}
              >
                {k}
              </div>
              {FAMILIES.map((f, fi) => cell(k, f, ki * FAMILIES.length + fi))}
            </React.Fragment>
          ))}
        </div>

        <div
          style={{
            ...stats,
            marginTop: 46,
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 20,
          }}
        >
          {STATS.map((s) => (
            <div
              key={s.label}
              style={{
                background: theme.bgPanel,
                borderRadius: 14,
                padding: "20px 24px",
              }}
            >
              <div
                style={{
                  fontSize: s.value.length > 6 ? 30 : 48,
                  fontWeight: 800,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {s.value}
              </div>
              <div
                style={{
                  fontSize: 24,
                  color: theme.inkMuted,
                  marginTop: 4,
                }}
              >
                {s.label}
              </div>
              <div
                style={{
                  marginTop: 10,
                  display: "inline-block",
                  fontSize: 19,
                  textTransform: "uppercase",
                  letterSpacing: 2,
                  color: s.tag === "live" ? theme.accent : theme.inkFaint,
                }}
              >
                {s.tag}
              </div>
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </Background>
  );
};
