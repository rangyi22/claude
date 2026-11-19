// Remotion CLI config. Render options (codec, size, props) are passed
// explicitly by md2short/render.py so the subprocess command is the contract.
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setPublicDir("public");
