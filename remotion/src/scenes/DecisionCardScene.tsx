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

type Row = {
  tag: string;
  detail: string;
  note: string;
  accent: string;
};

const ROWS: Row[] = [
  { tag: "Support set", detail: "50 tested compounds", note: "activity visible", accent: theme.compliance },
  { tag: "Candidate pool", detail: "≈290 candidates", note: "activity hidden", accent: theme.utility },
  { tag: "Hard constraints", detail: "7 medicinal-chem rules", note: "schema + chemistry", accent: theme.systems },
  { tag: "Budget", detail: "k = 10 picks", note: "finite testing", accent: theme.accent },
];

export const DecisionCardScene: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = useSceneFade(durationInFrames);
  const head = useEnter(4);
  const out = useEnter(70);

  return (
    <Background>
      <AbsoluteFill style={{ opacity: fade, padding: "80px 110px" }}>
        <div style={{ ...head, textAlign: "center" }}>
          <Kicker>What we built · the decision card</Kicker>
          <div style={{ fontSize: 62, fontWeight: 700, marginTop: 16 }}>
            One frozen decision card
          </div>
        </div>

        <div
          style={{
            maxWidth: 1180,
            margin: "54px auto 0",
            background: theme.bgPanel,
            border: `2px solid ${theme.border}`,
            borderRadius: 24,
            padding: 40,
            boxShadow: "0 24px 60px rgba(0,0,0,0.35)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 26,
            }}
          >
            <div style={{ fontSize: 30, fontWeight: 600, color: theme.inkMuted }}>
              CARA_LO · CHEMBL2328568 · IC50
            </div>
            <div
              style={{
                fontSize: 24,
                color: theme.inkFaint,
                border: `2px solid ${theme.border}`,
                borderRadius: 999,
                padding: "6px 18px",
              }}
            >
              lead optimisation
            </div>
          </div>

          <div style={{ display: "grid", gap: 16 }}>
            {ROWS.map((r, i) => {
              const en = spring({
                frame: frame - (22 + i * 12),
                fps,
                config: { damping: 200, mass: 0.8 },
              });
              return (
                <div
                  key={r.tag}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 24,
                    background: theme.bg,
                    borderLeft: `6px solid ${r.accent}`,
                    borderRadius: 12,
                    padding: "22px 28px",
                    opacity: en,
                    transform: `translateX(${interpolate(en, [0, 1], [-28, 0])}px)`,
                  }}
                >
                  <div
                    style={{
                      width: 300,
                      fontSize: 32,
                      fontWeight: 700,
                      color: r.accent,
                    }}
                  >
                    {r.tag}
                  </div>
                  <div style={{ flex: 1, fontSize: 32 }}>{r.detail}</div>
                  <div
                    style={{
                      fontSize: 25,
                      color: theme.inkMuted,
                      border: `2px solid ${theme.border}`,
                      borderRadius: 999,
                      padding: "6px 18px",
                    }}
                  >
                    {r.note}
                  </div>
                </div>
              );
            })}
          </div>

          <div
            style={{
              ...out,
              marginTop: 30,
              textAlign: "center",
              fontSize: 30,
              color: theme.inkMuted,
            }}
          >
            System returns{" "}
            <span style={{ color: theme.ink, fontWeight: 700 }}>
              10 ranked candidate IDs
            </span>{" "}
            — then hidden activity is revealed for scoring
          </div>
        </div>
      </AbsoluteFill>
    </Background>
  );
};
