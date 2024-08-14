import React, { useState, useCallback, useEffect } from 'react';
import {
  Container,
  Grid,
  Button,
  CircularProgress,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,

  SelectChangeEvent,

 
} from '@mui/material';

import axios from 'axios';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import LLMInteraction from './components/LLMInteraction';
import SummaryMetricsCard from './components/SummaryMetricsCard';
import CostTrendChart from './components/CostTrendChart';
import ExecutionTable from './components/ExecutionTable';
import ImpactedResourcesTable from './components/ImpactedResourcesTable';
import PolicyTable from './components/PolicyTable';
import PolicyPieChart from './components/PolicyPieChart';
import OptimizerLogs from './components/OptimizerLogs';

interface Policy {
  name: string;
  description: string;
  enabled: boolean;
}


interface CostData {
  date: string;
  cost: number;
  SubscriptionId: string;
}

interface SubscriptionCosts {
  [subscriptionId: string]: number;
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
  SubscriptionId: string;
  AverageDailyCost: number;
  MaximumDailyCost: number;
  MinimumDailyCost: number;
  TotalCost: number;
}

interface AnomalyData {
  date: string;
  cost: number;
  SubscriptionId: string;
}



const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AA00FF', '#FF4444'];

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f4f4f4',
      paper: '#ffffff',
    },
    text: {
      primary: '#333333',
      secondary: '#666666',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '8px 16px',
          margin: '0 8px',
          fontSize: '1rem',
        },
        containedPrimary: {
          color: '#ffffff',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 8px 16px rgba(0,0,0,0.1)',
          transition: '0.3s',
          '&:hover': {
            boxShadow: '0 16px 32px rgba(0,0,0,0.2)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          margin: '8px',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          backgroundColor: '#e0e0e0',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 'bold',
        },
        body: {
          fontSize: '0.875rem',
        },
      },
    },
  },
});


