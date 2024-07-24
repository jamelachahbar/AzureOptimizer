import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableRow, Paper, TableContainer } from '@mui/material';
import { ResourceData } from '../types';

interface ImpactedResourcesTableProps {
  data: ResourceData[];
}

const ImpactedResourcesTable: React.FC<ImpactedResourcesTableProps> = ({ data }) => {
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Resource</TableCell>
            <TableCell>Action</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((resource) => (
            <TableRow key={resource.resource}>
              <TableCell>{resource.resource}</TableCell>
              <TableCell>{resource.action}</TableCell>
              <TableCell>{resource.status}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ImpactedResourcesTable;
