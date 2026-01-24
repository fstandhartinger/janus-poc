'use client';

import { useEffect, useMemo, useRef } from 'react';
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
  Title,
} from 'chart.js';
import type { ChartOptions } from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

type ChartKind = 'bar' | 'line' | 'pie' | 'doughnut';

interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string | string[];
}

interface ChartData {
  type: ChartKind;
  data: {
    labels: string[];
    datasets: ChartDataset[];
  };
  options?: Record<string, unknown>;
  description?: string;
}

interface ChartBlockProps {
  config: ChartData;
}

const CHART_COLORS = [
  '#63D297',
  '#FA5D19',
  '#3B82F6',
  '#8B5CF6',
  '#F59E0B',
  '#EC4899',
];

function buildChartLabel(config: ChartData) {
  if (config.description) {
    return config.description;
  }

  const datasetLabels = config.data.datasets
    .map((dataset) => dataset.label)
    .filter((label) => Boolean(label));

  if (datasetLabels.length === 0) {
    return `${config.type} chart`;
  }

  return `${config.type} chart showing ${datasetLabels.join(', ')}`;
}

export function ChartBlock({ config }: ChartBlockProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<ChartJS | null>(null);
  const ariaLabel = useMemo(() => buildChartLabel(config), [config]);

  useEffect(() => {
    if (!canvasRef.current) return;

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    const datasets = config.data.datasets.map((dataset, index) => ({
      ...dataset,
      backgroundColor:
        dataset.backgroundColor ?? CHART_COLORS[index % CHART_COLORS.length],
      borderColor:
        dataset.borderColor ?? CHART_COLORS[index % CHART_COLORS.length],
    }));

    const baseOptions: ChartOptions = {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          labels: {
            color: '#9CA3AF',
          },
        },
      },
      scales:
        config.type !== 'pie' && config.type !== 'doughnut'
          ? {
              x: {
                ticks: { color: '#9CA3AF' },
                grid: { color: '#1F2937' },
              },
              y: {
                ticks: { color: '#9CA3AF' },
                grid: { color: '#1F2937' },
              },
            }
          : undefined,
    };

    chartRef.current = new ChartJS(canvasRef.current, {
      type: config.type,
      data: {
        ...config.data,
        datasets,
      },
      options: {
        ...baseOptions,
        ...(config.options ?? {}),
      } as ChartOptions,
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [config]);

  return (
    <div className="chart-block">
      <canvas ref={canvasRef} role="img" aria-label={ariaLabel} />
    </div>
  );
}
