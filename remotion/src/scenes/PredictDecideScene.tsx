import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background, Kicker, Panel, useEnter, useSceneFade } from "../components";
import { theme } from "../theme";

const COLS = 12;
const ROWS = 6;
const TOTAL = COLS * ROWS;
// Ten "picked" cells scattered across the pool.
const PICKED = new Set([4, 9, 18, 23, 31, 40, 47, 55, 61, 68]);

export const PredictDecideScene: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = useSceneFade(durationInFrames);
  const head = useEnter(4);
  const left = useEnter(26);
  const right = useEnter(38);

  const dot = 44;
  const gap = 16;
  const gridW = COLS * dot + (COLS - 1) * gap;

  return (
    <Background>
      <AbsoluteFill style={{ opacity: fade, padding: "84px 110px" }}>
        <div style={{ ...head, textAlign: "center" }}>
          <Kicker color={theme.utility}>The problem</Kicker>
          <div style={{ fontSize: 62, fontWeight: 700, marginTop: 16 }}>
            A prediction benchmark can&#39;t score a decision
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: 48,
            marginTop: 62,
            justifyContent: "center",
            alignItems: "stretch",
          }}
        >
          <Panel accent={theme.border} style={{ ...left, width: 690 }}>
            <div style={{ fontSize: 30, color: theme.inkFaint, fontWeight: 600 }}>
              Most benchmarks
            </div>
            <div style={{ fontSize: 40, fontWeight: 700, marginTop: 6 }}>
              Predict a property
            </div>
            <div style={{ fontSize: 28, color: theme.inkMuted, marginTop: 10 }}>
              Score one held-out label
            </div>

            <div
              style={{
                marginTop: 40,
                display: "flex",
                alignItems: "baseline",
                gap: 24,
              }}
            >
              <div>
                <div style={{ fontSize: 24, color: theme.inkFaint }}>
                  predicted
                </div>
                <div style={{ fontSize: 76, fontWeight: 800 }}>6.42</div>
              </div>
              <div style={{ fontSize: 40, color: theme.inkFaint }}>vs</div>
              <div>
                <div style={{ fontSize: 24, color: theme.inkFaint }}>actual</div>
                <div
                  style={{
                    fontSize: 76,
                    fontWeight: 800,
                    color: theme.inkMuted,
                  }}
                >
                  6.51
                </div>
              </div>
            </div>
            <div style={{ fontSize: 27, color: theme.inkFaint, marginTop: 30 }}>
              RMSE · AUC · one compound at a time
            </div>
          </Panel>

          <Panel accent={theme.accent} style={{ ...right, width: 830 }}>
            <div style={{ fontSize: 30, color: theme.accent, fontWeight: 600 }}>
              SpecGuard-Chem
            </div>
            <div style={{ fontSize: 40, fontWeight: 700, marginTop: 6 }}>
              Decide what to test next
            </div>
            <div style={{ fontSize: 28, color: theme.inkMuted, marginTop: 10 }}>
              Pick k from the pool, then reveal
            </div>

            <div
              style={{
                marginTop: 34,
                width: gridW,
                display: "grid",
                gridTemplateColumns: `repeat(${COLS}, ${dot}px)`,
                gap,
              }}
            >
              {Array.from({ length: TOTAL }).map((_, i) => {
                const picked = PICKED.has(i);
                const pop = spring({
                  frame: frame - (52 + [...PICKED].indexOf(i) * 6),
                  fps,
                  config: { damping: 200 },
                });
                const scale = picked ? interpolate(pop, [0, 1], [0.7, 1]) : 1;
                return (
                  <div
                    key={i}
                    style={{
                      width: dot,
                      height: dot,
                      borderRadius: 10,
                      background: picked ? theme.accent : theme.border,
                      opacity: picked ? pop : 0.55,
                      transform: `scale(${scale})`,
                    }}
                  />
                );
              })}
            </div>
            <div style={{ fontSize: 27, color: theme.inkMuted, marginTop: 30 }}>
              <span style={{ color: theme.accent, fontWeight: 700 }}>
                budget k = 10
              </span>{" "}
              · hard constraints · hidden activity
            </div>
          </Panel>
        </div>
      </AbsoluteFill>
    </Background>
  );
};
