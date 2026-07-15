import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Background, Kicker, useEnter, useSceneFade } from "../components";
import { font, theme } from "../theme";

export const TitleScene: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const fade = useSceneFade(durationInFrames);
  const title = useEnter(6);
  const sub = useEnter(20);
  const rule = interpolate(frame, [24, 54], [0, 720], {
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
          padding: 120,
        }}
      >
        <div style={{ ...title }}>
          <Kicker>A benchmark for constrained molecular selection</Kicker>
          <div
            style={{
              fontSize: 132,
              fontWeight: 800,
              marginTop: 24,
              letterSpacing: -2,
              lineHeight: 1.02,
            }}
          >
            SpecGuard&#8209;Chem{" "}
            <span style={{ color: theme.accent }}>v2</span>
          </div>
        </div>
        <div
          style={{
            height: 4,
            width: rule,
            background: theme.accent,
            borderRadius: 2,
            margin: "44px 0",
          }}
        />
        <div
          style={{
            ...sub,
            maxWidth: 1280,
            fontSize: 46,
            fontWeight: 400,
            lineHeight: 1.35,
            color: theme.inkMuted,
            fontFamily: font,
          }}
        >
          Drug projects constantly decide which compounds to test next —{" "}
          <span style={{ color: theme.ink }}>
            but no benchmark measures whether those decisions are good.
          </span>
        </div>
      </AbsoluteFill>
    </Background>
  );
};
