import type { NextConfig } from "next";

const config: NextConfig = {
  ...(process.env.NEXT_PUBLIC_DEMO_MODE === "1" ? { output: "export" } : {}),
};

export default config;
