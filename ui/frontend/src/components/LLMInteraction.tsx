import React, { useState, useTransition } from 'react';
import {
  Button, Box, Typography, List, ListItem, ListItemText, Collapse, CircularProgress, Paper, useTheme
} from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';

interface ShortDescription {
  problem: string;
}

interface Recommendation {
  category: string;
  impact: string;
  short_description: ShortDescription;
  extended_properties?: Record<string, string>;
  advice: string;
  subscription_id: string;  // Add subscription_id to the interface to track which subscription this belongs to
}

const LLMInteraction: React.FC = () => {
  const theme = useTheme(); // Access the current theme
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [isResultsExpanded, setIsResultsExpanded] = useState<boolean>(true); // State to manage the collapse of the results section

  const subscriptionIds = [
    '38c26c07-ccce-4839-b504-cddac8e5b09d',
    'c916841c-459e-4bbd-aff7-c235ae45f0dd',
    '9d923c47-1aa2-4fc9-856f-16ca53e97b76'
  ]; // List of subscription IDs

  const handleFetchAndAnalyze = async () => {
    startTransition(() => {
      setIsLoading(true);
      setRecommendations([]);
    });
  
    try {
      const allRecommendations: Recommendation[] = [];
  
      for (const subscription_id of subscriptionIds) {
        console.log(`Sending request for subscription ID: ${subscription_id}`);
        const res = await axios.post<{ advice: Recommendation[] }>(
          'http://localhost:5000/api/analyze-recommendations',
          { subscription_id },  // Pass each subscription ID individually
          {
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );
  
        console.log(`Response Data for ${subscription_id}:`, res.data.advice);
        if (res.data.advice) {
          // Add the subscription ID to each recommendation
          const updatedRecommendations = res.data.advice.map((rec) => ({
            ...rec,
            subscription_id,
          }));
          allRecommendations.push(...updatedRecommendations);
        }
      }
  
      setRecommendations(allRecommendations);
    } catch (error) {
      console.error('Error querying AI Assistant:', error);
      setRecommendations([]);
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

      if (line.trim().match(/^\d+\./)) {
        return (
          <Typography key={index} variant="body2" component="li" style={{ marginLeft: '20px' }}>
            {line.trim()}
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
    <Box
      p={2}
      m={2}
      border={1}
      borderRadius={2}
      borderColor={theme.palette.mode === 'light' ? 'grey.300' : 'grey.700'}
      bgcolor={theme.palette.background.paper}
    >
      <Typography variant="h5" gutterBottom>
        AI Assistant Assessment
      </Typography>
      <Button
        variant="contained"
        color="primary"
        onClick={handleFetchAndAnalyze}
        disabled={isLoading || isPending}
        sx={{ mb: 4 }}
      >
        {isLoading ? <CircularProgress size={24} /> : 'Fetch and Analyze Recommendations'}
      </Button>

      {recommendations.length > 0 && (
        <>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2} onClick={handleResultsToggle} sx={{ cursor: 'pointer' }}>
            <Typography variant="h6">
              Assessment Results
            </Typography>
            {isResultsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </Box>
          <Collapse in={isResultsExpanded} timeout="auto" unmountOnExit>
            <List>
              {recommendations.map((rec, index) => (
                <React.Fragment key={index}>
                  <ListItem
                    button
                    onClick={() => handleToggleExpand(index)}
                    sx={{
                      bgcolor: expandedIndex === index 
                        ? (theme.palette.mode === 'light' ? 'grey.100' : 'grey.800') 
                        : 'inherit',
                      mb: 2, // Add margin bottom for spacing
                      borderRadius: 1, // Add border radius to make it visually distinct
                    }}
                  >
                    <ListItemText
                      primary={
                        <>
                          <Typography variant="body1" color={theme.palette.text.primary}>
                            <strong>Subscription:</strong> {rec.subscription_id} - <strong>Recommendation {index + 1}:</strong> {rec.category}
                          </Typography>
                        </>
                      }
                      secondary={
                        <>
                          <Typography variant="body2" color={theme.palette.text.secondary}>
                            <strong>Impact:</strong> {rec.impact}
                          </Typography>
                          <Typography variant="body2" color={theme.palette.text.secondary}>
                            <strong>Problem:</strong> {rec.short_description.problem || "No problem description available"}
                          </Typography>
                        </>
                      }
                      primaryTypographyProps={{ color: theme.palette.text.primary }}
                      secondaryTypographyProps={{ color: theme.palette.text.secondary }}
                    />

                    {expandedIndex === index ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </ListItem>
                  <Collapse in={expandedIndex === index} timeout="auto" unmountOnExit>
                    <Paper
                      elevation={2}
                      sx={{
                        p: 2,
                        mb: 3,
                        bgcolor: theme.palette.mode === 'light' ? 'grey.100' : 'grey.800',
                        color: theme.palette.text.primary,
                      }}
                    >
                      <Typography variant="body2" sx={{ mt: 2 }}>
                        <strong>AI Advice:</strong>
                      </Typography>
                      <Box ml={2}>
                        {renderFormattedAdvice(rec.advice || "No advice available")}
                      </Box>
                      {rec.extended_properties && (
                        <Box
                          sx={{
                            mt: 2,
                            p: 2,
                            border: '1px solid',
                            borderColor: theme.palette.mode === 'light' ? 'grey.400' : 'grey.600',
                            borderRadius: 2,
                            bgcolor: theme.palette.mode === 'light' ? 'grey.50' : 'grey.900',
                          }}
                        >
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

export default LLMInteraction;