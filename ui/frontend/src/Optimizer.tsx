import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import {
  Container, Grid, CircularProgress, Typography, FormControl, InputLabel,
  Select, MenuItem, Box, SelectChangeEvent, Button,
} from '@mui/material';
import axios from 'axios';
import { useTheme } from '@mui/material/styles';
import { useIsAuthenticated } from '@azure/msal-react';
import { AuthProvider, useAuth } from './providers/AuthProvider';
import TracingBeamContainer from './components/TracingBeamContainer';
import { Highlight } from './components/HeroHighlight';
import TypewriterEffectSmooth from './components/TypewriterEffectSmooth';
import SummaryMetricsCard from './components/SummaryMetricsCard';
import CostTrendChart from './components/CostTrendChart';
import ExecutionTable from './components/ExecutionTable';
import ImpactedResourcesTable from './components/ImpactedResourcesTable';
import PolicyTable from './components/PolicyTable';
import PolicyPieChart from './components/PolicyPieChart';
import OptimizerLogs from './components/OptimizerLogs';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import PolicyEditor from './components/PolicyEditor';
import { LandingScreen } from './components/LandingScreen';
import LoginButton from './components/LoginButton';
import LogoutButton from './components/LogoutButton';
import AnomaliesDisplay from "./components/AnomaliesDisplay";

export const ColorModeContext = createContext({ toggleColorMode: () => { } });

interface Policy { name: string; description: string; enabled: boolean; }
interface CostData { date: string; cost: number; SubscriptionId: string; }
interface ExecutionData { Action: string; Cost: number; Message: string; Resource: string; Status: string; SubscriptionId: string; }
interface ResourceData { Resource: string; Action: string; Status: string; Cost: number; Policy: string; SubscriptionId: string; }
interface SummaryMetric { SubscriptionId: string; AverageDailyCost: number; MaximumDailyCost: number; MinimumDailyCost: number; TotalCost: number; }
interface AnomalyData { date: string; cost: number; SubscriptionId: string; }

