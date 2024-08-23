import React, { useState, useTransition } from 'react';
import {
  Button, Box, Typography, List, ListItem, ListItemText, Collapse, CircularProgress, Grid, Paper, Divider, useTheme
} from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';

interface ShortDescription {
  problem: string;
  // solution: string;
}

interface Recommendation {
  category: string;
  impact: string;
  short_description: ShortDescription;
  extended_properties?: Record<string, string>;
  advice: string;
}

const LLMInteraction: React.FC = () => {
  const theme = useTheme(); // Access the current theme
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const handleFetchAndAnalyze = async () => {
    startTransition(() => {
      setIsLoading(true);
      setRecommendations([
        {
          category: 'Cost',
          impact: 'High',
          short_description: {
            problem: 'This is an example cost recommendation description.',
            // solution: 'This is an optimistic solution.',
          },
          advice: 'This is an example piece of advice.',
        },
      ]);
    });

    try {
      const res = await axios.post<{ advice: Recommendation[] }>(
        'http://localhost:5000/api/analyze-recommendations',
        // pass a list of subscriptionids to the backend
        {
          subscription_id: '38c26c07-ccce-4839-b504-cddac8e5b09d',
          // subscription_id: 'c916841c-459e-4bbd-aff7-c235ae45f0dd'
          // subscription_id: '9d923c47-1aa2-4fc9-856f-16ca53e97b76'
        },

        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      console.log('Response Data:', res.data.advice);

      setRecommendations(res.data.advice || []);
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
          <Typography variant="h6" mb={2}>
            Assessment Results:
          </Typography>
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
                    primary={`Recommendation ${index + 1}: ${rec.category}`}
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
                    {/* <Typography variant="body2">
                      <strong>Solution:</strong> {rec.short_description.solution || "No solution available"}
                    </Typography> */}
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
        </>
      )}
    </Box>
  );
};

export default LLMInteraction;