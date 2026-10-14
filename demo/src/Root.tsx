import { Composition } from "remotion";
import { Demo } from "./Demo";

export const Root: React.FC = () => (
  <Composition id="Demo" component={Demo} durationInFrames={2400} fps={30} width={1280} height={720} />
);
