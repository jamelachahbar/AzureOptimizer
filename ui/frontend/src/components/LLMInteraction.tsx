import React, { useState, useTransition } from 'react';
import {
  Button, Box, Typography, List, Paper, CircularProgress, Grid
} from '@mui/material';
import axios from 'axios';

interface ShortDescription {
  problem: string;
  solution: string;
}

interface Recommendation {
  category: string;
  impact: string;
  short_description: ShortDescription;
  extended_properties?: Record<string, string>;
  advice: string;
}

const LLMInteraction: React.FC = () => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isPending, startTransition] = useTransition();

  const handleFetchAndAnalyze = async () => {
    // Start the optimistic update
    startTransition(() => {
      setIsLoading(true);
      setRecommendations([
        {
          category: 'Optimistic Category',
          impact: 'Optimistic Impact',
          short_description: {
            problem: 'This is an optimistic problem description.',
            solution: 'This is an optimistic solution.',
          },
          advice: 'This is an optimistic piece of advice.',
        },
      ]);
    });

    try {
      const res = await axios.post<{ advice: Recommendation[] }>(
        'http://localhost:5000/api/analyze-recommendations',
        {
          subscription_id: '38c26c07-ccce-4839-b504-cddac8e5b09d',
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      console.log('Response Data:', res.data.advice);

      // Update the state with the actual data
      setRecommendations(res.data.advice || []);
    } catch (error) {
      console.error('Error querying AI Assistant:', error);
      setRecommendations([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to render the AI advice with basic formatting
  const renderFormattedAdvice = (advice: string) => {
    const lines = advice.split('\n').map((line, index) => {
      // Handle bold text
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

      // Handle bullet points
      if (line.trim().startsWith('- ')) {
        return (
          <Typography key={index} variant="body2" component="li" style={{ marginLeft: '20px' }}>
            {line.trim().slice(2)}
          </Typography>
        );
      }

      // Handle numbered lists
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
    <Box p={2} m={2} border={1} borderRadius={2} borderColor="grey.300">
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
                <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={8}>
                      <Typography variant="subtitle1" fontWeight="bold">
                        Recommendation {index + 1}
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        <strong>Category:</strong> {rec.category}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Impact:</strong> {rec.impact}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Problem:</strong> {rec.short_description.problem || "No problem description available"}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Solution:</strong> {rec.short_description.solution || "No solution available"}
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 2 }}>
                        <strong>AI Advice:</strong>
                      </Typography>
                      <Box ml={2}>
                        {renderFormattedAdvice(rec.advice || "No advice available")}
                      </Box>
                    </Grid>
                    <Grid item xs={12} sm={6} md={4}>
                      {rec.extended_properties && (
                        <Box sx={{ mt: { xs: 2, sm: 0 }, p: 2, border: '1px solid', borderColor: 'grey.400', borderRadius: 2, bgcolor: 'grey.50' }}>
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
                    </Grid>
                  </Grid>
                </Paper>
              </React.Fragment>
            ))}
          </List>
        </>
      )}
    </Box>
  );
};

export default LLMInteraction;
