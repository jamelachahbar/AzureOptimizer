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
  FormGroup
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
  return (
    <TableContainer component={Paper} style={{ maxHeight: 400, overflow: 'auto' }}>
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>Policy Name</TableCell>
            <TableCell>Description</TableCell>
            <TableCell align="center">Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {policies.map((policy) => (
            <TableRow key={policy.name}>
              <TableCell>{policy.name}</TableCell>
              <TableCell>{policy.description}</TableCell>
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
