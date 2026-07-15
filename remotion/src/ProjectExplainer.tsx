import React from "react";
import { AbsoluteFill, Series } from "remotion";
import { TitleScene } from "./scenes/TitleScene";
import { PredictDecideScene } from "./scenes/PredictDecideScene";
import { DecisionCardScene } from "./scenes/DecisionCardScene";
import { CoverageScene } from "./scenes/CoverageScene";
import { ProtocolScene } from "./scenes/ProtocolScene";
import { LeaderboardScene } from "./scenes/LeaderboardScene";
import { TakeawayScene } from "./scenes/TakeawayScene";
import { theme } from "./theme";

export const SCENES = [
  { Comp: TitleScene, duration: 135 },
  { Comp: PredictDecideScene, duration: 225 },
  { Comp: DecisionCardScene, duration: 270 },
  { Comp: CoverageScene, duration: 270 },
  { Comp: ProtocolScene, duration: 255 },
  { Comp: LeaderboardScene, duration: 315 },
  { Comp: TakeawayScene, duration: 195 },
] as const;

export const EXPLAINER_DURATION = SCENES.reduce((a, s) => a + s.duration, 0);

export const ProjectExplainer: React.FC = () => (
  <AbsoluteFill style={{ background: theme.bg }}>
    <Series>
      {SCENES.map(({ Comp, duration }, i) => (
        <Series.Sequence key={i} durationInFrames={duration}>
          <Comp durationInFrames={duration} />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
