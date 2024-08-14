import React from 'react';
import { TableContainer, Table, TableHead, TableRow, TableCell, TableBody, Paper } from '@mui/material';

interface ResourceData {
  Resource: string;
  Action: string;
  Status: string;
  Cost: number;
  Policy: string;
  SubscriptionId: string;
}

interface ImpactedResourcesTableProps {
  impactedResources: ResourceData[];
  selectedSubscription: string;
}

const ImpactedResourcesTable: React.FC<ImpactedResourcesTableProps> = ({ impactedResources, selectedSubscription }) => {
  const filteredImpactedResources = selectedSubscription === 'All Subscriptions'
    ? impactedResources
    : impactedResources.filter((data) => data.SubscriptionId === selectedSubscription);

  return (
    <TableContainer component={Paper} style={{ maxHeight: 400 }}>
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>Resource</TableCell>
            <TableCell>Policy</TableCell>
            <TableCell>Subscription ID</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredImpactedResources.map((resource, index) => (
            <TableRow key={index}>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Resource}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Policy}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.SubscriptionId}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ImpactedResourcesTable;
