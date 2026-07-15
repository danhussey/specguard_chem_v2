import React from "react";
import { Composition } from "remotion";
import { VIDEO } from "./theme";
import {
  ProjectExplainer,
  EXPLAINER_DURATION,
  SCENES,
} from "./ProjectExplainer";
import { TitleScene } from "./scenes/TitleScene";
import { PredictDecideScene } from "./scenes/PredictDecideScene";
import { DecisionCardScene } from "./scenes/DecisionCardScene";
import { CoverageScene } from "./scenes/CoverageScene";
import { ProtocolScene } from "./scenes/ProtocolScene";
import { LeaderboardScene } from "./scenes/LeaderboardScene";
import { TakeawayScene } from "./scenes/TakeawayScene";

const STANDALONE = [
  { id: "Scene-Title", Comp: TitleScene, duration: SCENES[0].duration },
  { id: "Scene-PredictDecide", Comp: PredictDecideScene, duration: SCENES[1].duration },
  { id: "Scene-DecisionCard", Comp: DecisionCardScene, duration: SCENES[2].duration },
  { id: "Scene-Coverage", Comp: CoverageScene, duration: SCENES[3].duration },
  { id: "Scene-Protocol", Comp: ProtocolScene, duration: SCENES[4].duration },
  { id: "Scene-Leaderboard", Comp: LeaderboardScene, duration: SCENES[5].duration },
  { id: "Scene-Takeaway", Comp: TakeawayScene, duration: SCENES[6].duration },
] as const;

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="ProjectExplainer"
      component={ProjectExplainer}
      durationInFrames={EXPLAINER_DURATION}
      fps={VIDEO.fps}
      width={VIDEO.width}
      height={VIDEO.height}
    />
    {STANDALONE.map(({ id, Comp, duration }) => (
      <Composition
        key={id}
        id={id}
        component={Comp as React.FC}
        durationInFrames={duration}
        fps={VIDEO.fps}
        width={VIDEO.width}
        height={VIDEO.height}
        defaultProps={{ durationInFrames: duration }}
      />
    ))}
  </>
);
