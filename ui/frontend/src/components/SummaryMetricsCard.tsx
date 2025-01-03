import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faMoneyBills } from '@fortawesome/free-solid-svg-icons';
import subscriptionsIcon from '../components/subscriptions.png';

interface SummaryMetric {
    SubscriptionId: string;
    AverageDailyCost: number;
    MaximumDailyCost: number;
    MinimumDailyCost: number;
    TotalCost: number;
}

interface SummaryMetricsCardProps {
    metric: SummaryMetric;
}

const SummaryMetricsCard: React.FC<SummaryMetricsCardProps> = ({ metric }) => {
    return (
        <Card
            sx={{
                width: '100%', // Full width for grid cell
                maxWidth: 280,
                maxHeight: 180,
                boxShadow: 3,
                borderRadius: 3,
                '&:hover': {
                    boxShadow: 4,
                    transition: 'box-shadow 0.3s',
                },
            }}
        >
            <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                    <Box
                        component="img"
                        src={subscriptionsIcon}
                        alt="Subscription Icon"
                        sx={{ width: 24, height: 24, marginRight: 1 }}
                    />
                    <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                        sx={{
                            fontSize: '0.8rem',
                            lineHeight: 1.2,
                            overflow: 'visible', // Allow full text visibility
                            wordBreak: 'break-word', // Break long words
                        }}
                    >
                        Subscription: <b>{metric.SubscriptionId}</b>
                    </Typography>
                </Box>
                <Box display="flex" alignItems="center" mb={1}>
                    <FontAwesomeIcon
                        icon={faMoneyBills}
                        style={{ marginRight: 8, color: '#1976d2' }}
                    />
                    <Typography variant="h6" component="div" sx={{ fontSize: '1rem' }}>
                        <b>${metric.AverageDailyCost.toFixed(2)}</b>
                    </Typography>
                </Box>
                <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ fontSize: '0.8rem', lineHeight: 1.2 }}
                >
                    Max Daily: ${metric.MaximumDailyCost.toFixed(2)}
                </Typography>
                <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ fontSize: '0.8rem', lineHeight: 1.2 }}
                >
                    Min Daily: ${metric.MinimumDailyCost.toFixed(2)}
                </Typography>
                <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ fontSize: '0.8rem', lineHeight: 1.2 }}
                >
                    Total Cost: <b>${metric.TotalCost.toFixed(2)}</b>
                </Typography>
            </CardContent>
        </Card>
    );
};

export default SummaryMetricsCard;
