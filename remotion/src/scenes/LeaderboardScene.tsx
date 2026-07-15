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

type Row = { label: string; value: number; color: string; group: string };

const ROWS: Row[] = [
  { label: "Oracle (upper bound)", value: 89.022, color: theme.oracle, group: "Oracle control" },
  { label: "QSAR linear SVR", value: 81.382, color: theme.qsar, group: "QSAR baseline" },
  { label: "QSAR gradient boosting", value: 80.888, color: theme.qsar, group: "QSAR baseline" },
  { label: "QSAR random forest", value: 80.634, color: theme.qsar, group: "QSAR baseline" },
  { label: "LLM + validator", value: 78.188, color: theme.llm, group: "Guarded LLM" },
  { label: "LLM + tools + validator", value: 77.688, color: theme.llm, group: "Guarded LLM" },
  { label: "Similarity baseline", value: 73.603, color: theme.neutral, group: "Simple baseline" },
];

const LEGEND = [
  { label: "Oracle control", color: theme.oracle },
  { label: "QSAR baseline", color: theme.qsar },
  { label: "Guarded LLM", color: theme.llm },
  { label: "Simple baseline", color: theme.neutral },
];

const BAR_X = 620;
const MAX = 95;
const UNIT = 1120 / MAX;
const ROW_H = 60;
const ROW_STEP = 88;
const TOP = 322;

export const LeaderboardScene: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = useSceneFade(durationInFrames);
  const head = useEnter(4);
  const note = useEnter(110);

  return (
    <Background>
      <AbsoluteFill style={{ opacity: fade, padding: "80px 100px" }}>
        <div style={{ ...head }}>
          <Kicker>What we found · 50 lead-optimisation assays · k = 10</Kicker>
          <div style={{ fontSize: 60, fontWeight: 700, marginTop: 14 }}>
            Feasible utility — classical baselines still lead
          </div>
          <div style={{ display: "flex", gap: 40, marginTop: 22 }}>
            {LEGEND.map((l) => (
              <div
                key={l.label}
                style={{ display: "flex", alignItems: "center", gap: 12 }}
              >
                <div
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: 6,
                    background: l.color,
                  }}
                />
                <span style={{ fontSize: 27, color: theme.inkMuted }}>
                  {l.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        <svg
          width={1920}
          height={1080}
          viewBox="0 0 1920 1080"
          style={{ position: "absolute", inset: 0 }}
        >
          {ROWS.map((r, i) => {
            const y = TOP + i * ROW_STEP;
            const grow = spring({
              frame: frame - (24 + i * 8),
              fps,
              config: { damping: 200, mass: 0.9 },
            });
            const w = r.value * UNIT * grow;
            const shown = (r.value * grow).toFixed(1);
            const isOracle = i === 0;
            return (
              <g key={r.label}>
                <text
                  x={BAR_X - 30}
                  y={y + ROW_H / 2 + 12}
                  textAnchor="end"
                  fill={theme.ink}
                  fontSize={34}
                  fontWeight={500}
                >
                  {r.label}
                </text>
                <rect
                  x={BAR_X}
                  y={y}
                  width={w}
                  height={ROW_H}
                  rx={10}
                  fill={r.color}
                  opacity={isOracle ? 0.65 : 1}
                  stroke={isOracle ? theme.oracle : "none"}
                  strokeWidth={isOracle ? 3 : 0}
                  strokeDasharray={isOracle ? "10 8" : undefined}
                />
                <text
                  x={BAR_X + w + 22}
                  y={y + ROW_H / 2 + 12}
                  fill={theme.ink}
                  fontSize={36}
                  fontWeight={700}
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {shown}
                </text>
              </g>
            );
          })}
        </svg>

        <div
          style={{
            ...note,
            position: "absolute",
            left: 100,
            bottom: 70,
            fontSize: 32,
            color: theme.inkMuted,
            maxWidth: 1720,
            lineHeight: 1.4,
          }}
        >
          A calibration point for "LLMs for chemistry": guarded frontier LLMs are
          useful, but cheap per-card{" "}
          <span style={{ color: theme.qsar, fontWeight: 700 }}>QSAR</span> still
          wins by 3.2 utility points (95% CI 1.9–4.7), with the{" "}
          <span style={{ color: theme.oracle, fontWeight: 700 }}>oracle</span>{" "}
          ~7.6 points further ahead.
        </div>
      </AbsoluteFill>
    </Background>
  );
};
