import {
  campusParts,
  campusTrees,
  roleColors,
  type CampusRole,
} from "./campus-model";
const project = (x: number, y: number, z: number) =>
  `${340 + (x - z) * 29},${230 + (x + z) * 15 - y * 36}`;

export default function CampusIllustration({
  role = "student",
}: {
  role?: CampusRole;
}) {
  return (
    <svg
      viewBox="0 0 680 480"
      className="ss-campus-illustration"
      aria-hidden="true"
    >
      <ellipse
        cx="340"
        cy="352"
        rx="250"
        ry="70"
        fill="#080716"
        opacity=".15"
      />
      {[...campusParts]
        .sort(
          (a, b) =>
            a.position[0] +
            a.position[2] +
            a.position[1] * 4 -
            (b.position[0] + b.position[2] + b.position[1] * 4),
        )
        .map((part, i) => {
          const [x, y, z] = part.position;
          const [w, h, d] = part.size;
          const p = (a: number, b: number, c: number) =>
            project(x + (a * w) / 2, y + (b * h) / 2, z + (c * d) / 2);
          const color = part.highlight === role ? roleColors[role] : part.color;
          return (
            <g key={i} fill={color} stroke={color} strokeWidth=".5">
              <polygon
                points={`${p(-1, 1, 1)} ${p(1, 1, 1)} ${p(1, -1, 1)} ${p(-1, -1, 1)}`}
              />
              <polygon
                points={`${p(1, 1, -1)} ${p(1, 1, 1)} ${p(1, -1, 1)} ${p(1, -1, -1)}`}
                style={{ filter: "brightness(.77)" }}
              />
              <polygon
                points={`${p(-1, 1, -1)} ${p(1, 1, -1)} ${p(1, 1, 1)} ${p(-1, 1, 1)}`}
                style={{ filter: "brightness(1.12)" }}
              />
            </g>
          );
        })}
      {campusTrees
        .filter(([, , z]) => z > 0)
        .map(([x, , z], i) => {
          const [cx, cy] = project(x, 0, z).split(",").map(Number);
          return (
            <g key={i}>
              <ellipse
                cx={cx + 5}
                cy={cy + 1}
                rx="18"
                ry="7"
                fill="#424451"
                opacity=".2"
              />
              <path d={`M${cx} ${cy}v-30`} stroke="#746876" strokeWidth="4" />
              <ellipse
                cx={cx}
                cy={cy - 35}
                rx="15"
                ry="22"
                fill={i % 2 ? "#708e85" : "#8ba497"}
              />
              <ellipse
                cx={cx - 4}
                cy={cy - 40}
                rx="8"
                ry="14"
                fill="#acbeb0"
                opacity=".45"
              />
            </g>
          );
        })}
    </svg>
  );
}
