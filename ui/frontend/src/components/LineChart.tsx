// src/components/LineChart.tsx
import React from 'react';
import { Line } from 'react-chartjs-2';
import { ChartData, ChartOptions } from 'chart.js';

interface LineChartProps {
  data: ChartData<'line'>;
}

const LineChart: React.FC<LineChartProps> = ({ data }) => {
  const options: ChartOptions<'line'> = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Cost Trend Over Time',
      },
    },
  };

  return <Line data={data} options={options} />;
};

export default LineChart;
