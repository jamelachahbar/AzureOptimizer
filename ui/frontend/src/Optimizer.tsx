import React, { useState, useCallback, useEffect, useMemo, createContext, useContext, SyntheticEvent } from 'react';
import {
  Container,
  Grid,
  CircularProgress,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  SelectChangeEvent,
} from '@mui/material';
import Button from '@mui/material/Button';
import axios from 'axios';
import { useTheme } from '@mui/material/styles';

import Header from './components/Header'; // Import the Header component
import TracingBeamContainer from './components/TracingBeamContainer'; // Import the TracingBeamContainer
import { Highlight } from './components/HeroHighlight';
import TypewriterEffectSmooth from './components/TypewriterEffectSmooth'; // Import the TypewriterEffectSmooth component
import TypewriterEffect from './components/TypewriterEffect';
import FlipText from './components/FlipWords'; // Import the FlipWords component

import SummaryMetricsCard from './components/SummaryMetricsCard';
import CostTrendChart from './components/CostTrendChart';
import ExecutionTable from './components/ExecutionTable';
import ImpactedResourcesTable from './components/ImpactedResourcesTable';
import PolicyTable from './components/PolicyTable';
import PolicyPieChart from './components/PolicyPieChart';
import OptimizerLogs from './components/OptimizerLogs';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

import PolicyEditor from './components/PolicyEditor'; // Import the new PolicyEditor component
import { LandingScreen } from './components/LandingScreen'; // Import the LandingScreen component
import LoginButton from './components/LoginButton';
import LogoutButton from './components/LogoutButton';  // Import the LogoutButton

import { AuthProvider, useAuth } from './providers/AuthProvider';
import { useIsAuthenticated } from "@azure/msal-react";

// Define the ColorModeContext here
export const ColorModeContext = createContext({ toggleColorMode: () => { } });

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



