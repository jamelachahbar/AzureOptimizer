import React, { useState } from 'react';
import {
    Button, Paper, Typography, List, ListItem, ListItemText, Divider, CircularProgress
} from '@mui/material';
import axios from 'axios';

// Define the type for a Recommendation
interface ShortDescription {
    problem: string;
    solution: string;
}

interface Recommendation {
    category: string;
    impact: string;
    shortDescription: ShortDescription;
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
                    subscription_id: '38c26c07-ccce-4839-b504-cddac8e5b09d' // Ensure the correct subscription ID is used
                },
                {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            console.log('Response Data:', res.data.advice); // Debugging line
            setRecommendations(res.data.advice || []);
        } catch (error) {
            console.error('Error querying LLM:', error);
            setRecommendations([]);
        } finally {
            setIsLoading(false);
        }
    };
    return (
        <Paper style={{ padding: 20, margin: 20 }}>
            <Typography variant="h5" style={{ marginBottom: 20 }}>Azure Advisor AI Assistant</Typography>
            <Button
                variant="contained"
                color="primary"
                onClick={handleFetchAndAnalyze}
                disabled={isLoading}
            >
                {isLoading ? <CircularProgress size={24} /> : 'Fetch and Analyze Recommendations'}
            </Button>
            {recommendations.length > 0 && (
                <List style={{ marginTop: 20 }}>
                    {recommendations.map((rec, index) => (
                        <React.Fragment key={index}>
                            <ListItem alignItems="flex-start">
                                <ListItemText
                                    primary={`Recommendation ${index + 1}`}
                                    secondary={
                                        <>
                                            <Typography variant="body2" color="text.primary">
                                                Category: {rec.category}
                                            </Typography>
                                            <Typography variant="body2" color="text.primary">
                                                Impact: {rec.impact}
                                            </Typography>
                                            <Typography variant="body2" color="text.primary">
                                                Problem: {rec.shortDescription.problem}
                                            </Typography>
                                            <Typography variant="body2" color="text.primary">
                                                Solution: {rec.shortDescription.solution}
                                            </Typography>
                                        </>
                                    }
                                />
                            </ListItem>
                            <Divider component="li" />
                        </React.Fragment>
                    ))}
                </List>
            )}
        </Paper>
    );
};

export default LLMInteraction;
