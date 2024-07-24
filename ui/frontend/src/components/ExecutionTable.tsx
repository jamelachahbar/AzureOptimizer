import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableRow, Paper, TableContainer } from '@mui/material';
import { ExecutionData } from '../types';

interface ExecutionTableProps {
  data: ExecutionData[];
}

const ExecutionTable: React.FC<ExecutionTableProps> = ({ data }) => {
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Date</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Details</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((execution) => (
            <TableRow key={execution.date}>
              <TableCell>{execution.date}</TableCell>
              <TableCell>{execution.status}</TableCell>
              <TableCell>{execution.details}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ExecutionTable;
