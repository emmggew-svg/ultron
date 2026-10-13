"use client";

import dynamic from "next/dynamic";

const UltronOrb = dynamic(() => import("./UltronOrb"), { ssr: false });

export default function UltronScene() {
  return (
    <div className="stage">
      <UltronOrb />
      <div className="title">ULTRON</div>
    </div>
  );
}
