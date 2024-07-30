import React, { useEffect, useState } from 'react';
import { Container, Grid, Button, CircularProgress, Typography, FormControl, InputLabel, Select, MenuItem, Paper } from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Table, TableBody, TableCell, TableHead, TableRow, TableContainer } from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';

interface CostData {
  date: string;
  cost: number;
  SubscriptionId: string;
}

interface ExecutionData {
  Action: string;
  Cost: number;
  Message: string;
  Resource: string;
  Status: string;
  SubscriptionId: string;
}

interface ResourceData {
  Resource: string;
  Action: string;
  Status: string;
  Cost: number;
  Policy: string;
  SubscriptionId: string;
}

interface SummaryMetrics {
  AverageDailyCost: number;
  MaximumDailyCost: number;
  MinimumDailyCost: number;
  SubscriptionId: string;
  TotalCost: number;
}

interface AnomalyData {
  date: string;
  cost: number;
  SubscriptionId: string;
}

const App: React.FC = () => {
  // Mock data initialization
  const [summaryMetrics, setSummaryMetrics] = useState<SummaryMetrics[]>([
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 20,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-1',
      TotalCost: 100,
    },
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 20,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-2',
      TotalCost: 100,
    }
  ]);

  const [executionData, setExecutionData] = useState<ExecutionData[]>([
    {
      Action: 'Stop',
      Cost: 10,
      Message: 'VM stopped successfully.',
      Resource: 'mock-vm-1',
      Status: 'Success',
      SubscriptionId: 'mock-subscription-1',
    },
  ]);

  const [impactedResources, setImpactedResources] = useState<ResourceData[]>([
    {
      Resource: 'mock-vm-1',
      Action: 'Stop',
      Status: 'Success',
      Cost: 10,
      Policy: 'Mock Policy',
      SubscriptionId: 'mock-subscription-1',
    },
  ]);

  const [anomalyData, setAnomalyData] = useState<AnomalyData[]>([
    {
      date: '2024-07-10',
      cost: 195.93,
      SubscriptionId: 'mock-subscription-1',
    },
  ]);

  const [trendData, setTrendData] = useState<CostData[]>([
      {
        date: '2024-07-10',
        cost: 50,
        SubscriptionId: 'mock-subscription-1',
      },
      {
        date: '2024-07-10',
        cost: 50,
        SubscriptionId: 'mock-subscription-2',
      },
  ]); // Add state for trend data

  const [isOptimizerRunning, setIsOptimizerRunning] = useState(false);
  const [mode, setMode] = useState('dry-run');
  const [logs, setLogs] = useState<string[]>([]);
  const [selectedSubscription, setSelectedSubscription] = useState<string>('mock-subscription-1');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = () => {
    setIsOptimizerRunning(true);
    fetch('http://127.0.0.1:5000/api/summary-metrics')
      .then(res => res.json())
      .then(data => {
        setSummaryMetrics(data);
        if (data.length > 0 && !selectedSubscription) {
          setSelectedSubscription(data[0].SubscriptionId);
        }
      })
      .catch(err => console.error('Error fetching summary metrics:', err))
      .finally(() => setIsOptimizerRunning(false));


    fetch('http://127.0.0.1:5000/api/execution-data')
      .then(res => res.json())
      .then(data => setExecutionData(data))
      .catch(err => console.error('Error fetching execution data:', err));

    fetch('http://127.0.0.1:5000/api/impacted-resources')
      .then(res => res.json())
      .then(data => setImpactedResources(data))
      .catch(err => console.error('Error fetching impacted resources:', err));

    fetch('http://127.0.0.1:5000/api/anomalies')
      .then(res => res.json())
      .then(data => setAnomalyData(data))
      .catch(err => console.error('Error fetching anomaly data:', err));

    fetch('http://127.0.0.1:5000/api/trend-data')
      .then(res => res.json())
      .then(data => setTrendData(data)) // Fetch trend data
      .catch(err => console.error('Error fetching trend data:', err));
  };

  const runOptimizer = () => {
    setIsOptimizerRunning(true);
    setLogs([]);
    fetch('http://127.0.0.1:5000/api/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ mode: mode, all_subscriptions: true, use_adls: false })
    })
      .then(async response => {
        const text = await response.text();
        try {
          const data = JSON.parse(text);
          console.log('Run Optimizer Response:', data);
          setLogs(prevLogs => [...prevLogs, `Optimizer started in ${mode} mode.`]);
          // Fetch new data after optimizer run
          fetchData();
        } catch (err) {
          console.error('Error parsing response as JSON:', text);
          setLogs(prevLogs => [...prevLogs, 'Error starting optimizer.']);
        }
      })
      .catch(err => {
        console.error('Error running optimizer:', err);
        setLogs(prevLogs => [...prevLogs, 'Error running optimizer.']);
      })
      .finally(() => setIsOptimizerRunning(false));
  };

  const handleSubscriptionChange = (event: SelectChangeEvent<string>) => {
    setSelectedSubscription(event.target.value as string);
  };

  const filteredAnomalyData = anomalyData.filter(data => data.SubscriptionId === selectedSubscription);
  const filteredTrendData = trendData.filter(data => data.SubscriptionId === selectedSubscription); // Filter trend data

  return (
    <Container>
      <Grid container spacing={3} justifyContent="center" alignItems="center" style={{ margin: 20 }}>
        <Grid item>
          <FormControl variant="outlined" style={{ minWidth: 120 }}>
            <InputLabel>Mode</InputLabel>
            <Select
              value={mode}
              onChange={(e) => setMode(e.target.value as string)}
              label="Mode"
            >
              <MenuItem value="dry-run">Dry Run</MenuItem>
              <MenuItem value="apply">Apply</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item>
          <Button variant="contained" color="primary" onClick={runOptimizer} disabled={isOptimizerRunning}>
            Run Optimizer
          </Button>
        </Grid>
        {isOptimizerRunning && (
          <Grid item>
            <CircularProgress />
            <Typography variant="h6" style={{ marginLeft: 10 }}>Optimizer is running...</Typography>
          </Grid>
        )}
      </Grid>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <FormControl variant="outlined" style={{ minWidth: 120 }}>
            <InputLabel>Subscription</InputLabel>
            <Select
              value={selectedSubscription}
              onChange={handleSubscriptionChange}
              label="Subscription"
            >
              {summaryMetrics.map(metric => (
                <MenuItem key={metric.SubscriptionId} value={metric.SubscriptionId}>
                  {metric.SubscriptionId}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12}>
          <SummaryMetrics data={summaryMetrics} />
        </Grid>
        <Grid item xs={12} md={6}>
          <CostChart data={filteredTrendData} /> {/* Display trend data */}
        </Grid>
        <Grid item xs={12} md={6}>
          <ExecutionTable data={executionData} />
        </Grid>
        <Grid item xs={12}>
          <ImpactedResourcesTable data={impactedResources} />
        </Grid>
        <Grid item xs={12}>
          <AnomalyTable data={filteredAnomalyData} />
        </Grid>
      </Grid>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Typography variant="h6">Optimizer Logs</Typography>
          <Paper>
            {logs.map((log, index) => (
              <Typography key={index} variant="body1">{log}</Typography>
            ))}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

const SummaryMetrics: React.FC<{ data: SummaryMetrics[] }> = ({ data }) => (
  <Grid container spacing={3}>
    {data.map((metric, index) => (
      <Grid item xs={12} md={4} key={index}>
        <Paper>
          <Typography variant="h6">Subscription: {metric.SubscriptionId}</Typography>
          <Typography variant="body1">Average Daily Cost: {metric.AverageDailyCost}</Typography>
          <Typography variant="body1">Maximum Daily Cost: {metric.MaximumDailyCost}</Typography>
          <Typography variant="body1">Minimum Daily Cost: {metric.MinimumDailyCost}</Typography>
          <Typography variant="body1">Total Cost: {metric.TotalCost}</Typography>
        </Paper>
      </Grid>
    ))}
  </Grid>
);

const CostChart: React.FC<{ data: CostData[] }> = ({ data }) => (
  <ResponsiveContainer width="100%" height={400}>
    <LineChart data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="date" />
      <YAxis />
      <Tooltip />
      <Legend />
      <Line type="monotone" dataKey="cost" stroke="#8884d8" activeDot={{ r: 8 }} />
    </LineChart>
  </ResponsiveContainer>
);

const ExecutionTable: React.FC<{ data: ExecutionData[] }> = ({ data }) => (
  <TableContainer component={Paper}>
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>Action</TableCell>
          <TableCell>Cost</TableCell>
          <TableCell>Message</TableCell>
          <TableCell>Resource</TableCell>
          <TableCell>Status</TableCell>
          <TableCell>Subscription ID</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {data.map((execution) => (
          <TableRow key={execution.Resource}>
            <TableCell>{execution.Action}</TableCell>
            <TableCell>{execution.Cost}</TableCell>
            <TableCell>{execution.Message}</TableCell>
            <TableCell>{execution.Resource}</TableCell>
            <TableCell>{execution.Status}</TableCell>
            <TableCell>{execution.SubscriptionId}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </TableContainer>
);

const ImpactedResourcesTable: React.FC<{ data: ResourceData[] }> = ({ data }) => (
  <TableContainer component={Paper}>
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>Resource</TableCell>
          <TableCell>Action</TableCell>
          <TableCell>Status</TableCell>
          <TableCell>Cost</TableCell>
          <TableCell>Policy</TableCell>
          <TableCell>Subscription ID</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {data.map((resource) => (
          <TableRow key={resource.Resource}>
            <TableCell>{resource.Resource}</TableCell>
            <TableCell>{resource.Action}</TableCell>
            <TableCell>{resource.Status}</TableCell>
            <TableCell>{resource.Cost}</TableCell>
            <TableCell>{resource.Policy}</TableCell>
            <TableCell>{resource.SubscriptionId}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </TableContainer>
);

const AnomalyTable: React.FC<{ data: AnomalyData[] }> = ({ data }) => (
  <TableContainer component={Paper}>
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>Date</TableCell>
          <TableCell>Cost</TableCell>
          <TableCell>Subscription ID</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {data.map((anomaly, index) => (
          <TableRow key={index}>
            <TableCell>{anomaly.date}</TableCell>
            <TableCell>{anomaly.cost}</TableCell>
            <TableCell>{anomaly.SubscriptionId}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </TableContainer>
);

export default App;
