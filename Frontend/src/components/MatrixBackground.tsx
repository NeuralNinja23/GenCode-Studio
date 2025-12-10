import React, { useEffect, useRef } from 'react';

interface MatrixBackgroundProps {
  /** Hex color for the Matrix characters */
  color?: string;
  /** Opacity of the entire canvas (0-1) */
  opacity?: number;
}

/**
 * MatrixBackground Component
 * 
 * Renders a subtle Matrix-style falling code animation using HTML5 Canvas.
 * Optimized for performance and minimal visual distraction.
 */
const MatrixBackground: React.FC<MatrixBackgroundProps> = ({
  color = '#A855F7', // Purple to match GenCode theme
  opacity = 1
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    // Configuration
    const CONFIG = {
      characters: '01<>{}[]/\\|',
      fontSize: 14,
      columnSpacing: 4,    // Multiplier for fontSize
      fadeOpacity: 0.1,    // Trail fade amount
      charOpacity: 0.35,   // Character opacity
      dropSpeed: 0.3,      // Drop speed multiplier
      resetChance: 0.975,  // Chance to reset drop (higher = slower reset)
      animationInterval: 80 // ms between frames
    };

    // Set canvas to parent dimensions
    const setCanvasDimensions = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    setCanvasDimensions();
    window.addEventListener('resize', setCanvasDimensions);

    // Calculate columns based on canvas width
    const columnWidth = CONFIG.fontSize * CONFIG.columnSpacing;
    const columns = Math.floor(canvas.width / columnWidth);

    // Initialize drop positions (y-coordinate for each column)
    const drops: number[] = Array.from(
      { length: columns },
      () => Math.random() * -50 // Start above viewport
    );

    // Parse hex color to RGB
    const hexToRgb = (hex: string): { r: number; g: number; b: number } => {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return { r, g, b };
    };

    const rgb = hexToRgb(color);

    // Animation loop
    const draw = () => {
      // Fade effect for trailing characters
      context.fillStyle = `rgba(0, 0, 0, ${CONFIG.fadeOpacity})`;
      context.fillRect(0, 0, canvas.width, canvas.height);

      // Set font for characters
      context.font = `${CONFIG.fontSize}px 'JetBrains Mono', 'Fira Code', monospace`;

      // Draw each column
      drops.forEach((drop, columnIndex) => {
        // Select random character
        const char = CONFIG.characters[
          Math.floor(Math.random() * CONFIG.characters.length)
        ];

        // Calculate position
        const x = columnIndex * columnWidth;
        const y = drop * CONFIG.fontSize;

        // Set character color with opacity
        context.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${CONFIG.charOpacity})`;

        // Draw character
        context.fillText(char, x, y);

        // Reset drop if it's gone off screen
        if (y > canvas.height && Math.random() > CONFIG.resetChance) {
          drops[columnIndex] = 0;
        }

        // Move drop down
        drops[columnIndex] += CONFIG.dropSpeed;
      });
    };

    // Start animation
    const interval = setInterval(draw, CONFIG.animationInterval);

    // Cleanup
    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', setCanvasDimensions);
    };
  }, [color, opacity]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed top-0 left-0 w-full h-full z-0 pointer-events-none"
      style={{ opacity }}
      aria-hidden="true"
      role="presentation"
    />
  );
};

export default MatrixBackground;
