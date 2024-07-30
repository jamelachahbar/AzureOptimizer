import React from 'react';
import { Grid, Paper, Typography } from '@mui/material';

interface SummaryMetricsProps {
  data: any[];
}

const SummaryMetrics: React.FC<SummaryMetricsProps> = ({ data }) => {
  return (
    <Grid container spacing={3}>
      {data.map((metric, index) => (
        <Grid item xs={12} md={4} key={index}>
          <Paper style={{ padding: 16 }}>
            <Typography variant="h6">{metric.title}</Typography>
            <Typography variant="h4">{metric.value}</Typography>
          </Paper>
        </Grid>
      ))}
    </Grid>
  );
};

export default SummaryMetrics;
