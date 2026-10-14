import path from "node:path";
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setChromiumOpenGlRenderer("angle");
// Use a local Chromium when one is provided (e.g. offline CI); otherwise Remotion downloads its own.
if (process.env.REMOTION_BROWSER) Config.setBrowserExecutable(process.env.REMOTION_BROWSER);
// Remotion's bundler does not read tsconfig paths; mirror the @/ alias here.
Config.overrideWebpackConfig((c) => ({
  ...c,
  resolve: { ...c.resolve, alias: { ...(c.resolve?.alias ?? {}), "@": path.resolve(process.cwd(), "src") } },
}));
