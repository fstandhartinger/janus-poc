'use client';

import { useEffect, useMemo, useRef } from 'react';
import {
  Chart as ChartJS,
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

interface ScoreRadarProps {
  quality: number;
  speed: number;
  cost: number;
  streaming: number;
  multimodal: number;
}

const LABELS = ['Quality', 'Speed', 'Cost', 'Streaming', 'Multimodal'];

export function ScoreRadar({
  quality,
  speed,
  cost,
  streaming,
  multimodal,
}: ScoreRadarProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<ChartJS | null>(null);

  const values = useMemo(
    () => [quality, speed, cost, streaming, multimodal].map((score) => Math.round(score * 100)),
    [quality, speed, cost, streaming, multimodal]
  );

  useEffect(() => {
    if (!canvasRef.current) return;

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    chartRef.current = new ChartJS(canvasRef.current, {
      type: 'radar',
      data: {
        labels: LABELS,
        datasets: [
          {
            label: 'Score',
            data: values,
            backgroundColor: 'rgba(99, 210, 151, 0.2)',
            borderColor: '#63D297',
            pointBackgroundColor: '#63D297',
            pointBorderColor: '#0F1419',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: {
              color: '#6B7280',
              backdropColor: 'transparent',
            },
            grid: {
              color: '#1F2937',
            },
            angleLines: {
              color: '#1F2937',
            },
            pointLabels: {
              color: '#9CA3AF',
              font: {
                size: 12,
              },
            },
          },
        },
      },
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [values]);

  return (
    <div className="h-64 sm:h-72">
      <canvas ref={canvasRef} role="img" aria-label="Score breakdown radar chart" />
    </div>
  );
}
