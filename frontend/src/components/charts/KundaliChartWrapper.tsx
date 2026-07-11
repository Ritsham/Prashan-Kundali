import React, { useEffect, useRef } from 'react';
// @ts-ignore
import { KundaliChart } from '../../utils/chart-engine';

interface ChartProps {
  data: any;
  options?: any;
  className?: string;
}

const KundaliChartWrapper: React.FC<ChartProps> = ({ data, options, className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<any>(null);

  useEffect(() => {
    if (canvasRef.current && data) {
      // Clear previous instance if it exists to avoid memory leaks
      if (chartInstance.current && typeof chartInstance.current.destroy === 'function') {
        chartInstance.current.destroy();
      }
      
      chartInstance.current = new KundaliChart(canvasRef.current, data, {
        fontFamily: 'inherit',
        lineColor: window.matchMedia('(prefers-color-scheme: dark)').matches ? '#4b5563' : '#d1d5db',
        lineWidth: 1.5,
        ...options
      });
    }

    return () => {
      // Cleanup observer if possible
      if (chartInstance.current && typeof chartInstance.current.destroy === 'function') {
        chartInstance.current.destroy();
      }
    };
  }, [data, options]);

  return (
    <div className={`w-full aspect-square max-w-[500px] mx-auto ${className}`}>
      <canvas ref={canvasRef} className="w-full h-full" />
    </div>
  );
};

export default KundaliChartWrapper;
