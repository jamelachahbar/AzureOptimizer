import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Button,
  useTheme,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import RefreshIcon from '@mui/icons-material/Refresh';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import axios from 'axios';
import { API_BASE_URL } from '../utils/apiConfig';

interface AdvisorRecommendation {
  uuid: string;
  problem: string;
  solution: string;
  impact: 'High' | 'Medium' | 'Low';
  impactValue?: string;
  annualSavings?: number;
  monthlySavings?: number;
  subscriptionId: string;
  resourceId?: string;
  category?: string;
}

interface AdvisorRecommendationsCardProps {
  subscriptionId?: string;
}

const getImpactColor = (impact: string): 'error' | 'warning' | 'info' => {
  switch (impact) {
    case 'High':
      return 'error';
    case 'Medium':
      return 'warning';
    case 'Low':
      return 'info';
    default:
      return 'info';
  }
};

const AdvisorRecommendationsCard: React.FC<AdvisorRecommendationsCardProps> = ({
  subscriptionId,
}) => {
  const theme = useTheme();
  const [recommendations, setRecommendations] = useState<AdvisorRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPanel, setExpandedPanel] = useState<string | false>('High');
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [aiInsights, setAiInsights] = useState<{ [key: string]: string }>({});

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = subscriptionId ? { subscription_id: subscriptionId } : {};
      const { data } = await axios.get(`${API_BASE_URL}/api/review-recommendations`, { params });

      // Handle different response formats
      const recs = Array.isArray(data) ? data : data.recommendations || [];
      setRecommendations(recs);
    } catch (err: any) {
      console.error('Error fetching advisor recommendations:', err);
      setError(err.response?.data?.error || 'Failed to fetch recommendations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [subscriptionId]);

  const analyzeRecommendation = async (recommendation: AdvisorRecommendation) => {
    setAnalyzingId(recommendation.uuid);
    try {
      const { data } = await axios.post(`${API_BASE_URL}/api/analyze-recommendations`, {
        recommendation_id: recommendation.uuid,
        problem: recommendation.problem,
        solution: recommendation.solution,
      });
      setAiInsights(prev => ({
        ...prev,
        [recommendation.uuid]: data.analysis || data.insight || 'Analysis completed.',
      }));
    } catch (err: any) {
      console.error('Error analyzing recommendation:', err);
      setAiInsights(prev => ({
        ...prev,
        [recommendation.uuid]: 'Failed to get AI analysis.',
      }));
    } finally {
      setAnalyzingId(null);
    }
  };

  const groupedRecommendations = useMemo(() => {
    const groups: { [key: string]: AdvisorRecommendation[] } = {
      High: [],
      Medium: [],
      Low: [],
    };

    recommendations.forEach((rec) => {
      const impact = rec.impact || 'Low';
      if (groups[impact]) {
        groups[impact].push(rec);
      } else {
        groups.Low.push(rec);
      }
    });

    return groups;
  }, [recommendations]);

  const totalSavings = useMemo(() => {
    return recommendations.reduce((sum, rec) => {
      const annual = rec.annualSavings || 0;
      const monthly = rec.monthlySavings ? rec.monthlySavings * 12 : 0;
      return sum + Math.max(annual, monthly);
    }, 0);
  }, [recommendations]);

  const handlePanelChange = (panel: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedPanel(isExpanded ? panel : false);
  };

  if (loading) {
    return (
      <Card sx={{ width: '100%', boxShadow: 3, borderRadius: 3, height: '100%' }}>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="center" py={4}>
            <CircularProgress size={40} />
            <Typography variant="body1" sx={{ ml: 2 }}>
              Loading Azure Advisor recommendations...
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ width: '100%', boxShadow: 3, borderRadius: 3, height: '100%' }}>
        <CardContent>
          <Typography variant="h6" mb={2}>Azure Advisor Recommendations</Typography>
          <Alert
            severity="error"
            action={
              <IconButton size="small" onClick={fetchRecommendations}>
                <RefreshIcon />
              </IconButton>
            }
          >
            {error}
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        width: '100%',
        boxShadow: 3,
        borderRadius: 3,
        '&:hover': {
          boxShadow: 4,
          transition: 'box-shadow 0.3s',
        },
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <LightbulbIcon sx={{ color: theme.palette.warning.main }} />
            <Typography variant="h6">Azure Advisor Recommendations</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            {totalSavings > 0 && (
              <Chip
                label={`$${totalSavings.toFixed(2)}/yr potential`}
                color="success"
                variant="outlined"
                size="small"
              />
            )}
            <Tooltip title="Refresh recommendations">
              <IconButton onClick={fetchRecommendations} size="small">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {recommendations.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: 200,
              color: 'text.secondary',
            }}
          >
            <Typography variant="body2">
              No cost recommendations available
            </Typography>
          </Box>
        ) : (
          <Box sx={{ maxHeight: 400, overflowY: 'auto' }}>
            {(['High', 'Medium', 'Low'] as const).map((impact) => {
              const recs = groupedRecommendations[impact];
              if (recs.length === 0) return null;

              return (
                <Accordion
                  key={impact}
                  expanded={expandedPanel === impact}
                  onChange={handlePanelChange(impact)}
                  sx={{
                    mb: 1,
                    '&:before': { display: 'none' },
                    borderRadius: 1,
                    overflow: 'hidden',
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    sx={{
                      backgroundColor:
                        impact === 'High'
                          ? 'rgba(244, 67, 54, 0.08)'
                          : impact === 'Medium'
                          ? 'rgba(255, 152, 0, 0.08)'
                          : 'rgba(33, 150, 243, 0.08)',
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip
                        label={impact}
                        color={getImpactColor(impact)}
                        size="small"
                      />
                      <Typography variant="body2">
                        {recs.length} recommendation{recs.length !== 1 ? 's' : ''}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    {recs.map((rec, index) => (
                      <Box
                        key={rec.uuid || index}
                        sx={{
                          p: 2,
                          mb: 1,
                          borderRadius: 1,
                          backgroundColor: theme.palette.background.default,
                          border: `1px solid ${theme.palette.divider}`,
                        }}
                      >
                        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                          {rec.problem}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {rec.solution}
                        </Typography>
                        <Box display="flex" alignItems="center" justifyContent="space-between" mt={1}>
                          <Box display="flex" gap={1}>
                            {rec.annualSavings && rec.annualSavings > 0 && (
                              <Chip
                                label={`$${rec.annualSavings.toFixed(2)}/yr`}
                                color="success"
                                size="small"
                                variant="outlined"
                              />
                            )}
                            {rec.category && (
                              <Chip
                                label={rec.category}
                                size="small"
                                variant="outlined"
                              />
                            )}
                          </Box>
                          <Tooltip title="Get AI analysis">
                            <Button
                              size="small"
                              startIcon={
                                analyzingId === rec.uuid ? (
                                  <CircularProgress size={14} />
                                ) : (
                                  <AutoAwesomeIcon />
                                )
                              }
                              onClick={() => analyzeRecommendation(rec)}
                              disabled={analyzingId === rec.uuid}
                            >
                              Analyze
                            </Button>
                          </Tooltip>
                        </Box>
                        {aiInsights[rec.uuid] && (
                          <Box
                            sx={{
                              mt: 2,
                              p: 1.5,
                              borderRadius: 1,
                              backgroundColor: 'rgba(156, 39, 176, 0.08)',
                              border: '1px solid rgba(156, 39, 176, 0.3)',
                            }}
                          >
                            <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                              AI Analysis
                            </Typography>
                            <Typography variant="body2">
                              {aiInsights[rec.uuid]}
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    ))}
                  </AccordionDetails>
                </Accordion>
              );
            })}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default AdvisorRecommendationsCard;