// App component definition with functional component
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
    },
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 45,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-3',
      TotalCost: 100,
    },
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 30,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-4',
      TotalCost: 100,
    },
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 20,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-5',
      TotalCost: 100,
    },
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 20,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-6',
      TotalCost: 100,
    },
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 45,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-7',
      TotalCost: 100,
    },
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 30,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-8',
      TotalCost: 100,
    },
    {
      AverageDailyCost: 8,
      MaximumDailyCost: 45,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-9',
      TotalCost: 100,
    },
    {
      AverageDailyCost: 10,
      MaximumDailyCost: 40,
      MinimumDailyCost: 5,
      SubscriptionId: 'mock-subscription-10',
      TotalCost: 100,
    },
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
      Policy: 'stop-unused-vms',
      SubscriptionId: 'mock-subscription-1',
    },
    {
      Resource: 'mock-vm-1',
      Action: 'Stop',
      Status: 'Success',
      Cost: 20,
      Policy: 'stop-unused-vms',
      SubscriptionId: 'mock-subscription-1',
    },
    {
      Resource: 'mock-vm-1',
      Action: 'Downgrade Disk',
      Status: 'Success',
      Cost: 20,
      Policy: 'downgrade-disk',
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
      date: '2024-07-11',
      cost: 50,
      SubscriptionId: 'mock-subscription-1',
    },
    {
      date: '2024-07-12',
      cost: 60,
      SubscriptionId: 'mock-subscription-1',
    },
    {
      date: '2024-07-13',
      cost: 100,
      SubscriptionId: 'mock-subscription-1',
    },
    {
      date: '2024-07-10',
      cost: 50,
      SubscriptionId: 'mock-subscription-2',
    },
    {
      date: '2024-07-11',
      cost: 60,
      SubscriptionId: 'mock-subscription-2',
    },
    {
      date: '2024-07-12',
      cost: 34,
      SubscriptionId: 'mock-subscription-2',
    },
    {
      date: '2024-07-13',
      cost: 80,
      SubscriptionId: 'mock-subscription-2',
    },
  ]);

  const [isOptimizerRunning, setIsOptimizerRunning] = useState(false);
  const [mode, setMode] = useState('dry-run');
  const [logs, setLogs] = useState<string[]>([]);
  const [selectedSubscription, setSelectedSubscription] = useState<string>('All Subscriptions');
  const [timeout, setTimeout] = useState<number>(60); // default timeout in seconds
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeIndex, setActiveIndex] = useState<number>(0);

  useEffect(() => {
    const fetchPolicies = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/policies');
        setPolicies(response.data.policies);
      } catch (error) {
        console.error('Error fetching policies:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPolicies();
  }, []);

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
      setLogs((prevLogs) => [...prevLogs, `Optimizer started in ${mode} mode.`]);
    } catch (error) {
      console.error('Error running optimizer:', error);
      setLogs((prevLogs) => [...prevLogs, 'Error running optimizer.']);
      setErrorMessage('Error running optimizer. Please check the server.');
      setIsOptimizerRunning(false);
    }
  };

  const stopOptimizer = async () => {
    try {
      await axios.post('http://127.0.0.1:5000/api/stop');
      setIsOptimizerRunning(false);
      setLogs((prevLogs) => [...prevLogs, 'Optimizer stopped.']);
    } catch (error) {
      console.error('Error stopping optimizer:', error);
      setLogs((prevLogs) => [...prevLogs, 'Error stopping optimizer.']);
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
      if (trendData && Array.isArray(trendData)) {
        setTrendData(trendData);
      } else {
      setTrendData([]);
      }
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

  const handleTogglePolicy = async (policyName: string, enabled: boolean) => {
    try {
      await axios.post('http://localhost:5000/api/toggle-policy', {
        policy_name: policyName,
        enabled: !enabled,
      });
      setPolicies(policies.map(policy =>
        policy.name === policyName ? { ...policy, enabled: !enabled } : policy
      ));
    } catch (error) {
      console.error('Error updating policy:', error);
    }
  };


  // const filteredAnomalyData =
  //   selectedSubscription === 'All Subscriptions'
  //     ? anomalyData
  //     : anomalyData.filter((data) => data.SubscriptionId === selectedSubscription);

  // Filter metrics based on selected subscription
  const filteredSummaryMetrics =
    selectedSubscription === 'All Subscriptions'
      ? summaryMetrics
      : summaryMetrics.filter((metric) => metric.SubscriptionId === selectedSubscription);

  // const renderAnomalyTable = () => (
  //   <TableContainer component={Paper} style={{ maxHeight: 400 }}>
  //     <Table stickyHeader>
  //       <TableHead>
  //         <TableRow>
  //           <TableCell>Date</TableCell>
  //           <TableCell>Cost</TableCell>
  //           <TableCell>Subscription ID</TableCell>
  //         </TableRow>
  //       </TableHead>
  //       <TableBody>
  //         {filteredAnomalyData.map((anomaly, index) => (
  //           <TableRow key={index}>
  //             <TableCell style={{ wordBreak: 'break-word' }}>{anomaly.date}</TableCell>
  //             <TableCell style={{ wordBreak: 'break-word' }}>{anomaly.cost}</TableCell>
  //             <TableCell style={{ wordBreak: 'break-word' }}>{anomaly.SubscriptionId}</TableCell>
  //           </TableRow>
  //         ))}
  //       </TableBody>
  //     </Table>
  //   </TableContainer>
  // );



  {/* Return the main App component with all the components and data */} 
  return (
    <ThemeProvider theme={theme}>
      {/* // Add SideBar component here */}
      <Container maxWidth="xl">
       {/* add logo here and should stay at top left corner and be local to the repo and located in the public folder of my react app newacologo1.png and make it responsive */}
        {/* <img src="/newacologo1.png" alt="logo" style={{ position: 'fixed', width: 120, height: 100, top: 0, left: 0}}/> */}
      </Container>  

      <Container maxWidth="xl">
        <Typography variant="h4" sx={{ mt: 4, mb: 4, textAlign: 'center' }}>
          Team CSU Azure Infra - Cost Optimizer
        </Typography>

      <Container maxWidth="sm">
          {/* Add LLMInteraction component  */}
          {/* <LLMInteraction /> */}
      </Container>

{/* Controls Row */}
        <Grid container spacing={2} display={'flex'} alignContent={'center'} alignItems={'center'} justifyContent={'center'} marginBottom={2}>
          <Grid item>
            <FormControl variant="outlined" sx={{ minWidth: 120 }}>
              <InputLabel>Subscription</InputLabel>
              <Select value={selectedSubscription} onChange={handleSubscriptionChange} label="Subscription">
                <MenuItem value="All Subscriptions">All Subscriptions</MenuItem>
                {summaryMetrics.map((metric, index) => (
                  <MenuItem key={index} value={metric.SubscriptionId}>
                    {metric.SubscriptionId}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            </Grid>
            <Grid item>
            <FormControl variant="outlined" sx={{ minWidth: 120 }}>
              <InputLabel>Mode</InputLabel>
              <Select value={mode} onChange={(e) => setMode(e.target.value as string)} label="Mode">
                <MenuItem value="dry-run">Dry Run</MenuItem>
                <MenuItem value="apply">Apply</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item>
            <Button variant="contained" color="primary" onClick={runOptimizer} disabled={isOptimizerRunning}>
              Run Optimizer
            </Button>
            {/* // optimizer running indicator */}
            {isOptimizerRunning && <CircularProgress size={24}  sx={{ ml: 1 }
            }          
            />
            }
          </Grid>
          <Grid item>
            <Button variant="contained" color="secondary" onClick={stopOptimizer} disabled={!isOptimizerRunning}>
              Stop Optimizer
            </Button>

          </Grid>
          {/* <Grid item>
            <TextField label="Timeout (seconds)" type="number" variant="outlined" value={timeout}
              onChange={(e) => setTimeout(parseInt(e.target.value, 10))} sx={{ minWidth: 120 }} />
          </Grid> */} 
            
        </Grid>

{/* Error message when server returns error */}
        {errorMessage && (
          <Box mt={4}>
            <Typography variant="h6" color="error">
              {errorMessage}
            </Typography>
          </Box>)}


{/* Data Display Area */}
<Grid container xl={36} sx={{ 
          display: 'flex'
          }}>

  {/* Render Policies */}
  <Grid item xs={12} md={6}>
              <Typography variant="h5" mb={2}>Policies</Typography>
              <PolicyTable policies={policies} handleToggle={handleTogglePolicy} />
    </Grid>

  {/* Pie Chart for Impacted Resources by Policy */}
  <Grid item xl={4} marginLeft={8}>
            <PolicyPieChart impactedResources={impactedResources} />
    </Grid>

  {/* Summary Metrics Row */}
  <Typography variant="h5" mb={2}>Summary Metrics</Typography>
  <Grid container xl={36} spacing={2} sx={{ 
          marginBottom:2,
          display: 'flex'
         }}>
          {filteredSummaryMetrics.map((metric, index) => (
            <Grid item key={index} alignContent={'flex-start'}>
              <SummaryMetricsCard metric={metric} />
            </Grid>
          ))}
        </Grid>

{/* Render Cost Trend Chart */}
  <Grid item xl={12}>
            <Typography variant="h5">Cost Trend</Typography>
            <CostTrendChart trendData={trendData} selectedSubscription={selectedSubscription} />
   </Grid>

{/* Other Data Tables */}

  {/* Render Impacted Resources Table */}
  <Grid item xl={12} md={6}>
            <Typography variant="h5" mb={2}>Impacted Resources</Typography>
            <ImpactedResourcesTable impactedResources={impactedResources} selectedSubscription={selectedSubscription} />
    </Grid>
  
  {/* Render Execution Table */}
  <Grid item xl={12} md={6}>
            <Typography variant="h5" mb={2}>Execution Data</Typography>
            <ExecutionTable executionData={executionData} selectedSubscription={selectedSubscription} />
    </Grid>
 
  {/* Render Anomalies Table */}
          {/* <Grid item xl={12} md={6} >
            <Typography variant="h5" mb={2}>Anomalies</Typography>
            {renderAnomalyTable()}
          </Grid> */}
  </Grid>

{/* Data Display Area for Optimizer Logs */}
  <Grid container spacing={3} sx={{ 
          mt: 6,
          padding: 2,
          display: 'flex',
         }}>
    <Grid item xs={12} md={12}>
            <Typography variant="h5" mb={2}>Optimizer Logs</Typography>
            <OptimizerLogs logs={logs} />
          </Grid>
        </Grid>
    </Container>
     </ThemeProvider>
    );
};

export default App;
