export const theme = {
  bg: "#0e1116",
  bgPanel: "#161b22",
  ink: "#f2f4f8",
  inkMuted: "#9aa4b2",
  inkFaint: "#5b6572",
  border: "#232a34",
  // categorical roles, consistent with the project's diagrams
  neutral: "#8b94a3",
  systems: "#8a7ff0", // purple
  compliance: "#1baf7a", // teal/green
  utility: "#eb6834", // coral
  qsar: "#3987e5", // blue
  llm: "#eb6834", // coral
  oracle: "#8b94a3", // gray control
  accent: "#3987e5",
} as const;

export const font =
  'Inter, "Helvetica Neue", "SF Pro Display", system-ui, -apple-system, Arial, sans-serif';

export const VIDEO = {
  width: 1920,
  height: 1080,
  fps: 30,
} as const;
