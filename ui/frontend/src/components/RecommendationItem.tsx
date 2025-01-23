import React from 'react';
import { Box, Chip } from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { OverridableStringUnion } from '@mui/types';
import { ChipPropsColorOverrides } from '@mui/material/Chip';
import { QuestionMarkRounded } from '@mui/icons-material';

// Define the type for priority
type Priority = {
  icon: React.ReactElement;
  label: string;
  color: OverridableStringUnion<"error" | "warning" | "success" | "info" | "default" | "primary" | "secondary", ChipPropsColorOverrides>;
};

const getPriority = (annualSavingsAmount: number): Priority => {
  if (annualSavingsAmount >= 800) return { label: 'High Priority', color: 'error', icon: <WarningIcon /> };
  if (annualSavingsAmount >= 500) return { label: 'Medium Priority', color: 'warning', icon: <WarningIcon /> };
  if (annualSavingsAmount > 0) return { label: 'Low Priority', color: 'success', icon: <CheckCircleIcon /> };
  // Default case if there is no savings
  return { label: 'No savings Info!', color: 'info', icon: <QuestionMarkRounded /> };
};

type RecommendationItemProps = {
  rec: {
    extended_properties?: {
      annualSavingsAmount?: string;
    };
    additional_info?: string;
    source?: string;
    savingsAmount?: string; // Added for Log Analytics
    annualSavingsAmount?: string; // Added for Log Analytics
    problem?: string;
    resource_id?: string;

  };
  isExpanded?: boolean;
  onToggle: () => void;
};

const RecommendationItem: React.FC<RecommendationItemProps> = ({ rec }) => {
  let savingsAmount = 0;

  // Determine savings amount based on the source
  if (rec.source === 'Azure API' && rec.extended_properties) {
    savingsAmount = parseFloat(rec.extended_properties.annualSavingsAmount || '0');
  } 
  // else if (rec.source === 'SQL DB' && rec.additional_info) {
  //   try {
  //     // Parse additional_info (which is a JSON string)
  //     const additionalInfoObj = JSON.parse(rec.additional_info);
  //     savingsAmount = parseFloat(additionalInfoObj.annualSavingsAmount || '0');
  //   } catch (error) {
  //     console.error('Error parsing additional_info JSON:', error);
  //   }
  // } 
  else if (rec.source === 'Log Analytics' && rec.annualSavingsAmount) {
    savingsAmount = parseFloat(rec.annualSavingsAmount || '0');

  }

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
};

export default RecommendationItem;
