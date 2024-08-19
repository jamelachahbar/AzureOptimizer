import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faMoneyBills } from '@fortawesome/free-solid-svg-icons';

// Import your PNG image
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
        <Card sx={{ minWidth: 275, boxShadow: 3, borderRadius: 3, '&:hover': { boxShadow: 4 } }}>
            <CardContent>
                <Box display="flex" alignItems="center">
                    {/* Add icon using the imported PNG image */}
                    <Box component="img" src={subscriptionsIcon} alt="Subscription Icon" sx={{ width: 32, height: 32}} />
                    <Typography variant="h6" component="div" color="text.secondary" gutterBottom>
                        Subscription: {metric.SubscriptionId}
                    </Typography>
                </Box>
                <Box display="flex" alignItems="center">
                    <FontAwesomeIcon icon={faMoneyBills} size="lg" style={{ marginRight: 8, color: '#1976d2' }} />
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
                <Typography sx={{ mb: 1.5 }} color="text.secondary">
                    Total Cost: <b>${metric.TotalCost}</b>
                </Typography>
            </CardContent>
        </Card>
    );
};

export default SummaryMetricsCard;
