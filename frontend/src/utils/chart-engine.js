export class KundaliChart {
  constructor(canvas, data, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.data = data || {};
    this.options = {
      fontFamily: options.fontFamily || '"Roboto", sans-serif',
      lineColor: options.lineColor || '#f9c5af',
      lineWidth: options.lineWidth || 1.5,
      ...options
    };

    this.signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
    this.signNumbers = { Aries: 1, Taurus: 2, Gemini: 3, Cancer: 4, Leo: 5, Virgo: 6, Libra: 7, Scorpio: 8, Sagittarius: 9, Capricorn: 10, Aquarius: 11, Pisces: 12 };
    
    // Based on the image
    this.planetColors = {
      Sun: '#e63946', // Red
      Moon: '#a8dadc', // Light Blue
      Mars: '#2a9d8f', // Green
      Mercury: '#457b9d', // Blue
      Jupiter: '#9d4edd', // Purple
      Venus: '#2a9d8f', // Green
      Saturn: '#e76f51', // Orange/Red
      Rahu: '#c1121f', // Dark Red
      Ketu: '#b0891d', // Golden
      Uranus: '#e63946', // Red
      Neptune: '#1d3557', // Dark Blue
      Pluto: '#000000', // Black
      Asc: '#000000'
    };

    this.planetShort = { Asc: "Asc", Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju", Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke", Uranus: "Ur", Neptune: "Ne", Pluto: "Pl" };

    this.resizeObserver = new ResizeObserver(() => {
      this.resizeAndDraw();
    });
    this.resizeObserver.observe(this.canvas.parentElement || this.canvas);

    this.resizeAndDraw();
  }

  resizeAndDraw() {
    // Handle high DPI displays
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return; // Skip if hidden
    
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    
    this.ctx.scale(dpr, dpr);
    this.draw(rect.width, rect.height);
  }

  draw(width, height) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = this.options.lineColor;
    ctx.lineWidth = this.options.lineWidth;
    
    // Draw outer box
    ctx.strokeRect(0, 0, width, height);
    
    // Draw diagonals
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(width, height);
    ctx.moveTo(width, 0);
    ctx.lineTo(0, height);
    ctx.stroke();

    // Draw inner diamond
    ctx.beginPath();
    ctx.moveTo(width / 2, 0);
    ctx.lineTo(width, height / 2);
    ctx.lineTo(width / 2, height);
    ctx.lineTo(0, height / 2);
    ctx.closePath();
    ctx.stroke();

    this.drawContent(width, height);
  }

  drawContent(w, h) {
    const ascSign = this.signs.find((sign) => (this.data[sign] || []).includes("Asc")) || "Aries";
    const ascIndex = this.signs.indexOf(ascSign);

    // Geometric centroids — provably correct for the grid:
    //   outer square + both main diagonals + inner diamond.
    // Index 0 = H1 (Lagna, top-diamond), clockwise.
    const houseCenters = [
      { x: 0.50, y: 0.25 }, // H1  – top diamond
      { x: 0.25, y: 0.12 }, // H2  – top-left corner triangle
      { x: 0.12, y: 0.25 }, // H3  – left-upper side triangle
      { x: 0.25, y: 0.50 }, // H4  – left diamond
      { x: 0.12, y: 0.75 }, // H5  – left-lower side triangle
      { x: 0.25, y: 0.88 }, // H6  – bottom-left corner triangle
      { x: 0.50, y: 0.75 }, // H7  – bottom diamond
      { x: 0.75, y: 0.88 }, // H8  – bottom-right corner triangle
      { x: 0.88, y: 0.75 }, // H9  – right-lower side triangle
      { x: 0.75, y: 0.50 }, // H10 – right diamond
      { x: 0.88, y: 0.25 }, // H11 – right-upper side triangle
      { x: 0.75, y: 0.12 }, // H12 – top-right corner triangle
    ];

    // Safe vertical zone [yMin, yMax] for each house (fraction of h).
    // Content must be FULLY within this range to avoid crossing diagonal lines.
    // Inner-vertex Y limits are at 0.25/0.75 for corners, 0.5 for diamonds/sides.
    const safeZone = [
      [0.02, 0.47], // H1  top diamond (inner vertex at y=0.50)
      [0.01, 0.23], // H2  top-left corner (inner vertex at y=0.25)
      [0.02, 0.47], // H3  left-upper side
      [0.08, 0.92], // H4  left diamond
      [0.53, 0.97], // H5  left-lower side
      [0.77, 0.98], // H6  bottom-left corner (inner vertex at y=0.75)
      [0.53, 0.97], // H7  bottom diamond
      [0.77, 0.98], // H8  bottom-right corner (inner vertex at y=0.75)
      [0.53, 0.97], // H9  right-lower side
      [0.08, 0.92], // H10 right diamond
      [0.02, 0.47], // H11 right-upper side
      [0.01, 0.23], // H12 top-right corner (inner vertex at y=0.25)
    ];

    // Max safe width (fraction of w) — prevents text from crossing vertical diagonals.
    // Corner triangles are narrow; diamonds are wide.
    const safeWidth = [0.45, 0.22, 0.20, 0.42, 0.20, 0.22, 0.45, 0.22, 0.20, 0.42, 0.20, 0.22];

    const BASE_NUM  = Math.max(10, w * 0.034);
    const BASE_PLNT = Math.max( 9, w * 0.031);

    this.ctx.textAlign    = 'center';
    this.ctx.textBaseline = 'middle';

    for (let i = 0; i < 12; i++) {
      const sign    = this.signs[(ascIndex + i) % 12];
      const signNum = this.signNumbers[sign];
      const bodies  = (this.data[sign] || []).filter(b => b !== "Asc");
      const numRows = Math.ceil(bodies.length / 2);

      const cx       = houseCenters[i].x * w;
      const [yMin, yMax] = safeZone[i];
      const zoneH    = (yMax - yMin) * h;    // pixels of vertical space

      // ── Adaptive font sizing ─────────────────────────────────────────────────
      // Start with base sizes, then shrink until total content fits the safe zone.
      let numSize = BASE_NUM;
      let pSize   = BASE_PLNT;
      let lineH   = pSize * 1.4;

      for (let attempt = 0; attempt < 5; attempt++) {
        const totalH = numSize * 1.1 + numRows * lineH;
        if (totalH <= zoneH * 0.90) break;  // fits with 10 % margin → done
        numSize *= 0.82;
        pSize   *= 0.82;
        lineH    = pSize * 1.4;
      }

      // ── Vertical centering within safe zone ─────────────────────────────────
      const totalH  = numSize * 1.1 + numRows * lineH;
      const blockTop = (yMin + yMax) / 2 * h - totalH / 2; // top of content block
      const numY     = blockTop + numSize * 0.55;           // baseline of sign number

      // ── 1. Rashi number ──────────────────────────────────────────────────────
      this.ctx.font      = `bold ${numSize}px ${this.options.fontFamily}`;
      this.ctx.fillStyle = '#241f1a';
      this.ctx.fillText(signNum, cx, numY);

      // ── 2. Planet abbreviations (max 2 per row, individually coloured) ───────
      if (bodies.length > 0) {
        const pColOffset = Math.min(pSize * 0.9, safeWidth[i] * w * 0.4);
        let rowY = numY + numSize * 0.6 + lineH * 0.5;

        this.ctx.font = `bold ${pSize}px ${this.options.fontFamily}`;

        for (let j = 0; j < bodies.length; j += 2) {
          const p1 = bodies[j];
          const p2 = bodies[j + 1];

          if (p2) {
            this.ctx.fillStyle = this.planetColors[p1] || '#555';
            this.ctx.fillText(this.planetShort[p1] || p1, cx - pColOffset, rowY);
            this.ctx.fillStyle = this.planetColors[p2] || '#555';
            this.ctx.fillText(this.planetShort[p2] || p2, cx + pColOffset, rowY);
          } else {
            this.ctx.fillStyle = this.planetColors[p1] || '#555';
            this.ctx.fillText(this.planetShort[p1] || p1, cx, rowY);
          }
          rowY += lineH;
        }
      }
    }
  }

  drawPlanets(planets, cx, cy, w) {
    if (!planets || planets.length === 0) return;

    const fontSize = Math.max(12, w * 0.04);
    this.ctx.font = `bold ${fontSize}px ${this.options.fontFamily}`;
    
    // Rough calculation of spacing
    const lineHeight = fontSize * 1.2;
    const cols = planets.length > 2 ? 2 : 1;
    const rows = Math.ceil(planets.length / cols);
    
    const startY = cy - ((rows - 1) * lineHeight) / 2;

    planets.forEach((planet, index) => {
      const col = index % cols;
      const row = Math.floor(index / cols);
      
      const xOffset = cols > 1 ? (col === 0 ? -w*0.04 : w*0.04) : 0;
      const x = cx + xOffset;
      const y = startY + row * lineHeight;

      const shortName = this.planetShort[planet] || planet;
      this.ctx.fillStyle = this.planetColors[planet] || '#333';
      this.ctx.fillText(shortName, x, y);
    });
  }
}
