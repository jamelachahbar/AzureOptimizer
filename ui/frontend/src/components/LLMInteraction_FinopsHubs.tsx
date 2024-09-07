import React, { useState, useTransition } from 'react';
import {
  Button, Box, Typography, List, ListItem, ListItemText, Collapse, CircularProgress, Paper, useTheme, MenuItem, Select, InputLabel, FormControl
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
  SubscriptionGuid?: string; 
  Instance?: string;
  generated_date?: string;
  fit_score?: string;
}

const LLMInteraction_FinopsHubs: React.FC = () => {
  const theme = useTheme();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [isResultsExpanded, setIsResultsExpanded] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string>('All');  // New state for source filter

  // Get the subscription ID based on the recommendation source
  const getSubscriptionId = (rec: Recommendation) => {
    if (rec.source === 'Azure API') {
      return rec.extended_properties?.subid || rec.subscription_id || 'N/A';
    }
    return rec.subscription_id || 'N/A';
  };

  // Fetch recommendations for review (without sending to LLM)
  const handleFetchRecommendations = async () => {
    startTransition(() => {
      setIsLoading(true);
      setRecommendations([]);
      setError(null);
    });

    try {
      const res = await axios.get<Recommendation[]>(
        `http://localhost:5000/api/review-recommendations`
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

  const handleFilterChange = (event: any) => {
    setSourceFilter(event.target.value);
  };

  // Filter recommendations based on the selected source
  const filteredRecommendations = recommendations.filter((rec) => {
    return sourceFilter === 'All' || rec.source === sourceFilter;
  });

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

  const renderSqlDbProperties = (rec: Recommendation) => {
    return (
      <Box sx={{ mt: 2, p: 2, border: '1px solid', borderRadius: 2 }}>
        <Typography variant="subtitle2" fontWeight="bold">
          Additional SQL DB Information:
        </Typography>
        <Typography variant="body2">
          <strong>Instance Name:</strong> {rec.Instance || 'N/A'}
        </Typography>
        <Typography variant="body2">
          <strong>Generated Date:</strong> {rec.generated_date || 'N/A'}
        </Typography>
        <Typography variant="body2">
          <strong>Fit Score:</strong> {rec.fit_score || 'N/A'}
        </Typography>
        <Typography variant="body2">
          <strong>Subscription ID:</strong> {rec.subscription_id || 'N/A'}
        </Typography>
      </Box>
    );
  };

  const renderExtendedProperties = (rec: Recommendation) => {
    if (rec.source === 'SQL DB') {
      return renderSqlDbProperties(rec);
    } else if (rec.extended_properties) {
      return (
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
      );
    }
    return null;
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
          <Button
            variant="contained"
            color="secondary"
            onClick={handleSendToLLM}
            disabled={isLoading || isPending}
            sx={{ mb: 4, ml: 2 }}
          >
            {isLoading ? <CircularProgress size={24} /> : 'Send to LLM for Analysis'}
          </Button>

          <FormControl sx={{ mb: 4, ml: 2, minWidth: 200 }}>
            <InputLabel>Filter by Source</InputLabel>
            <Select
              value={sourceFilter}
              label="Filter by Source"
              onChange={handleFilterChange}
            >
              <MenuItem value="All">All</MenuItem>
              <MenuItem value="SQL DB">SQL DB</MenuItem>
              <MenuItem value="Azure API">Azure API</MenuItem>
            </Select>
          </FormControl>

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
              {filteredRecommendations.map((rec, index) => (
                <React.Fragment key={index}>
                  <ListItem button onClick={() => handleToggleExpand(index)} sx={{ bgcolor: expandedIndex === index ? 'grey.100' : 'inherit', mb: 2, borderRadius: 1 }}>
                    <ListItemText
                      primary={
                        <>
                          <Typography variant="body1">
                            <strong>Subscription:</strong> {getSubscriptionId(rec)} - <strong>Recommendation {index + 1}:</strong> {rec.category || 'N/A'}
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
                      {renderExtendedProperties(rec)} {/* Render SQL DB or Azure API properties */}
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
