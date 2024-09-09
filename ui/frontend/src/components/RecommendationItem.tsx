import React from 'react';
import { Box, Chip } from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { OverridableStringUnion } from '@mui/types';
import { ChipPropsColorOverrides } from '@mui/material/Chip';
import { QuestionMark } from '@mui/icons-material';

// Define the type for priority
type Priority = {
  icon: React.ReactElement;
  label: string;
  color: OverridableStringUnion<"error" | "warning" | "success" | "info" | "default" | "primary" | "secondary", ChipPropsColorOverrides>;
};

// Helper function to determine the priority based on savings amount
const getPriority = (annualSavingsAmount: number): Priority => {
  if (annualSavingsAmount >= 900) return { label: 'High Priority', color: 'error', icon: <WarningIcon /> };
  if (annualSavingsAmount >= 400) return { label: 'Medium Priority', color: 'warning', icon: <WarningIcon /> };
  if (annualSavingsAmount > 0) return { label: 'Low Priority', color: 'success', icon: <CheckCircleIcon /> };
  return { label: 'No savings info!', color: 'info', icon: <QuestionMark /> };
};

// Define the prop types for RecommendationItem
type RecommendationItemProps = {
  rec: {
    extended_properties?: {
      annualSavingsAmount?: string;
    };
    additional_info?: string; // Now this is a JSON string for SQL DB
    source: string;
  };
};

// Main component to render the priority badge
const RecommendationItem: React.FC<RecommendationItemProps> = ({ rec }) => {
  let savingsAmount = 0;

  // Check if the source is Azure API
  if (rec.source === 'Azure API') {
    savingsAmount = parseFloat(rec.extended_properties?.annualSavingsAmount || '0');
  } 
  // Handle SQL DB source where additional_info is a JSON string
  else if (rec.source === 'SQL DB' && rec.additional_info) {
    try {
      const additionalInfo = JSON.parse(rec.additional_info);
      savingsAmount = parseFloat(additionalInfo.annualSavingsAmount || '0');
    } catch (error) {
      console.error("Failed to parse additional_info JSON:", error);
    }
  }

  // Get the priority based on the savings amount
  const priority = getPriority(savingsAmount);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', minWidth: '150px' }}>
      {/* Priority Badge */}
      <Chip
        icon={priority.icon}
        label={priority.label}
        color={priority.color} // Ensures predefined values or custom overrides are used
        sx={{ fontWeight: 'bold', height: '40px' }} // Ensure consistent height for all badges
      />
    </Box>
  );
};

export default RecommendationItem;
