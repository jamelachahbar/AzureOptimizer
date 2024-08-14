import React from 'react';
import { Typography, Paper } from '@mui/material';

interface OptimizerLogsProps {
  logs: string[];
}

const OptimizerLogs: React.FC<OptimizerLogsProps> = ({ logs }) => {
  return (
    <Paper style={{ maxHeight: 400, overflow: 'auto', padding: 2, width: '100%', background: '#f4f4f4'  }}>
      {logs.map((log, index) => (
        <Typography key={index} variant="body1">
          {log}
        </Typography>
      ))}
    </Paper>
  );
};

export default OptimizerLogs;
