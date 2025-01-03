import React from 'react';
import {
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Paper,
  Switch,
  FormControlLabel,
  FormGroup,
  useTheme,
} from '@mui/material';

interface Policy {
  name: string;
  description: string;
  enabled: boolean;
}

interface PolicyTableProps {
  policies: Policy[];
  handleToggle: (policyName: string, enabled: boolean) => void;
}

const PolicyTable: React.FC<PolicyTableProps> = ({ policies, handleToggle }) => {
  const theme = useTheme();

  return (
    <TableContainer
      component={Paper}
      sx={{
        maxHeight: 400,
        overflowY: 'scroll',
        backgroundColor: theme.palette.background.paper,
      }}
    >
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell
              sx={{
                color: theme.palette.text.primary,
                backgroundColor: theme.palette.mode === 'light' ? '#f4f4f4' : '#1e1e1e',
                fontSize: '0.85rem',
              }}
            >
              Policy Name
            </TableCell>
            <TableCell
              sx={{
                color: theme.palette.text.primary,
                backgroundColor: theme.palette.mode === 'light' ? '#f4f4f4' : '#1e1e1e',
                fontSize: '0.85rem',
              }}
            >
              Description
            </TableCell>
            <TableCell
              align="center"
              sx={{
                color: theme.palette.text.primary,
                backgroundColor: theme.palette.mode === 'light' ? '#f4f4f4' : '#1e1e1e',
                fontSize: '0.85rem',
              }}
            >
              Status
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {policies.map((policy) => (
            <TableRow
              key={policy.name}
              sx={{
                backgroundColor: policy.enabled
                  ? theme.palette.mode === 'light'
                    ? '#E6F4EA' // Dark text for enabled rows in light mode
                    : '#004D40' // Dark blue for dark mode when enabled
                  : theme.palette.mode === 'dark'
                    ? '#333333' // Default background for disabled rows
                    : '#ffff' // Light gray for disabled rows in light mode
                
              }}
            >
              <TableCell
                sx={{
                  fontSize: '0.8rem',
                  color: theme.palette.text.primary,
                }}
              >
                {policy.name}
              </TableCell>
              <TableCell
                sx={{
                  fontSize: '0.8rem',
                  color: theme.palette.text.secondary,
                }}
              >
                {policy.description}
              </TableCell>
              <TableCell align="center">
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={policy.enabled}
                        onChange={() => handleToggle(policy.name, policy.enabled)}
                        color="success"
                      />
                    }
                    label={policy.enabled ? 'Enabled' : 'Disabled'}
                    sx={{
                      fontSize: '0.8rem', // Consistent font size for the label
                      color: theme.palette.text.primary,
                      '& .MuiTypography-root': {
                        fontSize: '0.8rem', // Explicitly target label text
                      },
                    }}
                  />
                </FormGroup>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default PolicyTable;
