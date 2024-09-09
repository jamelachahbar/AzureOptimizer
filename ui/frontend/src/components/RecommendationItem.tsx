import React from 'react';
import { Box, Chip} from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const getPriority = (savingsAmount: number) => {
  if (savingsAmount > 100) return { label: 'High Priority', color: 'error', icon: <WarningIcon /> };
  if (savingsAmount > 50) return { label: 'Medium Priority', color: 'warning', icon: <WarningIcon /> };
  if (savingsAmount > 0) return { label: 'Low Priority', color: 'success', icon: <CheckCircleIcon /> };
  // if there is no savings amount, it is a low priority recommendation
  if (savingsAmount === 0) return { label: 'Low Priority', color: 'success', icon: <CheckCircleIcon /> };
  return { label: 'Unknown Priority', color: 'info', icon: <WarningIcon /> };
};


function RecommendationItem({ rec={
  extended_properties: {
    savingsAmount: '0'
} } }) {
  const savingsAmount = parseFloat(rec.extended_properties?.savingsAmount || '0');
  const priority = getPriority(savingsAmount);

  return (
      <Box sx={{ display: 'flex', alignItems: 'center', minWidth: '150px' }}>
          {/* Priority Badge */}
          <Chip
              icon={priority.icon}
              label={priority.label}
              color={priority.color} // This ensures you are using one of the predefined values or a custom override
              sx={{ fontWeight: 'bold', height: '40px' }} // Ensure consistent height for all badges
          />
      </Box>
  );
}

export default RecommendationItem;

