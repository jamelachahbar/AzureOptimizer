// components/PolicyCard.tsx

import React from 'react';
import { Card, CardContent, Typography, Switch } from '@mui/material';

// Define an interface for the policy prop directly in this file
interface Policy {
  name: string;
  description: string;
  enabled: boolean;
}

interface PolicyCardProps {
  policy: Policy;
  onToggle: (policyName: string) => void;
}

const PolicyCard: React.FC<PolicyCardProps> = ({ policy, onToggle }) => {
  return (
    <Card sx={{ margin: 2, justifyContent:'flex-start' ,maxWidth: 400, maxHeight: 250,boxShadow: 3, textWrap:'pretty', flexWrap:'wrap', '&:hover': { boxShadow: 6 } }}>
      <CardContent >
        <Typography variant="h5">{policy.name}</Typography>
        <Typography variant="body2" color="text.secondary">
          {policy.description}
        </Typography>
        <Switch
          checked={policy.enabled}
          onChange={() => onToggle(policy.name)}
          color="primary"
        />
      </CardContent>
    </Card>
  );
};

export default PolicyCard;
