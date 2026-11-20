import React from "react";
import { BOTTOM_BAR_HEIGHT, WIDTH } from "./layout";

// Bottom 380px black caption band. Captions.tsx draws on top of it.
export const BottomBar: React.FC = () => (
  <div
    style={{
      position: "absolute",
      bottom: 0,
      left: 0,
      width: WIDTH,
      height: BOTTOM_BAR_HEIGHT,
      backgroundColor: "#000000",
    }}
  />
);
