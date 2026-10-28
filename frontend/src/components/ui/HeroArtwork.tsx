import { type SVGProps } from "react";

interface HeroArtworkProps extends SVGProps<SVGSVGElement> {
  className?: string;
}

/**
 * HeroArtwork: "The Brutalist Arena of Verified Intelligence"
 * Official PragyaX Brand Palette illustration with isometric monolithic slabs,
 * crisp 2px deep plum wireframes (#28122F), warm amber (#E7962B), golden highlight (#F5B942),
 * and secondary plum (#63324F) architectural accent planes, plus dynamic HUD tags.
 */
export function HeroArtwork({ className = "", ...props }: HeroArtworkProps) {
  return (
    <div className={`hero-artwork-wrap ${className}`.trim()}>
      <svg
        viewBox="0 0 600 520"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="hero-artwork-svg"
        aria-hidden="true"
        role="img"
        {...props}
      >
        <defs>
          {/* Brutalist Hard Shadow Filter in Deep Plum */}
          <filter id="brutalShadow" x="-10%" y="-10%" width="130%" height="130%">
            <feDropShadow dx="6" dy="6" stdDeviation="0" floodColor="#28122F" floodOpacity="1" />
          </filter>
          <filter id="brutalShadowSm" x="-10%" y="-10%" width="130%" height="130%">
            <feDropShadow dx="3" dy="3" stdDeviation="0" floodColor="#28122F" floodOpacity="1" />
          </filter>

          {/* Grid pattern */}
          <pattern id="brutalGrid" width="30" height="30" patternUnits="userSpaceOnUse">
            <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#E6E1D6" strokeWidth="1" strokeDasharray="2 3" />
          </pattern>
        </defs>

        {/* Ambient Brutalist Grid Matrix */}
        <rect x="20" y="20" width="560" height="480" fill="url(#brutalGrid)" stroke="#28122F" strokeWidth="2" />
        
        {/* Crosshair coordinate markers */}
        <g stroke="#28122F" strokeWidth="1.5">
          <line x1="20" y1="260" x2="40" y2="260" />
          <line x1="560" y1="260" x2="580" y2="260" />
          <line x1="300" y1="20" x2="300" y2="40" />
          <line x1="300" y1="480" x2="300" y2="500" />
          <circle cx="300" cy="260" r="190" stroke="#28122F" strokeWidth="1.5" strokeDasharray="4 6" fill="none" />
          <circle cx="300" cy="260" r="130" stroke="#E7962B" strokeWidth="1.5" strokeDasharray="2 4" fill="none" opacity="0.8" />
        </g>

        {/* Diagonal Perspective Rays */}
        <line x1="40" y1="40" x2="200" y2="180" stroke="#28122F" strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />
        <line x1="560" y1="40" x2="400" y2="180" stroke="#28122F" strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />
        <line x1="40" y1="480" x2="200" y2="340" stroke="#28122F" strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />
        <line x1="560" y1="480" x2="400" y2="340" stroke="#28122F" strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />

        {/* Isometric Platform / Base Slabs */}
        <g filter="url(#brutalShadow)">
          {/* Lower Base Slab */}
          <polygon
            points="100,380 300,470 500,380 300,290"
            fill="#EFECE4"
            stroke="#28122F"
            strokeWidth="2.5"
          />
          {/* Lower Slab Thickness Side 1 */}
          <polygon
            points="100,380 300,470 300,490 100,400"
            fill="#28122F"
          />
          {/* Lower Slab Thickness Side 2 */}
          <polygon
            points="300,470 500,380 500,400 300,490"
            fill="#431E4F"
          />

          {/* Middle Slab (Warm Amber Active Arena Stage) */}
          <polygon
            points="140,340 300,410 460,340 300,270"
            fill="#E7962B"
            stroke="#28122F"
            strokeWidth="2.5"
          />
          <polygon
            points="140,340 300,410 300,422 140,352"
            fill="#28122F"
          />
          <polygon
            points="300,410 460,340 460,352 300,422"
            fill="#36183F"
          />
        </g>

        {/* Central Monolith / AI Core Obelisk */}
        <g filter="url(#brutalShadow)">
          {/* Left Facet: Pure White with Tech Lines */}
          <polygon
            points="300,100 210,210 210,330 300,240"
            fill="#FFFFFF"
            stroke="#28122F"
            strokeWidth="2.5"
          />
          {/* Right Facet: Secondary Plum */}
          <polygon
            points="300,100 390,210 390,330 300,240"
            fill="#63324F"
            stroke="#28122F"
            strokeWidth="2.5"
          />
          {/* Top Cap Facet: Golden Highlight */}
          <polygon
            points="300,100 250,60 300,20 350,60"
            fill="#F5B942"
            stroke="#28122F"
            strokeWidth="2.5"
          />
          <polygon
            points="210,210 250,60 300,100"
            fill="#F8F6F1"
            stroke="#28122F"
            strokeWidth="2"
          />
          <polygon
            points="390,210 350,60 300,100"
            fill="#4E253E"
            stroke="#28122F"
            strokeWidth="2"
          />
        </g>

        {/* Tech markings on Left Facet */}
        <g stroke="#28122F" strokeWidth="1.5">
          <line x1="235" y1="230" x2="275" y2="190" />
          <line x1="235" y1="260" x2="275" y2="220" />
          <line x1="235" y1="290" x2="275" y2="250" />
        </g>

        {/* Floating Satellite Cubes / Nodes */}
        {/* Left Node: 1v1 Battle Node */}
        <g filter="url(#brutalShadowSm)">
          <polygon points="90,190 135,170 180,190 135,210" fill="#E7962B" stroke="#28122F" strokeWidth="2" />
          <polygon points="90,190 135,210 135,250 90,230" fill="#28122F" stroke="#28122F" strokeWidth="2" />
          <polygon points="135,210 180,190 180,230 135,250" fill="#FFFFFF" stroke="#28122F" strokeWidth="2" />
        </g>

        {/* Right Node: Verified Credential Node */}
        <g filter="url(#brutalShadowSm)">
          <polygon points="420,180 465,160 510,180 465,200" fill="#FFFFFF" stroke="#28122F" strokeWidth="2" />
          <polygon points="420,180 465,200 465,240 420,220" fill="#63324F" stroke="#28122F" strokeWidth="2" />
          <polygon points="465,200 510,180 510,220 465,240" fill="#28122F" stroke="#28122F" strokeWidth="2" />
        </g>

        {/* Vector Connector Lines */}
        <path d="M 180 210 L 210 240" stroke="#28122F" strokeWidth="2" strokeDasharray="3 3" />
        <path d="M 420 200 L 390 230" stroke="#28122F" strokeWidth="2" strokeDasharray="3 3" />

        {/* Brutalist Editorial UI Badges in SVG */}
        <g filter="url(#brutalShadowSm)">
          {/* Top Left Badge */}
          <rect x="40" y="50" width="165" height="32" fill="#28122F" stroke="#28122F" strokeWidth="2" />
          <rect x="42" y="52" width="161" height="28" fill="#E7962B" />
          <text x="52" y="70" fill="#28122F" fontFamily="var(--font-heading), monospace" fontWeight="800" fontSize="11" letterSpacing="1">
            DIAGNOSTIC // ACTIVE
          </text>

          {/* Top Right Badge */}
          <rect x="400" y="50" width="160" height="32" fill="#28122F" stroke="#28122F" strokeWidth="2" />
          <rect x="402" y="52" width="156" height="28" fill="#63324F" />
          <text x="414" y="70" fill="#FFFFFF" fontFamily="var(--font-heading), monospace" fontWeight="800" fontSize="11" letterSpacing="1">
            AI MENTOR // LIVE
          </text>

          {/* Bottom Left Badge */}
          <rect x="40" y="440" width="150" height="32" fill="#FFFFFF" stroke="#28122F" strokeWidth="2" />
          <text x="52" y="460" fill="#28122F" fontFamily="var(--font-heading), monospace" fontWeight="800" fontSize="11" letterSpacing="1">
            ARENA: 1v1 DUEL
          </text>

          {/* Bottom Right Badge */}
          <rect x="410" y="440" width="150" height="32" fill="#FFFFFF" stroke="#28122F" strokeWidth="2" />
          <text x="422" y="460" fill="#28122F" fontFamily="var(--font-heading), monospace" fontWeight="800" fontSize="11" letterSpacing="1">
            SCORE: VERIFIED
          </text>
        </g>
      </svg>
    </div>
  );
}

export default HeroArtwork;
