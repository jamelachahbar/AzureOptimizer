import React, { useEffect, useState } from 'react';
import { Container, Grid, Button } from '@mui/material';
import SummaryMetrics from './components/SummaryMetrics';
import CostChart from './components/CostChart';
import ExecutionTable from './components/ExecutionTable';
import ImpactedResourcesTable from './components/ImpactedResourcesTable';
import { CostData, ExecutionData, ResourceData } from './types';

const App: React.FC = () => {
  const [summaryMetrics, setSummaryMetrics] = useState<any[]>([]);
  const [costData, setCostData] = useState<CostData[]>([]);
  const [executionData, setExecutionData] = useState<ExecutionData[]>([]);
  const [impactedResources, setImpactedResources] = useState<ResourceData[]>([]);


  useEffect(() => {
    // Fetch data from backend
    fetch('http://127.0.0.1:5000/api/summary-metrics')
      .then(res => res.json())
      .then(data => setSummaryMetrics(data));
    fetch('http://127.0.0.1:5000/api/cost-data')
      .then(res => res.json())
      .then(data => setCostData(data));
    fetch('http://127.0.0.1:5000/api/execution-data')
      .then(res => res.json())
      .then(data => setExecutionData(data));
    fetch('http://127.0.0.1:5000/api/impacted-resources')
      .then(res => res.json())
      .then(data => setImpactedResources(data));
  }, []);
  // useEffect(() => {
  //   // Fetch data from backend
  //   fetch('/api/summary-metrics')
  //     .then(res => res.json())
  //     .then(data => {
  //       console.log('Summary Metrics:', data); // Debugging log
  //       setSummaryMetrics(data);
  //     })
  //     .catch(err => console.error('Error fetching summary metrics:', err));
      
  //   fetch('/api/cost-data')
  //     .then(res => res.json())
  //     .then(data => {
  //       console.log('Cost Data:', data); // Debugging log
  //       setCostData(data);
  //     })
  //     .catch(err => console.error('Error fetching cost data:', err));
      
  //   fetch('/api/execution-data')
  //     .then(res => res.json())
  //     .then(data => {
  //       console.log('Execution Data:', data); // Debugging log
  //       setExecutionData(data);
  //     })
  //     .catch(err => console.error('Error fetching execution data:', err));
      
  //   fetch('/api/impacted-resources')
  //     .then(res => res.json())
  //     .then(data => {
  //       console.log('Impacted Resources:', data); // Debugging log
  //       setImpactedResources(data);
  //     })
  //     .catch(err => console.error('Error fetching impacted resources:', err));
  // }, []);

  const runOptimizer = () => {
    fetch('/api/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ mode: 'apply', all_subscriptions: true, use_adls: false })
    })
    .then(response => response.json())
    .then(data => {
      console.log('Run Optimizer Response:', data);
    })
    .catch(err => console.error('Error running optimizer:', err));
  };

  return (
    <Container>
      <Button variant="contained" color="primary" onClick={runOptimizer}>
        Run Optimizer
      </Button>
      <SummaryMetrics data={summaryMetrics} />
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <CostChart data={costData} />
        </Grid>
        <Grid item xs={12} md={6}>
          <ExecutionTable data={executionData} />
        </Grid>
      </Grid>
      <ImpactedResourcesTable data={impactedResources} />
    </Container>
  );
};

export default App;
