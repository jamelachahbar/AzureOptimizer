import React, { useMemo } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  CircularProgress,
  useTheme,
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';

interface Policy {
  name: string;
  description: string;
  enabled: boolean;
}

interface ResourceData {
  Resource: string;
  Action: string;
  Status: string;
  Cost: number;
  Policy: string;
  SubscriptionId: string;
}

interface OptimizationScoreCardProps {
  policies: Policy[];
  impactedResources: ResourceData[];
  anomalyCount: number;
  estimatedSavings: number;
}

const OptimizationScoreCard: React.FC<OptimizationScoreCardProps> = ({
  policies,
  impactedResources,
  anomalyCount,
  estimatedSavings,
}) => {
  const theme = useTheme();

  const { score, issues } = useMemo(() => {
    let calculatedScore = 100;
    const issuesList: { label: string; severity: 'error' | 'warning' | 'success' }[] = [];

    // Deduct points for disabled policies (5 points per disabled policy, max 25)
    const disabledPolicies = policies.filter(p => !p.enabled).length;
    const policyPenalty = Math.min(disabledPolicies * 5, 25);
    calculatedScore -= policyPenalty;
    if (disabledPolicies > 0) {
      issuesList.push({ label: `${disabledPolicies} disabled policies`, severity: 'warning' });
    }

    // Deduct points for waste resources (2 points per resource, max 30)
    const wasteResourceCount = impactedResources.length;
    const wastePenalty = Math.min(wasteResourceCount * 2, 30);
    calculatedScore -= wastePenalty;
    if (wasteResourceCount > 0) {
      issuesList.push({ label: `${wasteResourceCount} waste resources`, severity: 'error' });
    }

    // Deduct points for anomalies (10 points per anomaly, max 20)
    const anomalyPenalty = Math.min(anomalyCount * 10, 20);
    calculatedScore -= anomalyPenalty;
    if (anomalyCount > 0) {
      issuesList.push({ label: `${anomalyCount} anomalies detected`, severity: 'error' });
    }

    // Bonus for no issues
    if (issuesList.length === 0) {
      issuesList.push({ label: 'All optimized', severity: 'success' });
    }

    return { score: Math.max(0, calculatedScore), issues: issuesList };
  }, [policies, impactedResources, anomalyCount]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    return '#f44336';
  };

  const scoreColor = getScoreColor(score);

  return (
    <Card
      sx={{
        width: '100%',
        height: '100%',
        boxShadow: 3,
        borderRadius: 3,
        display: 'flex',
        flexDirection: 'column',
        '&:hover': {
          boxShadow: 4,
          transition: 'box-shadow 0.3s',
        },
      }}
    >
      <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="h6">Optimization Score</Typography>
          {score >= 80 ? (
            <CheckCircleIcon sx={{ color: scoreColor }} />
          ) : (
            <WarningAmberIcon sx={{ color: scoreColor }} />
          )}
        </Box>

        <Box display="flex" alignItems="center" justifyContent="center" mb={3}>
          <Box position="relative" display="inline-flex">
            <CircularProgress
              variant="determinate"
              value={100}
              size={140}
              thickness={4}
              sx={{ color: theme.palette.grey[300] }}
            />
            <CircularProgress
              variant="determinate"
              value={score}
              size={140}
              thickness={4}
              sx={{
                color: scoreColor,
                position: 'absolute',
                left: 0,
              }}
            />
            <Box
              sx={{
                top: 0,
                left: 0,
                bottom: 0,
                right: 0,
                position: 'absolute',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography
                variant="h3"
                component="div"
                sx={{ color: scoreColor, fontWeight: 'bold' }}
              >
                {score}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                out of 100
              </Typography>
            </Box>
          </Box>
        </Box>

        {estimatedSavings > 0 && (
          <Box
            sx={{
              backgroundColor: '#e8f5e9',
              borderRadius: 2,
              p: 1.5,
              mb: 2,
              textAlign: 'center',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              Potential Monthly Savings
            </Typography>
            <Typography variant="h5" sx={{ color: '#2e7d32', fontWeight: 'bold' }}>
              ${estimatedSavings.toFixed(2)}
            </Typography>
          </Box>
        )}

        <Box display="flex" flexWrap="wrap" gap={1} justifyContent="center">
          {issues.map((issue, index) => (
            <Chip
              key={index}
              label={issue.label}
              size="small"
              color={issue.severity}
              variant="outlined"
              icon={
                issue.severity === 'success' ? (
                  <CheckCircleIcon />
                ) : (
                  <WarningAmberIcon />
                )
              }
            />
          ))}
        </Box>
      </CardContent>
    </Card>
  );
};

export default OptimizationScoreCard;
