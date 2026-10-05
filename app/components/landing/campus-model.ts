export type CampusRole = "student" | "professor" | "administration";
export type CampusPart = {
  position: [number, number, number];
  size: [number, number, number];
  color: string;
  highlight?: CampusRole;
};
// Original fictional campus. Shared dimensions for the static SVG and the WebGL model.
export const campusParts: CampusPart[] = [
  { position: [0, -0.36, 0], size: [10, 0.6, 8], color: "#777387" },
  { position: [0, -0.02, 0], size: [10, 0.1, 8], color: "#d5d2de" },
  { position: [0, 0.05, 1.2], size: [1.7, 0.06, 5.6], color: "#eeebf5" },
  { position: [0, 0.05, 0.8], size: [8.9, 0.06, 1.1], color: "#eeebf5" },
  { position: [0, 0.12, -1.4], size: [5.2, 0.2, 3.2], color: "#eeebf5" },
  {
    position: [0, 1.55, -1.9],
    size: [4.5, 2.7, 2.1],
    color: "#e9e5f0",
    highlight: "administration",
  },
  {
    position: [0, 1.45, -0.82],
    size: [3.9, 2.2, 0.06],
    color: "#66638d",
    highlight: "professor",
  },
  { position: [0, 2.95, -1.8], size: [4.9, 0.22, 2.6], color: "#f8f5ff" },
  { position: [0, 3.13, -2.05], size: [4.4, 0.15, 1.8], color: "#a2a0b9" },
  { position: [0, 0.13, -0.08], size: [2.4, 0.15, 0.95], color: "#e9e5f0" },
  { position: [0, 0.23, -0.35], size: [2.4, 0.15, 0.65], color: "#f8f5ff" },
  {
    position: [-3.35, 0.82, 0.9],
    size: [2.15, 1.55, 2.75],
    color: "#bab4d4",
    highlight: "student",
  },
  { position: [-3.35, 1.68, 0.9], size: [2.4, 0.2, 3], color: "#f1edf8" },
  { position: [-3.35, 1.8, 0.9], size: [2.1, 0.08, 2.65], color: "#89869f" },
  {
    position: [-2.25, 0.92, 0.9],
    size: [0.05, 1.12, 2.35],
    color: "#5a617c",
    highlight: "student",
  },
  {
    position: [3.05, 0.6, -0.1],
    size: [1.8, 1.1, 2.3],
    color: "#d1cadf",
    highlight: "professor",
  },
  { position: [3.05, 1.24, -0.1], size: [2.1, 0.18, 2.6], color: "#f1edf8" },
  { position: [3.05, 0.7, 1.07], size: [1.4, 0.72, 0.05], color: "#687189" },
  { position: [2.8, 0.08, 2.55], size: [2.75, 0.12, 1.6], color: "#929f95" },
  { position: [-1.8, 0.08, 2.55], size: [1.3, 0.12, 1.6], color: "#929f95" },
  ...[-1.7, -0.85, 0, 0.85, 1.7].map((x): CampusPart => ({
    position: [x, 1.5, -0.54],
    size: [0.19, 2.55, 0.24],
    color: "#f5f1fa",
  })),
  ...[-1.65, -0.55, 0.55, 1.65].map((x): CampusPart => ({
    position: [x, 2.25, -2.98],
    size: [0.6, 0.65, 0.03],
    color: "#74728d",
  })),
  ...[-0.1, 0.7, 1.5, 2.1].map((z): CampusPart => ({
    position: [-2.2, 0.92, z],
    size: [0.09, 1.18, 0.08],
    color: "#e8e2f0",
  })),
  ...[-0.55, 0.55].map((x): CampusPart => ({
    position: [x, 0.09, 2.1],
    size: [0.035, 0.025, 3.5],
    color: "#aaa1c7",
  })),
  ...[1.55, 2.45].map((z): CampusPart => ({
    position: [1.25, 0.25, z],
    size: [0.3, 0.3, 0.65],
    color: "#777087",
  })),
];
export const campusTrees: [number, number, number][] = [
  [-4.15, 0, -2.7],
  [-3.3, 0, -2.9],
  [3.35, 0, -2.7],
  [4.15, 0, -2.4],
  [2, 0, 2.7],
  [3.2, 0, 2.7],
  [4.15, 0, 2.7],
  [-1.8, 0, 2.7],
  [-4, 0, 3],
];
export const roleColors: Record<CampusRole, string> = {
  student: "#8d80d9",
  professor: "#839faa",
  administration: "#ac91ce",
};
