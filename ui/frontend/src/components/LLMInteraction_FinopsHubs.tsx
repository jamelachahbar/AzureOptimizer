import React, { useEffect, useState } from 'react';
import {
  Button,
  Checkbox,
  CircularProgress,
  Collapse,
  FormControl,
  Grid,
  InputLabel,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Typography,
  Box,
  TextField,
  styled
} from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import { useAuth } from '../providers/AuthProvider';
import LoginButton from './LoginButton';
import LogoutButton from './LogoutButton';
import { useIsAuthenticated } from "@azure/msal-react";
import RecommendationItem from './RecommendationItem'; // For priority badges
import { v4 as uuidv4 } from 'uuid';
import ReactMarkdown from 'react-markdown';

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
  const { tenantId, token } = useAuth(); // Fetch tenantId and token here
  const isAuthenticated = useIsAuthenticated();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isFetching, setIsFetching] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [subscriptionIds, setSubscriptionIds] = useState<string[]>([]);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRecommendations, setSelectedRecommendations] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [subscriptions, setSubscriptions] = useState<{ id: string; name: string }[]>([]);
  const [loadingSubscriptions, setLoadingSubscriptions] = useState(false);
  const [loading, setLoading] = useState<boolean>(false);


  useEffect(() => {
    // Ensure the user is authenticated
    if (!isAuthenticated) {
      setError('User is not authenticated.');
      return;
    }

    const fetchSubscriptions = async () => {
      // Ensure authentication details are present
      if (!tenantId || !token) {
        setError('Authentication details are missing. Please log in again.');
        return;
      }

      try {
        setLoadingSubscriptions(true); // Set loading state
        const res = await axios.get(
          'https://management.azure.com/subscriptions?api-version=2020-01-01',
          { headers: { Authorization: `Bearer ${token}` } } // Pass token in headers
        );

        // Process subscription data
        if (res.data?.value) {
          setSubscriptions(
            res.data.value.map((sub: any) => ({
              id: sub.subscriptionId,
              name: sub.displayName,
            }))
          );
          setError(null); // Clear any previous errors
        } else {
          setError('No subscriptions found.');
        }
      } catch (error) {
        console.error('Error fetching subscriptions:', error);
        setError('Failed to fetch subscriptions. Please try again later.');
      } finally {
        setLoadingSubscriptions(false); // Reset loading state
      }
    };

    // Trigger the fetch function
    fetchSubscriptions();
  }, [isAuthenticated, tenantId, token]); // Run whenever `isAuthenticated`, `tenantId`, or `token` changes

  // make sure you first check if customer is logged in, then don't check the token anymore
  const handleFetchRecommendations = async () => {
    if (!tenantId) {
      setError('Tenant ID is missing. Please log in again.');
      return;
    }
    if (subscriptionIds.length === 0) {
      setError('No subscriptions selected. Please select at least one subscription.');
      return;
    }

    setIsFetching(true);
    setError(null);
    setRecommendations([]);

    try {
      const res = await axios.post(
        'http://localhost:5000/api/review-recommendations',
        { tenantId, subscriptionIds },
        { headers: { 'Content-Type': 'application/json' } },
      );

      if (!Array.isArray(res.data)) {
        setError('Unexpected API response format. Please contact support.');
        return;
      }

      if (res.data.length === 0) {
        setError('No recommendations are currently available.');
      } else {
        const mappedData = res.data.map((rec: any) => ({
          ...rec,
          problem: rec.short_description?.problem || 'No problem description available',
          solution: rec.short_description?.solution || 'No solution available',
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
    if (!tenantId) {
      setError('Tenant ID is missing. Please log in again.');
      return;
    }
    if (selectedRecommendations.size === 0) {
      setError('No recommendations selected for analysis.');
      return;
    }

    setIsSending(true);
    setError(null);

    try {
      const selectedRecs = Array.from(selectedRecommendations)
        .map((index) => recommendations[index])
        .filter(Boolean)
        .map((rec) => ({
          ...rec,
          subscription_id: rec.subscription_id || 'N/A',
          uuid: rec.uuid || uuidv4(),
        }));

      const res = await axios.post(
        'http://localhost:5000/api/analyze-recommendations',
        { tenantId, recommendations: selectedRecs },
        { headers: { 'Content-Type': 'application/json' } },
      );

      setRecommendations((prev) =>
        prev.map((rec) => {
          const updatedRec = res.data.find((r: { recommendation: { uuid: string } }) => r.recommendation?.uuid === rec.uuid);
          return updatedRec ? { ...rec, advice: updatedRec.advice } : rec;
        }),
      );
    } catch (error) {
      console.error('Error querying AI Assistant:', error);
      setError('Failed to query the AI Assistant. Please try again later.');
    } finally {
      setIsSending(false);
    }
  };

  const toggleRowExpansion = (index: number) => {
    setExpandedIndex((prev) => (prev === index ? null : index));
  };

  const handleSelectRecommendation = (index: number) => {
    setSelectedRecommendations((prev) => {
      const updated = new Set(prev);
      if (updated.has(index)) {
        updated.delete(index);
      } else {
        updated.add(index);
      }
      return updated;
    });
  };

  const StyledMarkdownContainer = styled('div')({
    fontSize: '1rem',
    lineHeight: 1.5,
    '& h1': {
      fontSize: '1.5rem',
      fontWeight: 'bold',
      marginBottom: '1rem',
    },
    '& h2': {
      fontSize: '1.25rem',
      fontWeight: 'bold',
      marginBottom: '1rem',
    },
    '& h3': {
      fontSize: '1rem',
      fontWeight: 'bold',
      marginBottom: '1rem',
    },
    '& p': {
      marginBottom: '0.5rem',
    },
    '& ul': {
      paddingLeft: '20px',
      marginBottom: '1rem',
    },
    '& li': {
      marginBottom: '0.5rem',
    },
    '& strong': {
      fontWeight: 'bold',
    },
  });

  const renderFormattedAdvice = (advice: string) => (
    <StyledMarkdownContainer>
      <ReactMarkdown>{advice}</ReactMarkdown>
    </StyledMarkdownContainer>
  );


  const renderExtendedProperties = (rec: Recommendation) => {
    const properties = rec.extended_properties || {};
    return (
      <div style={{ marginTop: '1rem' }}>
        <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>Extended Properties:</div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ border: '1px solid #ddd', padding: '8px', backgroundColor: '#f4f4f4', fontWeight: 'bold' }}>
                Property
              </th>
              <th style={{ border: '1px solid #ddd', padding: '8px', backgroundColor: '#f4f4f4', fontWeight: 'bold' }}>
                Value
              </th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(properties).map(([key, value]) => (
              <tr key={key}>
                <td style={{ border: '1px solid #ddd', padding: '8px' }}>{key}</td>
                <td style={{ border: '1px solid #ddd', padding: '8px' }}>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };


  const filteredRecommendations = recommendations.filter(
    (rec) =>
      rec.problem?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rec.resource_id?.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  if (!isAuthenticated) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <LoginButton />
      </Box>
    );
  }

  const handleSubscriptionSelection = (event: SelectChangeEvent<string[]>) => {
    const selected = event.target.value as string[];
    setSubscriptionIds(selected);
  };

  return (
    <Box p={2} m={2} border={1} borderRadius={2} borderColor="grey.300">
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
      <FormControl fullWidth sx={{ mb: 4 }}>
        <InputLabel id="subscription-select-label">Select Subscriptions</InputLabel>
        <Select
          labelId="subscription-select-label"
          id="subscription-select"
          multiple
          value={subscriptionIds}
          onChange={handleSubscriptionSelection}
          renderValue={(selected) => selected.join(', ')}
        >
          {!loadingSubscriptions && subscriptions.length > 0 && (
            subscriptions.map((sub) => (
              <MenuItem key={sub.id} value={sub.id}>
                <Checkbox checked={subscriptionIds.includes(sub.id)} />
                {sub.name} ({sub.id})
              </MenuItem>
            ))
          )}
          {loadingSubscriptions && (
            <MenuItem disabled>
              <CircularProgress size={24} />
              Loading Subscriptions...
            </MenuItem>
          )}
        </Select>
      </FormControl>

      <TextField
        label="Search Recommendations"
        variant="outlined"
        fullWidth
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        sx={{ mb: 4 }}
      />

      <Button
        variant="contained"
        color="primary"
        onClick={handleFetchRecommendations}
        disabled={isFetching || subscriptionIds.length === 0}
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

      {filteredRecommendations.length > 0 && (
        <List>
          {filteredRecommendations.map((rec, index) => (
            <React.Fragment key={rec.uuid}>
              <ListItem>
                <Box display="flex" alignItems="center">
                  <Checkbox
                    checked={selectedRecommendations.has(index)}
                    onChange={() => handleSelectRecommendation(index)}
                    inputProps={{ 'aria-label': `select recommendation ${index}` }}
                  />
                </Box>

                <Box display="flex" alignItems="center" mr={2}>
                  <RecommendationItem rec={rec} onToggle={function (): void {
                    throw new Error('Function not implemented.');
                  }} />
                </Box>

                <ListItemText
                  primary={
                    <Typography variant="body1">
                      <strong>Subscription:</strong> {rec.subscription_id || 'N/A'} -{' '}
                      <strong>Recommendation {index + 1}:</strong> {rec.category || 'N/A'}{' '}
                      <strong>Source:</strong> {rec.source || 'N/A'}
                    </Typography>
                  }
                  secondary={
                    <>
                      <Typography variant="body2">
                        <strong>Impact:</strong> {rec.impact || 'Unknown'}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Problem:</strong> {rec.problem || 'No problem description available'}
                      </Typography>
                    </>
                  }
                />
                <Button onClick={() => toggleRowExpansion(index)}>
                  {expandedIndex === index ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </Button>
              </ListItem>
              <Collapse in={expandedIndex === index} timeout="auto" unmountOnExit>
                <div style={{ padding: '16px', marginBottom: '16px', border: '1px solid #ddd', borderRadius: '4px', maxHeight: '300px', overflowY: 'auto' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>AI Advice:</div>
                  {renderFormattedAdvice(rec.advice || 'No advice available')}
                  {renderExtendedProperties(rec)}
                </div>
              </Collapse>

            </React.Fragment>
          ))}
        </List>

      )}
    </Box>
  );
};

export default LLMInteraction_FinopsHubs;


