import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { font, theme } from "./theme";

export const Background: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      background: theme.bg,
      fontFamily: font,
      color: theme.ink,
      overflow: "hidden",
    }}
  >
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage:
          "radial-gradient(circle at 50% 0%, rgba(57,135,229,0.10), transparent 55%)",
      }}
    />
    {children}
  </div>
);

// Fade + rise entrance driven by a spring, delayed by `delay` frames.
export const useEnter = (delay = 0, damping = 200) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({
    frame: frame - delay,
    fps,
    config: { damping, mass: 0.8, stiffness: 120 },
  });
  return {
    opacity: s,
    transform: `translateY(${interpolate(s, [0, 1], [24, 0])}px)`,
  };
};

// Fade the whole scene in at the start and out near the end.
export const useSceneFade = (durationInFrames: number, pad = 12) => {
  const frame = useCurrentFrame();
  return interpolate(
    frame,
    [0, pad, durationInFrames - pad, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
};

export const Kicker: React.FC<{ children: React.ReactNode; color?: string }> = ({
  children,
  color = theme.accent,
}) => (
  <div
    style={{
      textTransform: "uppercase",
      letterSpacing: 6,
      fontSize: 24,
      fontWeight: 600,
      color,
    }}
  >
    {children}
  </div>
);

export const Panel: React.FC<{
  style?: React.CSSProperties;
  accent?: string;
  children: React.ReactNode;
}> = ({ style, accent, children }) => (
  <div
    style={{
      background: theme.bgPanel,
      border: `2px solid ${accent ?? theme.border}`,
      borderRadius: 24,
      padding: 36,
      boxShadow: "0 24px 60px rgba(0,0,0,0.35)",
      ...style,
    }}
  >
    {children}
  </div>
);
