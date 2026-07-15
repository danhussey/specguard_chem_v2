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

type Step = { name: string; role: string; color: string; h: number; dashed?: boolean };

// Heights ordered by real feasible utility (similarity < guarded LLM < QSAR < oracle).
const STEPS: Step[] = [
  { name: "Random", role: "floor", color: theme.neutral, h: 92 },
  { name: "Rules", role: "desirability", color: theme.neutral, h: 142 },
  { name: "Similarity", role: "strong simple", color: theme.neutral, h: 190 },
  { name: "Guarded LLM", role: "frontier + guard", color: theme.llm, h: 255 },
  { name: "QSAR", role: "best deployable", color: theme.qsar, h: 300 },
  { name: "Oracle", role: "upper bound", color: theme.oracle, h: 406, dashed: true },
];

const METRICS = ["Feasible utility", "NDCG@k", "Constrained regret", "Compliance"];

const BASE_Y = 820;
const BAR_W = 200;
const CENTERS = [230, 522, 814, 1106, 1398, 1690];

export const ProtocolScene: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = useSceneFade(durationInFrames);
  const head = useEnter(4);
  const chips = useEnter(20);
  const note = useEnter(96);

  return (
    <Background>
      <AbsoluteFill style={{ opacity: fade }}>
        <div style={{ ...head, textAlign: "center", paddingTop: 76 }}>
          <Kicker>What we built · evaluation</Kicker>
          <div style={{ fontSize: 62, fontWeight: 700, marginTop: 14 }}>
            A baseline ladder from random to oracle
          </div>
        </div>

        <div
          style={{
            ...chips,
            display: "flex",
            gap: 18,
            justifyContent: "center",
            marginTop: 26,
          }}
        >
          {METRICS.map((m) => (
            <div
              key={m}
              style={{
                fontSize: 26,
                color: theme.inkMuted,
                border: `2px solid ${theme.border}`,
                background: theme.bgPanel,
                borderRadius: 999,
                padding: "10px 26px",
              }}
            >
              {m}
            </div>
          ))}
        </div>

        <svg
          width={1920}
          height={1080}
          viewBox="0 0 1920 1080"
          style={{ position: "absolute", inset: 0 }}
        >
          <line
            x1={110}
            y1={BASE_Y}
            x2={1810}
            y2={BASE_Y}
            stroke={theme.border}
            strokeWidth={2}
          />
          {STEPS.map((s, i) => {
            const grow = spring({
              frame: frame - (34 + i * 9),
              fps,
              config: { damping: 200, mass: 0.9 },
            });
            const h = s.h * grow;
            const x = CENTERS[i] - BAR_W / 2;
            const top = BASE_Y - h;
            return (
              <g key={s.name}>
                <rect
                  x={x}
                  y={top}
                  width={BAR_W}
                  height={h}
                  rx={12}
                  fill={s.dashed ? "transparent" : s.color}
                  opacity={s.dashed ? 1 : 0.92}
                  stroke={s.dashed ? s.color : "none"}
                  strokeWidth={s.dashed ? 3 : 0}
                  strokeDasharray={s.dashed ? "12 9" : undefined}
                />
                <text
                  x={CENTERS[i]}
                  y={top - 18}
                  textAnchor="middle"
                  fill={s.color}
                  fontSize={24}
                  fontWeight={600}
                  opacity={grow}
                >
                  {s.role}
                </text>
                <text
                  x={CENTERS[i]}
                  y={BASE_Y + 44}
                  textAnchor="middle"
                  fill={theme.ink}
                  fontSize={30}
                  fontWeight={700}
                >
                  {s.name}
                </text>
              </g>
            );
          })}
        </svg>

        <div
          style={{
            ...note,
            position: "absolute",
            bottom: 58,
            width: "100%",
            textAlign: "center",
            fontSize: 28,
            color: theme.inkMuted,
          }}
        >
          Paired-bootstrap confidence intervals · raw-vs-repaired attribution so
          guardrails aren&#39;t credited as chemical judgment
        </div>
      </AbsoluteFill>
    </Background>
  );
};
