import React, { useState } from 'react';
import { Card, CardContent, Typography, Switch, CircularProgress } from '@mui/material';
import axios from 'axios';

interface Policy {
  name: string;
  description: string;
  enabled: boolean;
}

interface PolicyCardProps {
  policy: Policy;
  onPolicyUpdate?: (updatedPolicy: Policy) => void; // Optional callback if needed
}

const PolicyCard: React.FC<PolicyCardProps> = ({ policy, onPolicyUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [currentPolicy, setCurrentPolicy] = useState(policy);

  const handleToggle = async () => {
    const updatedPolicy = { ...currentPolicy, enabled: !currentPolicy.enabled };
    setLoading(true); // Show loading spinner

    try {
      // Send API request to update the policy
      await axios.patch(`/api/policies/${updatedPolicy.name}`, { enabled: updatedPolicy.enabled });
      
      // Update local state
      setCurrentPolicy(updatedPolicy);
      if (onPolicyUpdate) {
        onPolicyUpdate(updatedPolicy); // Notify parent if a callback is provided
      }
    } catch (error) {
      console.error('Error updating policy:', error);
    } finally {
      setLoading(false); // Hide loading spinner
    }
  };

  return (
    <Card
      sx={{
        margin: 2,
        justifyContent: 'flex-start',
        maxWidth: 400,
        maxHeight: 280,
        boxShadow: 3,
        textWrap: 'pretty',
        flexWrap: 'wrap',
        '&:hover': { boxShadow: 6 },
      }}
    >
      <CardContent>
        <Typography variant="h6">{currentPolicy.name}</Typography>
        <Typography variant="h6" color="text.secondary">
          {currentPolicy.description}
        </Typography>
        <Switch
          checked={currentPolicy.enabled}
          onChange={handleToggle}
          color="primary"
          disabled={loading} // Disable while loading
        />
        {loading && <CircularProgress size={20} />} {/* Optional spinner */}
      </CardContent>
    </Card>
  );
};

export default PolicyCard;
