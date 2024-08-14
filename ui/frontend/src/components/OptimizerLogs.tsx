import React from 'react';
import { Typography, Paper } from '@mui/material';

interface OptimizerLogsProps {
  logs: string[];
}

const OptimizerLogs: React.FC<OptimizerLogsProps> = ({ logs }) => {
  return (
    <Paper style={{ maxHeight: 300, overflow: 'auto', padding: 16 }}>
      {logs.map((log, index) => (
        <Typography key={index} variant="body1">
          {log}
        </Typography>
      ))}
    </Paper>
  );
};

export default OptimizerLogs;
