import React, { useCallback } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import { Typography } from '@mui/material';

interface CostData {
    date: string;
    cost: number;
    SubscriptionId: string;
}

interface DataBySubscription {
    [SubscriptionId: string]: CostData[];
}

interface ProcessedData {
    [date: string]: {
        date: string;
        costs: SubscriptionCosts;
    };
}

interface SubscriptionCosts {
    [subscriptionId: string]: number;
}

interface CostTrendChartProps {
    trendData: CostData[];
    selectedSubscription: string;
}

const CostTrendChart: React.FC<CostTrendChartProps> = ({ trendData, selectedSubscription }) => {
    const filteredTrendData = selectedSubscription === 'All Subscriptions'
      ? trendData
      : trendData.filter((data) => data.SubscriptionId === selectedSubscription);
    const generateRandomColor = useCallback(() => {
        return '#' + Math.floor(Math.random() * 16777215).toString(16);
    }, []);

    const renderChartData = () => {
        const dataBySubscription: DataBySubscription = {};

        if (!trendData || trendData.length === 0) {
            return <Typography>No data available</Typography>;
        }

        if (selectedSubscription === 'All Subscriptions') {
            trendData.forEach((data) => {
                if (!dataBySubscription[data.SubscriptionId]) {
                    dataBySubscription[data.SubscriptionId] = [];
                }
                dataBySubscription[data.SubscriptionId].push(data);
            });
        } else {
            dataBySubscription[selectedSubscription] = trendData.filter(
                (data) => data.SubscriptionId === selectedSubscription
            );

            if (!dataBySubscription[selectedSubscription]) {
                dataBySubscription[selectedSubscription] = [];
            }
        }

        const processedData = trendData.reduce<ProcessedData>((acc, curr) => {
            const { SubscriptionId, cost, date } = curr;

            if (!acc[date]) {
                acc[date] = { date, costs: {} };
            }

            if (!acc[date].costs[SubscriptionId]) {
                acc[date].costs[SubscriptionId] = 0;
            }

            acc[date].costs[SubscriptionId] += cost;

            return acc;
        }, {});

        const chartData = Object.values(processedData).map(entry => ({
            date: entry.date,
            ...entry.costs
        }));

        if (chartData.length === 0) {
            return <Typography>No chart data available</Typography>;
        }

        return (
            <ResponsiveContainer width="100%" maxHeight={400}>
                <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    {Object.keys(dataBySubscription).map((subscriptionId, index) => (
                        <Line
                            key={subscriptionId}
                            type="natural"
                            dataKey={subscriptionId}
                            stroke={generateRandomColor()}
                            activeDot={{ r: 8 }}
                            animationEasing='ease-in-out'
                        />
                    ))}


                </LineChart>
            </ResponsiveContainer>
        );
    };

    return <>{renderChartData()}</>;
};

export default CostTrendChart;
