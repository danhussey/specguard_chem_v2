import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background, useEnter, useSceneFade } from "../components";
import { theme } from "../theme";

export const TakeawayScene: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const fade = useSceneFade(durationInFrames);
  const line = useEnter(8);
  const sub = useEnter(28);
  const rule = interpolate(frame, [10, 40], [0, 560], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <Background>
      <AbsoluteFill
        style={{
          opacity: fade,
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          padding: 140,
        }}
      >
        <div style={{ ...line, fontSize: 110, fontWeight: 800, lineHeight: 1.08 }}>
          Score the <span style={{ color: theme.accent }}>decision</span>,
          <br />
          not just the prediction
        </div>
        <div
          style={{
            height: 4,
            width: rule,
            background: theme.accent,
            borderRadius: 2,
            margin: "48px 0",
          }}
        />
        <div
          style={{
            ...sub,
            maxWidth: 1360,
            fontSize: 44,
            color: theme.inkMuted,
            lineHeight: 1.4,
          }}
        >
          A decision-centric benchmark for the constrained, budget-limited choice a
          project actually makes — open harness, living leaderboard, one shared set
          of frozen cards.
        </div>
        <div
          style={{
            ...sub,
            marginTop: 60,
            fontSize: 30,
            color: theme.inkFaint,
            letterSpacing: 2,
          }}
        >
          Bring your system · retrospective audit, not a molecule generator or clinical tool
        </div>
      </AbsoluteFill>
    </Background>
  );
};
