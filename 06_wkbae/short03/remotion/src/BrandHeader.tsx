import React from "react";
import { Img, staticFile } from "remotion";
import { HEADER_HEIGHT, HEADER_LOGO_HEIGHT, HEADER_SAFE_MARGIN, WIDTH } from "./layout";

// Top 360px black band = 140px safe margin + 220px logo (img/header_logo.png).
export const BrandHeader: React.FC = () => (
  <div
    style={{
      position: "absolute",
      top: 0,
      left: 0,
      width: WIDTH,
      height: HEADER_HEIGHT,
      backgroundColor: "#000000",
    }}
  >
    <div
      style={{
        position: "absolute",
        top: HEADER_SAFE_MARGIN,
        left: 0,
        width: WIDTH,
        height: HEADER_LOGO_HEIGHT,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Img
        src={staticFile("img/header_logo.png")}
        style={{ height: HEADER_LOGO_HEIGHT, maxWidth: WIDTH, objectFit: "contain" }}
      />
    </div>
  </div>
);
