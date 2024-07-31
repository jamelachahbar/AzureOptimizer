import React, { useState, useCallback, useEffect } from 'react';
import { Container, Grid, Button, CircularProgress, Typography, FormControl, InputLabel, Select, MenuItem, Paper, Box, TextField } from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Table, TableBody, TableCell, TableHead, TableRow, TableContainer } from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import axios from 'axios';
import { createTheme, ThemeProvider } from '@mui/material/styles';

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

interface SummaryMetric {
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

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

const App: React.FC = () => {
  const [summaryMetrics, setSummaryMetrics] = useState<SummaryMetric[]>([
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
  ]);

  const [isOptimizerRunning, setIsOptimizerRunning] = useState(false);
  const [mode, setMode] = useState('dry-run');
  const [logs, setLogs] = useState<string[]>([]);
  const [selectedSubscription, setSelectedSubscription] = useState<string>('All Subscriptions');
  const [timeout, setTimeout] = useState<number>(60); // default timeout in seconds
  const [errorMessage, setErrorMessage] = useState<string>('');

  const fetchLogStream = useCallback(() => {
    const eventSource = new EventSource('http://127.0.0.1:5000/api/log-stream');
    eventSource.onmessage = (event) => {
      setLogs((prevLogs) => [...prevLogs, event.data]);
    };
    eventSource.onerror = () => {
      eventSource.close();
    };
  }, []);

  const runOptimizer = async () => {
    setIsOptimizerRunning(true);
    setLogs([]);
    fetchLogStream();
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/run', { mode: mode, all_subscriptions: true });
      const data = response.data;
      console.log('Run Optimizer Response:', data);
      setLogs(prevLogs => [...prevLogs, `Optimizer started in ${mode} mode.`]);
    } catch (error) {
      console.error('Error running optimizer:', error);
      setLogs(prevLogs => [...prevLogs, 'Error running optimizer.']);
      setErrorMessage('Error running optimizer. Please check the server.');
      setIsOptimizerRunning(false);
    }
  };

  const stopOptimizer = async () => {
    try {
      await axios.post('http://127.0.0.1:5000/api/stop');
      setIsOptimizerRunning(false);
      setLogs(prevLogs => [...prevLogs, 'Optimizer stopped.']);
    } catch (error) {
      console.error('Error stopping optimizer:', error);
      setLogs(prevLogs => [...prevLogs, 'Error stopping optimizer.']);
    }
  };

