import React, { useState, useTransition } from 'react';
import {
  Button, Box, Typography, List, ListItem, ListItemText, Collapse, CircularProgress, Paper, useTheme
} from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import { AnimatedTooltip } from './AnimatedTooltip';

interface Recommendation {
  category: string;
  impact?: string;
  short_description?: { problem: string };
  extended_properties?: Record<string, string>;
  advice?: string;
  subscription_id?: string;
  source?: string;
}

const LLMInteraction_FinopsHubs: React.FC = () => {
  const theme = useTheme();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [isResultsExpanded, setIsResultsExpanded] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);  // New state for errors

  const subscriptionIds = [
    '38c26c07-ccce-4839-b504-cddac8e5b09d',
    'c916841c-459e-4bbd-aff7-c235ae45f0dd',
    '9d923c47-1aa2-4fc9-856f-16ca53e97b76'
  ];

  // Fetch recommendations for review (without sending to LLM)
  const handleFetchRecommendations = async () => {
    startTransition(() => {
      setIsLoading(true);
      setRecommendations([]);
      setError(null);
    });

    try {
      const res = await axios.get<Recommendation[]>(
        `http://localhost:5000/api/review-recommendations?subscription_id=9d923c47-1aa2-4fc9-856f-16ca53e97b76`
      );

      if (res.data.length === 0) {
        setError('No recommendations available.');
      } else {
        setRecommendations(res.data);
      }
    } catch (error: any) {
      console.error('Error fetching recommendations:', error);
      setError('Failed to fetch recommendations. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };
  // Send selected recommendations to LLM for advice generation
  const handleSendToLLM = async () => {
    startTransition(() => {
      setIsLoading(true);
      setError(null);
    });

    try {
      const res = await axios.post<{ advice: Recommendation[] }>(
        'http://localhost:5000/api/analyze-recommendations',
        { recommendations },  // Send the reviewed recommendations
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      setRecommendations(res.data.advice);
    } catch (error: any) {
      console.error('Error querying AI Assistant:', error);
      setError('Failed to query the AI Assistant. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const handleResultsToggle = () => {
    setIsResultsExpanded(!isResultsExpanded);
  };

  const renderFormattedAdvice = (advice: string) => {
    const lines = advice.split('\n').map((line, index) => {
      if (line.includes('**')) {
        const parts = line.split('**');
        return (
          <Typography key={index} variant="body2">
            {parts.map((part, i) =>
              i % 2 === 1 ? <strong key={i}>{part}</strong> : part
            )}
          </Typography>
        );
      }

      if (line.trim().startsWith('- ')) {
        return (
          <Typography key={index} variant="body2" component="li" style={{ marginLeft: '20px' }}>
            {line.trim().slice(2)}
          </Typography>
        );
      }

      return (
        <Typography key={index} variant="body2">
          {line}
        </Typography>
      );
    });

    return <>{lines}</>;
  };

  return (
    <Box p={2} m={2} border={1} borderRadius={2} borderColor={theme.palette.mode === 'light' ? 'grey.300' : 'grey.700'}>
      <Typography variant="h5" gutterBottom>
        AI Assistant Assessment
      </Typography>

      {/* Error display */}
      {error && (
        <Typography variant="body1" color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleFetchRecommendations}
        disabled={isLoading || isPending}
        sx={{ mb: 4 }}
      >
        {isLoading ? <CircularProgress size={24} /> : 'Fetch Recommendations for Review'}
      </Button>

      {recommendations.length > 0 && (
        <> 
          <Box mt={2} display="flex" alignItems="center" justifyContent="space-between" mb={2} onClick={handleResultsToggle} sx={{ cursor: 'pointer' }}>
            <AnimatedTooltip title="Click to expand/collapse the results">
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                <Typography variant="h6">Assessment Results</Typography>
                {isResultsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </Box>
            </AnimatedTooltip>
          </Box>
          <Collapse in={isResultsExpanded} timeout="auto" unmountOnExit>
            <List>
              {recommendations.map((rec, index) => (
                <React.Fragment key={index}>
                  <ListItem button onClick={() => handleToggleExpand(index)} sx={{ bgcolor: expandedIndex === index ? 'grey.100' : 'inherit', mb: 2, borderRadius: 1 }}>
                    <ListItemText
                      primary={
                        <>
                          <Typography variant="body1">
                            <strong>Subscription:</strong> {rec.subscription_id || 'N/A'} - <strong>Recommendation {index + 1}:</strong> {rec.category || 'N/A'} 
                            <strong> Source:</strong> {rec.source || 'N/A'}
                          </Typography>
                        </>
                      }
                      secondary={
                        <>
                          <Typography variant="body2">
                            <strong>Impact:</strong> {rec.impact || 'Unknown'}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Problem:</strong> {rec.short_description?.problem || "No problem description available"}
                          </Typography>
                        </>
                      }
                    />
                    {expandedIndex === index ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </ListItem>
                  <Collapse in={expandedIndex === index} timeout="auto" unmountOnExit>
                    <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
                      <Typography variant="body2">
                        <strong>AI Advice:</strong>
                      </Typography>
                      <Box ml={2}>
                        {renderFormattedAdvice(rec.advice || "No advice available")}
                      </Box>
                      {rec.extended_properties && (
                        <Box sx={{ mt: 2, p: 2, border: '1px solid', borderRadius: 2 }}>
                          <Typography variant="subtitle2" fontWeight="bold">
                            Extended Properties:
                          </Typography>
                          {Object.entries(rec.extended_properties).map(([key, value]) => (
                            <Typography key={key} variant="body2">
                              <strong>{key}:</strong> {value}
                            </Typography>
                          ))}
                        </Box>
                      )}
                    </Paper>
                  </Collapse>
                </React.Fragment>
              ))}
            </List>
          </Collapse>
        </>
      )}
    </Box>
  );
};

export default LLMInteraction_FinopsHubs;