const Optimizer: React.FC = () => {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const isAuthenticated = useIsAuthenticated();
  const [summaryMetrics, setSummaryMetrics] = useState<SummaryMetric[]>([{
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
  const [executionData, setExecutionData] = useState<ExecutionData[]>([{
    Action: 'Stop',
    Cost: 10,
    Message: 'VM stopped successfully.',
    Resource: 'mock-vm-1',
    Status: 'Success',
    SubscriptionId: 'mock-subscription-1',
  },]);
  const [impactedResources, setImpactedResources] = useState<ResourceData[]>([{
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
  },]);
  const [trendData, setTrendData] = useState<CostData[]>([{
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
  },]);
  const [anomalyData, setAnomalyData] = useState<any[]>([]); // State for storing anomalies
  const [loadingAnomalies, setLoadingAnomalies] = useState(false); // Loading state for anomalies
  const [anomaliesError, setAnomaliesError] = useState<string | null>(null); // Error state for anomalies
  const [isOptimizerRunning, setIsOptimizerRunning] = useState(false);
  const [mode, setMode] = useState('dry-run');
  const [logs, setLogs] = useState<string[]>([]);
  const [selectedSubscription, setSelectedSubscription] = useState<string>('All Subscriptions');
  const [timeout, setTimeout] = useState<number>(60);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const colorMode = useContext(ColorModeContext);
  const theme = useTheme();
  const { isAdmin } = useAuth();

  useEffect(() => {
    const fetchPolicies = async () => {
      try {
        const { data } = await axios.get('http://localhost:5000/api/policies');
        setPolicies(data.policies);
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
  const { tenantId } = useAuth();

  const runOptimizer = async () => {
    if (!tenantId) {
      console.error("Tenant ID is missing.");
      setLogs((prevLogs) => [...prevLogs, "Error: Tenant ID is missing."]);
      return;
    }
    if (mode === "apply" && !isAdmin) {
      alert("You do not have sufficient permissions to use Apply mode.");
      return;
    }
    setIsOptimizerRunning(true);
    setLogs([]);
    fetchLogStream();
    setAnomalyData([]);
    setAnomaliesError(null);
    setLoadingAnomalies(true);
    try {
      const { data } = await axios.post('http://127.0.0.1:5000/api/run', {
        mode: mode,
        all_subscriptions: true,
        tenantId: tenantId,

      });
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
    const { data: summaryData } = await axios.get('http://127.0.0.1:5000/api/summary-metrics');
    setSummaryMetrics(summaryData);
  } catch (error) {
    console.error('Error fetching summary metrics:', error);
    setErrorMessage('Error fetching data from server. Please make sure the server is running.');
  }

  try {
    const { data: executionData } = await axios.get('http://127.0.0.1:5000/api/execution-data');
    setExecutionData(executionData);
  } catch (error) {
    console.error('Error fetching execution data:', error);
  }

  try {
    const { data: impactedResourcesData } = await axios.get('http://127.0.0.1:5000/api/impacted-resources');
    setImpactedResources(impactedResourcesData);
  } catch (error) {
    console.error('Error fetching impacted resources:', error);
  }

  try {
    const { data: anomalies } = await axios.get("http://127.0.0.1:5000/api/anomalies");
    console.log("Raw Anomalies:", anomalies);

    // Map anomalies to match the expected structure
    const mappedAnomalies = anomalies.map((anomaly: { Date: any; Cost: any; SubscriptionId: any }) => ({
      date: anomaly.Date,
      cost: anomaly.Cost,
      SubscriptionId: anomaly.SubscriptionId
    }));

    console.log("Mapped Anomalies:", mappedAnomalies);
    setAnomalyData(mappedAnomalies);
  } catch (error) {
    console.error("Error fetching anomalies:", error);
    setAnomaliesError("Failed to load anomalies.");
  } finally {
    setLoadingAnomalies(false);
  }
  try {
    const { data: trendData } = await axios.get('http://127.0.0.1:5000/api/trend-data');
    if (Array.isArray(trendData)) {
      setTrendData(trendData);
    } else {
      console.error('Unexpected trend data format:', trendData);
      setTrendData([]); // Reset to an empty state
    }
  } catch (error) {
    console.error('Error fetching trend data:', error);
    setTrendData([]); // Reset to an empty state
  }


}, [selectedSubscription]);

  useEffect(() => {
    let interval: NodeJS.Timeout | undefined;
    const checkCompletion = async () => {
      try {
        const { data } = await axios.get('http://127.0.0.1:5000/api/status');
        if (data.status === 'Completed') {
          setIsOptimizerRunning(false); // Stop polling
          clearInterval(interval); // Clear the interval
        }
      } catch (error) {
        console.error('Error checking optimizer status:', error);
      }
    };
    if (isOptimizerRunning) {
      interval = setInterval(() => {
        fetchData();
        checkCompletion();
      }, 5000);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [isOptimizerRunning, fetchData]);

  const handleSubscriptionChange = (event: SelectChangeEvent<string>) => setSelectedSubscription(event.target.value as string);

  const handleTogglePolicy = async (policyName: string, enabled: boolean) => {
    try {
      await axios.post('http://localhost:5000/api/toggle-policy', { policy_name: policyName, enabled: !enabled });
      setPolicies(policies.map(policy => policy.name === policyName ? { ...policy, enabled: !enabled } : policy));
    } catch (error) {
      console.error('Error updating policy:', error);
    }
  };

  const filteredSummaryMetrics = selectedSubscription === 'All Subscriptions' ? summaryMetrics : summaryMetrics.filter((metric) => metric.SubscriptionId === selectedSubscription);

  if (!isAuthenticated) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <LoginButton />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <Container sx={{ maxWidth: "1200px", margin: '0 auto', display: 'flex', position: 'center', maxHeight: '80%', flex: 1, padding: theme.spacing(2), boxShadow: 'rgba(9, 30, 66, 0.25) 0px 4px 8px -2px, rgba(9, 30, 66, 0.08) 0px 0px 0px 1px', borderRadius: 2, zIndex: 2, backgroundColor: theme.palette.mode === 'light' ? 'rgba(255, 255, 255, 0.9)' : '#1A1A1A', backdropFilter: 'blur(10px)' }}>
        <TracingBeamContainer>
          <Typography variant="h4" sx={{ mb: 4, textAlign: 'center' }}>Azure Optimizer Tool</Typography>
          <Typography variant="h6" sx={{ mb: 4, textAlign: 'center' }}><Highlight>Optimize</Highlight>your<Highlight>Azure Infrastructure costs</Highlight></Typography>

          <Grid container spacing={2} display="flex" alignContent="center" alignItems="center" justifyContent="center" marginBottom={2}>
            <Grid item>
              <FormControl variant="outlined" sx={{ minWidth: 120, fontSize: '0.8rem' }}>
                <InputLabel sx={{ fontSize: '0.8rem' }}>Subscription</InputLabel>
                <Select value={selectedSubscription} onChange={handleSubscriptionChange} label="Subscription" sx={{ fontSize: '0.8rem' }}>
                  <MenuItem value="All Subscriptions" sx={{ fontSize: '0.8rem' }}>All Subscriptions</MenuItem>
                  {summaryMetrics.map((metric, index) => <MenuItem key={index} value={metric.SubscriptionId}>{metric.SubscriptionId}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            <Grid item>
              <FormControl variant="outlined" sx={{ minWidth: 120 }}>
                <InputLabel>Mode</InputLabel>
                <Select value={mode} onChange={(e) => setMode(e.target.value as string)} label="Mode" sx={{ fontSize: '0.8rem' }}>
                  <MenuItem value="dry-run" sx={{ fontSize: '0.8rem' }}>Dry Run</MenuItem>
                  <MenuItem value="apply" sx={{ fontSize: '0.8rem' }}>Apply</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item>
              <Button variant="contained" color="primary" onClick={runOptimizer} disabled={isOptimizerRunning}>Run Optimizer</Button>
              {isOptimizerRunning && <CircularProgress size={24} sx={{ ml: 1 }} />}
            </Grid>
            <Grid item>
              <Button variant="contained" color="secondary" onClick={stopOptimizer} disabled={!isOptimizerRunning}>Stop Optimizer</Button>
            </Grid>
            <Grid item>
              <LogoutButton />
            </Grid>
          </Grid>

          {errorMessage && <Box mt={4}><Typography variant="h6" color="error">{errorMessage}</Typography></Box>}

          <Grid container spacing={2} rowSpacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" mb={2}>Policies</Typography>
              <PolicyTable policies={policies} handleToggle={handleTogglePolicy} />
            </Grid>
            <Grid item xl={4} marginLeft={8}>
              <PolicyPieChart impactedResources={impactedResources} />
            </Grid>

            <Typography ml={2} variant="h6">Summary Metrics</Typography>
            <Grid container spacing={1} margin={1} justifyContent="flex-start" alignItems="flex-start" wrap="wrap">
              {filteredSummaryMetrics.map((metric, index) => (
                <Grid item xs={12} sm={6} md={4} lg={3} key={index} sx={{ display: 'flex', justifyContent: 'center' }}>
                  <SummaryMetricsCard metric={metric} />
                </Grid>
              ))}
            </Grid>

            <Grid item xl={12} md={12} xs={12} padding={2}>
              <Typography variant="h6" mb={2}>Cost Trend</Typography>
              <CostTrendChart trendData={trendData} selectedSubscription={selectedSubscription} />
            </Grid>

            <Grid item xl={12} md={12} xs={12}>
              <Typography variant="h6" mb={2}>Impacted Resources</Typography>
              <ImpactedResourcesTable impactedResources={impactedResources} selectedSubscription={selectedSubscription} />
            </Grid>

            <Grid item xl={12} md={12} xs={12}>
              <Typography variant="h6" mb={2}>Execution Data</Typography>
              <ExecutionTable executionData={executionData} selectedSubscription={selectedSubscription} />
            </Grid>
          </Grid>
          {/* New Anomalies Section */}
          <Grid item xs={4} md={6}>
            <Typography variant="h6" mb={2}>Detected Anomalies</Typography>
            <AnomaliesDisplay
              anomalies={anomalyData}
              loading={loadingAnomalies}
              error={anomaliesError}
            />
          </Grid>
          <Grid container spacing={2} sx={{ mt: 6, display: 'flex', mb: 4 }}>
            <Grid item xs={12} md={12}>
              <Typography variant="h6" mb={2}>Optimizer Logs</Typography>
              <OptimizerLogs logs={logs} />
            </Grid>
          </Grid>
        </TracingBeamContainer>
      </Container>
      <TypewriterEffectSmooth words={[{ text: "Brought" }, { text: "to" }, { text: "you" }, { text: "by" }, { text: "Jamel Achahbar" }]} variant="h6" speed={100} />
    </Box>
  );
};
export default Optimizer;



function setError(arg0: string) {
  throw new Error('Function not implemented.');
}

function fetchData(): void {
  throw new Error('Function not implemented.');
}

function setPolicies(arg0: any) {
  throw new Error('Function not implemented.');
}