  const fetchData = useCallback(async () => {
    try {
      const summaryResponse = await axios.get('http://127.0.0.1:5000/api/summary-metrics');
      const summaryData = summaryResponse.data;
      if (summaryData.length > 0) {
        setSummaryMetrics(summaryData);
        if (!selectedSubscription) {
          setSelectedSubscription('All Subscriptions');
        }
      }
    } catch (error) {
      console.error('Error fetching summary metrics:', error);
      setErrorMessage('Error fetching data from server. Please make sure the server is running.');
      setIsOptimizerRunning(false);
    }

    try {
      const executionResponse = await axios.get('http://127.0.0.1:5000/api/execution-data');
      const executionData = executionResponse.data;
      setExecutionData(executionData);
    } catch (error) {
      console.error('Error fetching execution data:', error);
    }

    try {
      const impactedResourcesResponse = await axios.get('http://127.0.0.1:5000/api/impacted-resources');
      const impactedResourcesData = impactedResourcesResponse.data;
      setImpactedResources(impactedResourcesData);
    } catch (error) {
      console.error('Error fetching impacted resources:', error);
    }

    try {
      const anomaliesResponse = await axios.get('http://127.0.0.1:5000/api/anomalies');
      const anomaliesData = anomaliesResponse.data;
      setAnomalyData(anomaliesData);
    } catch (error) {
      console.error('Error fetching anomaly data:', error);
    }

    try {
      const trendDataResponse = await axios.get('http://127.0.0.1:5000/api/trend-data');
      const trendData = trendDataResponse.data;
      setTrendData(trendData);
    } catch (error) {
      console.error('Error fetching trend data:', error);
    }
  }, [selectedSubscription]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isOptimizerRunning) {
      interval = setInterval(fetchData, 5000);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isOptimizerRunning, fetchData]);

  const handleSubscriptionChange = (event: SelectChangeEvent<string>) => {
    setSelectedSubscription(event.target.value as string);
  };

  const filteredAnomalyData = selectedSubscription === 'All Subscriptions' ? anomalyData : anomalyData.filter(data => data.SubscriptionId === selectedSubscription);
  const filteredTrendData = selectedSubscription === 'All Subscriptions' ? trendData : trendData.filter(data => data.SubscriptionId === selectedSubscription);
  const filteredExecutionData = selectedSubscription === 'All Subscriptions' ? executionData : executionData.filter(data => data.SubscriptionId === selectedSubscription);
  const filteredImpactedResources = selectedSubscription === 'All Subscriptions' ? impactedResources : impactedResources.filter(data => data.SubscriptionId === selectedSubscription);

  const renderSummaryMetricsTable = () => (
    <Grid container spacing={3}>
      {summaryMetrics.map((metric, index) => (
        <Grid item xs={12} md={4} key={index}>
          <Paper style={{ padding: 16, wordBreak: 'break-word' }}>
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

  const renderCostChart = () => (
    <ResponsiveContainer width="100%" height={500}>
      <LineChart data={filteredTrendData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="cost" stroke="#8884d8" activeDot={{ r: 8 }} />
      </LineChart>
    </ResponsiveContainer>
  );

  const renderExecutionTable = () => (
    <TableContainer component={Paper} style={{ maxHeight: 400 }}>
      <Table stickyHeader>
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
          {filteredExecutionData.map((execution, index) => (
            <TableRow key={index}>
              <TableCell style={{ wordBreak: 'break-word' }}>{execution.Action}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{execution.Cost}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{execution.Message}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{execution.Resource}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{execution.Status}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{execution.SubscriptionId}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderImpactedResourcesTable = () => (
    <TableContainer component={Paper} style={{ maxHeight: 400 }}>
      <Table stickyHeader>
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
          {filteredImpactedResources.map((resource, index) => (
            <TableRow key={index}>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Resource}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Action}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Status}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Cost}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Policy}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.SubscriptionId}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderAnomalyTable = () => (
    <TableContainer component={Paper} style={{ maxHeight: 400 }}>
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>Date</TableCell>
            <TableCell>Cost</TableCell>
            <TableCell>Subscription ID</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredAnomalyData.map((anomaly, index) => (
            <TableRow key={index}>
              <TableCell style={{ wordBreak: 'break-word' }}>{anomaly.date}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{anomaly.cost}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{anomaly.SubscriptionId}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <ThemeProvider theme={theme}>
      <Container>
        <Box mt={4} textAlign="center">
          <Typography variant="h4">Team XYZ - Cost Optimizer</Typography>
        </Box>
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
          <Grid item>
            <Button variant="contained" color="secondary" onClick={stopOptimizer} disabled={!isOptimizerRunning}>
              Stop Optimizer
            </Button>
          </Grid>
          <Grid item>
            <TextField
              label="Timeout (seconds)"
              type="number"
              variant="outlined"
              value={timeout}
              onChange={(e) => setTimeout(parseInt(e.target.value, 10))}
            />
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
                <MenuItem value="All Subscriptions">All Subscriptions</MenuItem>
                {summaryMetrics.map(metric => (
                  <MenuItem key={metric.SubscriptionId} value={metric.SubscriptionId}>
                    {metric.SubscriptionId}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
        {errorMessage && (
          <Box mt={4}>
            <Typography variant="h6" color="error">{errorMessage}</Typography>
          </Box>
        )}
        <Box mt={4}>
          <Typography variant="h5">Summary Metrics</Typography>
          {renderSummaryMetricsTable()}
        </Box>
        <Box mt={4}>
          <Typography variant="h5">Cost Trend</Typography>
          {renderCostChart()}
        </Box>
        <Box mt={4}>
          <Typography variant="h5">Execution Data</Typography>
          {renderExecutionTable()}
        </Box>
        <Box mt={4}>
          <Typography variant="h5">Impacted Resources</Typography>
          {renderImpactedResourcesTable()}
        </Box>
        <Box mt={4}>
          <Typography variant="h5">Anomalies</Typography>
          {renderAnomalyTable()}
        </Box>
        <Box mt={4}>
          <Typography variant="h5">Optimizer Logs</Typography>
          <Paper style={{ maxHeight: 300, overflow: 'auto', padding: 16 }}>
            {logs.map((log, index) => (
              <Typography key={index} variant="body1">{log}</Typography>
            ))}
          </Paper>
        </Box>
      </Container>
    </ThemeProvider>
  );
};

export default App;