// App component definition with functional component
const Optimizer: React.FC = () => {
  const [isDarkMode, setIsDarkMode] = useState(false); // State to toggle between themes

  const isAuthenticated = useIsAuthenticated();

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

  // Theme mode context and toggle logic
  const colorMode = useContext(ColorModeContext);
  const theme = useTheme();

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

  const { isAdmin } = useAuth();

  const runOptimizer = async () => {
    if (mode === "apply" && !isAdmin) {
      alert("You do not have sufficient permissions to use Apply mode.");
      return;
    }
    // Continue with the function if the user has sufficient permissions
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


  // const [loading, setLoading] = useState(true); // Control the landing screen visibility

  // const handleLandingFinished = () => {
  //   setLoading(false);
  // };

  // if (loading) {
  //   return <LandingScreen onFinished={handleLandingFinished} />;
  // }
  if (!isAuthenticated) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >

        <LoginButton />
      </Box>
    );
  }
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
      }}>
      {/* <Header />   */}

      {/* Full-width header at the top */}

      <Container
        sx={{
          maxWidth: "1200px",
          margin: '0 auto',
          display: 'flex',
          position: 'center',
          // marginLeft: 'auto',
          maxHeight: '80%',
          flex: 1,
          // mt: 7.5,
          // mb: 4,
          // adjust on smaller screen width
          padding: theme.spacing(2),
          // boxShadow: 'rgba(0, 0, 0, 0.2) 0px 19px 36px, rgba(0, 10, 2, 0.6) 0px 12px 12px',
          // boxShadow: 'rgba(17, 17, 26, 0.1) 0px 0px 1px',
          boxShadow: 'rgba(9, 30, 66, 0.25) 0px 4px 8px -2px, rgba(9, 30, 66, 0.08) 0px 0px 0px 1px',
          borderRadius: 2,
          zIndex: 2, // Higher than the background, lower than other overlays (if any)
          backgroundColor: theme.palette.mode === 'light'
            ? 'rgba(255, 255, 255, 0.9)'
            : '#1A1A1A',
          backdropFilter: 'blur(10px)',

        }}
      >
        <TracingBeamContainer>

          <Typography variant="h4" sx={{ mb: 4, textAlign: 'center' }}>
            Azure Optimizer Tool
          </Typography>

          <Typography variant="h6" sx={{ mb: 4, textAlign: 'center' }}>
            <Highlight>Optimize</Highlight>your<Highlight>Azure Infrastructure costs</Highlight>
          </Typography>

          {/* New Policy Editor Component */}
          {/* <Grid container spacing={2} rowSpacing={2}>
            <Grid item xs={12}>
              <PolicyEditor policies={policies} setPolicies={setPolicies} isLoading={isLoading} />
            </Grid>
          </Grid> */}

          {/* <LLMInteraction /> */}

          <Grid container spacing={2} rowSpacing={2} display="flex" alignContent="center" alignItems="center" justifyContent="center" marginBottom={2}>

            {/* <Grid item xs={12}>
              <PolicyEditor policies={policies} setPolicies={setPolicies} isLoading={isLoading} />
            </Grid> */}
          </Grid>
          <Grid container spacing={2} display="flex" alignContent="center" alignItems="center" justifyContent="center" marginBottom={2}>

            <Grid item>
              <FormControl
                variant="outlined"
                sx={{
                  minWidth: 120,
                  fontSize: '0.8rem', // Match the button font size
                }}
              >
                <InputLabel
                  sx={{
                    fontSize: '0.8rem', // Match the button font size
                  }}>Subscription</InputLabel>
                <Select value={selectedSubscription} onChange={handleSubscriptionChange} label="Subscription"
                  sx={{
                    fontSize: '0.8rem', // Match the button font size
                  }}>
                  <MenuItem value="All Subscriptions"
                    sx={{
                      fontSize: '0.8rem', // Match the button font size
                    }}>All Subscriptions</MenuItem>
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
                <Select value={mode} onChange={(e) => setMode(e.target.value as string)} label="Mode"
                  sx={{
                    fontSize: '0.8rem', // Match the button font size
                  }}>
                  <MenuItem
                    value="dry-run"
                    sx={{
                      fontSize: '0.8rem', // Match the button font size
                    }}>Dry Run</MenuItem>
                  <MenuItem value="apply"
                    sx={{
                      fontSize: '0.8rem', // Match the button font size
                    }}>Apply</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item>
              <Button variant="contained" color="primary" onClick={runOptimizer} disabled={isOptimizerRunning}>
                Run Optimizer
              </Button>
              {isOptimizerRunning && <CircularProgress size={24} sx={{ ml: 1 }} />}
            </Grid>
            <Grid item>
              <Button variant="contained" color="secondary" onClick={stopOptimizer} disabled={!isOptimizerRunning}>
                Stop Optimizer
              </Button>
            </Grid>
            <Grid item>
              <LogoutButton />
            </Grid>
          </Grid>

          {errorMessage && (
            <Box mt={4}>
              <Typography variant="h6" color="error">
                {errorMessage}
              </Typography>
            </Box>
          )}

          {/* Policies */}
          <Grid container spacing={2} rowSpacing={2} >
            <Grid item xs={12} md={6}>
              <Typography variant="h6" mb={2}>Policies</Typography>
              <PolicyTable policies={policies} handleToggle={handleTogglePolicy} />
            </Grid>
            <Grid item xl={4} marginLeft={8}>
              <PolicyPieChart impactedResources={impactedResources} />
            </Grid>

            {/* Summary Metrics Row */}

            <Typography ml={2} variant="h6">Summary Metrics</Typography>
            <Grid
              container
              spacing={1}
              margin={1}
              justifyContent="flex-start" // Align cards to the left
              alignItems="flex-start"    // Align items at the top
              wrap="wrap"                // Ensure wrapping is enabled
            >
              {filteredSummaryMetrics.map((metric, index) => (
                <Grid
                  item
                  xs={12} sm={6} md={4} lg={3} // Adjust grid breakpoints
                  key={index}
                  sx={{
                    display: 'flex',         // Ensure items are flex containers
                    justifyContent: 'center', // Center-align content in the grid cell
                  }}
                >
                  <SummaryMetricsCard metric={metric} />
                </Grid>
              ))}
            </Grid>




            {/* Render Cost Trend Chart */}
            <Grid item xl={12} md={6} padding={2}>
              <Typography variant="h6" mb={2}>Cost Trend</Typography>
              <CostTrendChart trendData={trendData} selectedSubscription={selectedSubscription} />
            </Grid>
            {/* Render Impacted Resources */}
            <Grid item xs={4} md={6}>
              <Typography variant="h6" mb={2}>Impacted Resources</Typography>
              <ImpactedResourcesTable impactedResources={impactedResources} selectedSubscription={selectedSubscription} />
            </Grid>
            {/* Render Execution Table showing status of action */}
            <Grid item xs={4} md={6}>
              <Typography variant="h6" mb={2}>Execution Data</Typography>
              <ExecutionTable executionData={executionData} selectedSubscription={selectedSubscription} />
            </Grid>
          </Grid>

          {/* Data Display Area for Optimizer Logs */}
          <Grid container spacing={2} sx={{
            mt: 6,
            display: 'flex',
            mb: 4
          }}>
            <Grid item xs={12} md={12}>
              <Typography variant="h6" mb={2}>Optimizer Logs</Typography>
              <OptimizerLogs logs={logs} />
            </Grid>
          </Grid>
        </TracingBeamContainer>
      </Container>
      <TypewriterEffectSmooth
        words={[
          { text: "Brought" },
          { text: "to" },
          { text: "you" },
          { text: "by" },
          { text: "Jamel Achahbar" },
        ]}
        variant="h6"
        speed={100}
      />
    </Box>

  );
};

// Export the App component
export default Optimizer;
