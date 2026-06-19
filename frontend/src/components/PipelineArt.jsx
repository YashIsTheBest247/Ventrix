/**
 * Animated "live pipeline" hero art — Velora-style line icons on a dashed rail.
 * Nodes map to what the app actually does: discover → process → remind → notes.
 * Motion: the process gear spins, the remind bell rings, and a dot travels the rail.
 */
export default function PipelineArt() {
  const railY = 96;
  const nodes = [
    { x: 90, label: "discover", icon: GlobeIcon },
    { x: 290, label: "process", icon: GearIcon },
    { x: 490, label: "remind", icon: BellIcon },
    { x: 660, label: "notes", icon: NoteIcon },
  ];
  const x0 = nodes[0].x;
  const x1 = nodes[nodes.length - 1].x;

  return (
    <div className="pipeline">
      <svg viewBox="55 52 630 128" className="pipeline-svg" role="img" aria-label="live pipeline">
        <line x1={x0} y1={railY} x2={x1} y2={railY} className="rail" />

        <circle r="7" className="traveller">
          <animateMotion
            dur="3.4s"
            repeatCount="indefinite"
            keyPoints="0;1"
            keyTimes="0;1"
            calcMode="linear"
            path={`M${x0},${railY} L${x1},${railY}`}
          />
        </circle>

        {nodes.map(({ x, label, icon: Icon }) => (
          <g key={label}>
            <Icon x={x} y={railY} />
            <text x={x} y={railY + 66} className="node-label">
              {label}
            </text>
          </g>
        ))}
      </svg>

      <div className="pipeline-caption">
        <div className="pipeline-title">live pipeline</div>
        <div className="pipeline-sub">scrape · match · remind · note</div>
      </div>
    </div>
  );
}

/* ── big line-drawn icons (centered on x,y) ──────────── */

function GlobeIcon({ x, y }) {
  return (
    <g className="ico">
      <circle cx={x} cy={y} r="22" />
      <ellipse cx={x} cy={y} rx="9" ry="22" />
      <line x1={x - 22} y1={y} x2={x + 22} y2={y} />
      <path d={`M${x - 19} ${y - 11} Q${x} ${y - 3} ${x + 19} ${y - 11}`} />
      <path d={`M${x - 19} ${y + 11} Q${x} ${y + 3} ${x + 19} ${y + 11}`} />
    </g>
  );
}

function GearIcon({ x, y }) {
  // 8-tooth gear, absolute coords so CSS rotate spins it in place.
  const teeth = Array.from({ length: 8 }, (_, i) => {
    const a = (i * Math.PI) / 4;
    return (
      <line
        key={i}
        x1={x + Math.cos(a) * 15}
        y1={y + Math.sin(a) * 15}
        x2={x + Math.cos(a) * 22}
        y2={y + Math.sin(a) * 22}
      />
    );
  });
  return (
    <g className="ico gear spin" style={{ transformOrigin: `${x}px ${y}px` }}>
      <circle cx={x} cy={y} r="11" />
      <circle cx={x} cy={y} r="4" className="filled" />
      {teeth}
    </g>
  );
}

function BellIcon({ x, y }) {
  // gentle ring, pivoting from the top knob.
  return (
    <g className="ico bell ring" style={{ transformOrigin: `${x}px ${y - 24}px` }}>
      <circle cx={x} cy={y - 22} r="2.4" className="filled" />
      <path
        d={`M${x - 16} ${y + 9}
            C${x - 16} ${y - 9} ${x - 9} ${y - 20} ${x} ${y - 20}
            C${x + 9} ${y - 20} ${x + 16} ${y - 9} ${x + 16} ${y + 9}
            L${x + 19} ${y + 13} L${x - 19} ${y + 13} Z`}
      />
      <path d={`M${x - 4} ${y + 15} a4 4 0 0 0 8 0`} />
    </g>
  );
}

function NoteIcon({ x, y }) {
  // document with a folded corner + text lines.
  return (
    <g className="ico">
      <path
        d={`M${x - 15} ${y - 20}
            H${x + 7} L${x + 16} ${y - 11}
            V${y + 20} H${x - 15} Z`}
      />
      <path d={`M${x + 7} ${y - 20} V${y - 11} H${x + 16}`} />
      <line x1={x - 9} y1={y - 4} x2={x + 9} y2={y - 4} />
      <line x1={x - 9} y1={y + 3} x2={x + 9} y2={y + 3} />
      <line x1={x - 9} y1={y + 10} x2={x + 2} y2={y + 10} />
    </g>
  );
}
