import React, { useState, useTransition } from 'react';
import {
  Button, List, ListItem, ListItemText, Collapse, Paper, useTheme, Checkbox, Select, MenuItem,
} from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import { AnimatedTooltip } from './AnimatedTooltip';
import { SelectChangeEvent } from '@mui/material';
import { v4 as uuidv4 } from 'uuid';
import RecommendationItem from './RecommendationItem';
import { Autocomplete, TextField } from '@mui/material';
import LoginButton from './LoginButton';
import { useIsAuthenticated } from "@azure/msal-react";
import LogoutButton from './LogoutButton';
import {
  Grid,
  CircularProgress,
  Typography,
  Box,
} from '@mui/material';

interface Recommendation {
  uuid: string;
  id: any;
  category: string;
  impact?: string;
  short_description?: { problem: string };
  short_description_s?: { solution: string };
  extended_properties?: Record<string, string>;
  advice?: string;
  subscription_id?: string;
  source?: string;
  SubscriptionGuid?: string;
  Instance?: string;
  generated_date?: string;
  fit_score?: string;
  savingsAmount?: string;
  Impact_s?: string;
  problem?: string;
  solution?: string;
  annualSavingsAmount?: string;
  resource_id?: string;
}

const LLMInteraction_FinopsHubs: React.FC = () => {
  const theme = useTheme();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isFetching, setIsFetching] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [isResultsExpanded, setIsResultsExpanded] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRecommendations, setSelectedRecommendations] = useState<Set<number>>(new Set());
  const [selectAll, setSelectAll] = useState(false);
  const [filterSource, setFilterSource] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const getSubscriptionId = (rec: Recommendation) => {
    if (rec.source === 'Azure API') {
      return rec.extended_properties?.subid || rec.subscription_id || 'N/A';
    } else if (rec.source === 'Log Analytics') {
      return rec.subscription_id || rec.SubscriptionGuid || 'N/A';
    }
    return rec.subscription_id || 'N/A';
  };

  const handleFetchRecommendations = async () => {
    setIsFetching(true);
    setError(null);
    setRecommendations([]);

    try {
      const res = await axios.get('http://localhost:5000/api/review-recommendations');
      if (res.data.message === 'No recommendations available') {
        setError('No recommendations available to display at this time.');
        return;
      }
      if (!Array.isArray(res.data)) {
        setError('Unexpected API response format. Please contact support.');
        return;
      }

      if (res.data.length === 0) {
        setError('No recommendations are currently available.');
      } else {
        const mappedData = res.data.map((rec: any) => ({
          ...rec,
          recommendation_name: rec.problem || rec.short_description?.problem || 'Unnamed Recommendation',
          impact: rec.impact || 'Unknown',
          problem: rec.problem || 'No problem description available',
          solution: rec.solution || 'No solution available',
          resource_id: rec.resource_id || 'N/A',
        }));
        setRecommendations(mappedData);
      }
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      setError('Failed to fetch recommendations. Please try again later.');
    } finally {
      setIsFetching(false);
    }
  };

  const handleSendToLLM = async () => {
    if (selectedRecommendations.size === 0) {
      console.error('No recommendations selected');
      return;
    }

    setIsSending(true);
    setError(null);

    try {
      const mappedRecommendations = Array.from(selectedRecommendations)
        .map(index => recommendations[index])
        .filter(Boolean)
        .map(rec => ({
          ...rec,
          subscription_id: rec.subscription_id || 'N/A',
          uuid: rec.uuid || uuidv4(),
        }));

      const res = await axios.post(
        'http://localhost:5000/api/analyze-recommendations',
        { recommendations: mappedRecommendations },
        { headers: { 'Content-Type': 'application/json' } }
      );

      setRecommendations(prev =>
        prev.map(rec => {
          const updatedRec = res.data.find((r: { recommendation: { uuid: string } }) => r.recommendation?.uuid === rec.uuid);
          return updatedRec ? { ...rec, advice: updatedRec.advice } : rec;
        })
      );
    } catch (error) {
      console.error('Error querying AI Assistant:', error);
      setError('Failed to query the AI Assistant. Please try again later.');
    } finally {
      setIsSending(false);
    }
  };

  const isAuthenticated = useIsAuthenticated();

  if (!isAuthenticated) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <LoginButton />
      </Box>
    );
  }

  return (
    <Box p={2} m={2} border={1} borderRadius={2} borderColor={theme.palette.mode === 'light' ? 'grey.300' : 'grey.700'}>
      <Grid container spacing={2} alignItems="center" justifyContent="space-between">
        <Grid item>
          <Typography variant="h5" gutterBottom>
            Azure Optimizer Assessment
          </Typography>
        </Grid>
        <Grid item>
          <LogoutButton />
        </Grid>
      </Grid>

      {error && (
        <Typography variant="body1" color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleFetchRecommendations}
        disabled={isFetching}
        sx={{ mb: 4 }}
      >
        {isFetching ? <CircularProgress size={24} /> : 'Fetch Recommendations for Review'}
      </Button>

      <Button
        variant="contained"
        color="secondary"
        onClick={handleSendToLLM}
        disabled={isSending || selectedRecommendations.size === 0}
        sx={{ mb: 4, ml: 2 }}
      >
        {isSending ? <CircularProgress size={24} /> : `Send to AI Assistant for Analysis (${selectedRecommendations.size})`}
      </Button>

      {recommendations.length > 0 && (
        <List>
          {recommendations.map((rec, index) => (
            <ListItem key={rec.uuid}>
              <ListItemText
                primary={`Recommendation ${index + 1}: ${rec.problem}`}
                secondary={`Impact: ${rec.impact}`}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
};

export default LLMInteraction_FinopsHubs;
