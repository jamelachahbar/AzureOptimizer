import React, { useState } from 'react';
import {
  Button, Box, Typography, List, ListItem, Divider, CircularProgress, Grid, Paper
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
  advice: string;  // New field to capture AI-generated advice
}

const LLMInteraction: React.FC = () => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleFetchAndAnalyze = async () => {
    setIsLoading(true);
    try {
      const res = await axios.post<{ advice: Recommendation[] }>(
        'http://localhost:5000/api/analyze-recommendations',
        {
          subscription_id: '38c26c07-ccce-4839-b504-cddac8e5b09d'
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
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

  return (
    <Box p={2} m={2} border={1} borderRadius={2} borderColor="grey.300">
      <Typography variant="h5" gutterBottom>
        AI Assistant Assessment
      </Typography>
      <Button
        variant="contained"
        color="primary"
        onClick={handleFetchAndAnalyze}
        disabled={isLoading}
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
                        <strong>AI Advice:</strong> {rec.advice || "No advice available"}
                      </Typography>
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
