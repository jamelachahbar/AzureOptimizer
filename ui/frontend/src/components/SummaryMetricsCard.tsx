import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faMoneyBillWave } from '@fortawesome/free-solid-svg-icons';

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
        <Card sx={{ minWidth: 275, boxShadow: 3, '&:hover': { boxShadow: 6 } }}>
            <CardContent>
                <Typography sx={{ fontSize: 14 }} color="text.secondary" gutterBottom>
                    Subscription: {metric.SubscriptionId}
                </Typography>
                <Box display="flex" alignItems="center">
                    <FontAwesomeIcon icon={faMoneyBillWave} size="lg" style={{ marginRight: 8, color: '#1976d2' }} />
                    <Typography variant="h5" component="div">
                        ${metric.AverageDailyCost}
                    </Typography>
                </Box>
                <Typography sx={{ mb: 1.5 }} color="text.secondary">
                    Max Daily: ${metric.MaximumDailyCost}
                </Typography>
                <Typography sx={{ mb: 1.5 }} color="text.secondary">
                    Min Daily: ${metric.MinimumDailyCost}
                </Typography>
                <Typography variant="body2">
                    Total Cost: <b>${metric.TotalCost}</b>
                </Typography>
            </CardContent>
        </Card>
    );
};

export default SummaryMetricsCard;
