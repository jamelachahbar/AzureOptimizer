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
  Paper,
  Box,
  TextField,
  Card,
  CardContent,
  TableContainer,
  Table,
  SelectChangeEvent,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
   Switch,
   FormControlLabel,
   FormGroup
 
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Sector
} from 'recharts';
import axios from 'axios';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { Virtuoso } from 'react-virtuoso'; // Import the Virtuoso component
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faMoneyBillWave } from '@fortawesome/free-solid-svg-icons';

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
interface ProcessedData {
  [date: string]: {
    date: string;
    costs: SubscriptionCosts;
  };
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

interface SummaryMetricsCardProps {
  metric: SummaryMetric;
}

interface AnomalyData {
  date: string;
  cost: number;
  SubscriptionId: string;
}

interface DataBySubscription {
  [SubscriptionId: string]: CostData[];
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
  const handleToggle = async (policyName: string, enabled: boolean) => {
    console.log('Toggling policy:', policyName);

    // First find the policy and determine its new state
    const policy = policies.find(policy => policy.name === policyName);
    if (!policy) return; // If for some reason the policy is not found, exit early

    const newEnabledState = !policy.enabled;

    // Update the frontend state
    setPolicies((prevPolicies) =>
      prevPolicies.map((p) =>
        p.name === policyName ? { ...p, enabled: newEnabledState } : p
      )
    );

    try {
      // Send the toggle change to the server
      await axios.post('http://localhost:5000/api/toggle-policy', {
        policy_name: policyName,
        enabled: newEnabledState,
      });
    } catch (error) {
      console.error('Error updating policy:', error);
      // Optionally roll back the toggle on error
      setPolicies((prevPolicies) =>
        prevPolicies.map((p) =>
          p.name === policyName ? { ...p, enabled: !newEnabledState } : p
        )
      );
    }
};

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



  const onPieEnter = useCallback((_: any, index: number) => {
    setActiveIndex(index);
  }, []);

  // const filteredAnomalyData =
  //   selectedSubscription === 'All Subscriptions'
  //     ? anomalyData
  //     : anomalyData.filter((data) => data.SubscriptionId === selectedSubscription);
  const filteredTrendData =
    selectedSubscription === 'All Subscriptions'
      ? trendData
      : trendData.filter((data) => data.SubscriptionId === selectedSubscription);
  const filteredExecutionData =
    selectedSubscription === 'All Subscriptions'
      ? executionData
      : executionData.filter((data) => data.SubscriptionId === selectedSubscription);
  const filteredImpactedResources =
    selectedSubscription === 'All Subscriptions'
      ? impactedResources
      : impactedResources.filter((data) => data.SubscriptionId === selectedSubscription);
  // Filter metrics based on selected subscription
  const filteredSummaryMetrics =
    selectedSubscription === 'All Subscriptions'
      ? summaryMetrics
      : summaryMetrics.filter((metric) => metric.SubscriptionId === selectedSubscription);

  // Define the summaryMetrics card component
  const SummaryMetricsCard: React.FC<SummaryMetricsCardProps> = ({ metric }) => {
    console.log('Metric data:', metric);
    return (
      <Card sx={{ minWidth: 275, boxShadow: 3, '&:hover': { boxShadow: 6 } }}>
        <CardContent>
          <Typography sx={{ fontSize: 14 }} color="text.secondary" gutterBottom>
            Subscription: {metric.SubscriptionId}
          </Typography>
          <Box display="flex" alignItems="center">
            <FontAwesomeIcon icon={faMoneyBillWave} size="lg" style={{ marginRight: 8, color: '#1976d2' }} />
            <Typography variant="h5" component="div">
              ${metric.AverageDailyCost}
            </Typography>
          </Box>
          <Typography sx={{ mb: 1.5 }} color="text.secondary">
            Max Daily: ${metric.MaximumDailyCost}
          </Typography>
          <Typography sx={{ mb: 1.5 }} color="text.secondary">
            Min Daily: ${metric.MinimumDailyCost}
          </Typography>
          <Typography variant="body2">
            Total Cost: <b>${metric.TotalCost}</b>
          </Typography>
        </CardContent>
      </Card>
    );
  };

  const renderCostChart = (trendData: CostData[], selectedSubscription: string) => {
    // Initialize dataBySubscription with the appropriate type
    const dataBySubscription: DataBySubscription = {};  
    if (!trendData || trendData.length === 0) {
      return <Typography>No data available</Typography>;
    }
    if (selectedSubscription === 'All Subscriptions') {
      trendData.forEach((data) => {
        if (!dataBySubscription[data.SubscriptionId]) {
          dataBySubscription[data.SubscriptionId] = [];
        }
        dataBySubscription[data.SubscriptionId].push(data);
      });
    } else {
      dataBySubscription[selectedSubscription] = trendData.filter(
        (data) => data.SubscriptionId === selectedSubscription
      );
    
      // Ensure dataBySubscription[selectedSubscription] is always initialized
      if (!dataBySubscription[selectedSubscription]) {
        dataBySubscription[selectedSubscription] = [];
      }
    }
    
    // Determine the min and max cost for the Y-axis scale
    const costs = trendData.map((data) => data.cost);
    const minY = Math.min(...costs);
    const maxY = Math.max(...costs);
    // Prepare lines for each subscription
    const lines = Object.keys(dataBySubscription).map((subscriptionId) => (
      <Line
        key={subscriptionId}
        type="monotone"
        dataKey="cost"
        data={dataBySubscription[subscriptionId]}
        name={`Subscription ${subscriptionId}`}
        stroke={generateRandomColor()} // Ensure this function returns a consistent color for the same subscription ID
        activeDot={{ r: 8 }}
      />
    ));
    const rawData: CostData[] = trendData;
    const processedData = rawData.reduce<ProcessedData>((acc, curr) => {
      const { SubscriptionId, cost, date } = curr;
    
      if (!acc[date]) {
        acc[date] = { date, costs: {} };
      }
    
      if (!acc[date].costs[SubscriptionId]) {
        acc[date].costs[SubscriptionId] = 0; // Ensure initialization
      }
    
      acc[date].costs[SubscriptionId] += cost;
    
      return acc;
    }, {});
    const chartData = Object.values(processedData).map(entry => ({
      date: entry.date,
      ...entry.costs // Spread operator to flatten the costs into the same object
    }));
     // Ensure that chartData is not empty before rendering the chart
    if (chartData.length === 0) {
      return <Typography>No chart data available</Typography>;
    }     
    // Process the data to group costs by date
    return (
      <ResponsiveContainer width="100%" maxHeight={400}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          {Object.keys(chartData[0]).filter(key => key !== 'date').map(key => (
            <Line key={key} type="monotone" dataKey={key} stroke={generateRandomColor()} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );  
  };

  // Utility function to generate colors (could be enhanced to ensure better colors or use a set array of colors)
  function generateRandomColor() {
    const randomColor = '#' + Math.floor(Math.random() * 16777215).toString(16);
    return randomColor;
  }
  // Define a function to determine row styles based on status
  const getRowStyle = (status: string) => {
    switch (status) {
      case 'Success':
        return { backgroundColor: 'lightgreen' };
      case 'Failed':
        return { backgroundColor: 'red' };
      case 'Dry Run':
        return { backgroundColor: 'lightyellow' };
      default:
        return {};
    }
  };
  const renderExecutionTable = () => (
    <Paper style={{ height:500}}>
      <div style={{
        display: 'flex',
        position: 'relative',
        top:0,
        backgroundColor: '#f4f4f4',
        zIndex: 1,
        padding: '8px 16px',
        borderBottom: '1px solid #e0e0e0',
        marginBottom: -10,
      }}>
        <Typography style={{ flex: 1, fontWeight: 'bold' }}>Action</Typography>
        <Typography style={{ flex: 1, fontWeight: 'bold' }}>Message</Typography>
        <Typography style={{ flex: 1, fontWeight: 'bold' }}>Resource</Typography>
        <Typography style={{ flex: 1, fontWeight: 'bold' }}>Status</Typography>
        <Typography style={{ flex: 1, fontWeight: 'bold' }}>Subscription ID</Typography>
      </div>
      <Virtuoso
        data={filteredExecutionData}
        itemContent={(index, execution) => (
          <div
            style={{
              display: 'flex',
              padding: '8px 10px',
              borderBottom: '1px solid #e0e0e0',
              ...getRowStyle(execution.Status),
            }}
          >
            <Typography style={{ flex: 1 }}>{execution.Action}</Typography>
            <Typography style={{ flex: 1 }}>{execution.Message}</Typography>
            <Typography style={{ flex: 1 }}>{execution.Resource}</Typography>
            <Typography style={{ flex: 1 }}>{execution.Status}</Typography>
            <Typography style={{ flex: 1 }}>{execution.SubscriptionId}</Typography>
          </div>
        )}
        style={{ maxHeight: 500, width: '100%' }}
      />

    </Paper>
  );

  const renderImpactedResourcesTable = () => (
    <TableContainer component={Paper} style={{ maxHeight: 400 }}>
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>Resource</TableCell>
            <TableCell>Policy</TableCell>
            <TableCell>Subscription ID</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredImpactedResources.map((resource, index) => (
            <TableRow key={index}>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Resource}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.Policy}</TableCell>
              <TableCell style={{ wordBreak: 'break-word' }}>{resource.SubscriptionId}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const getImpactedResourcesByPolicy = () => {
    const policyCountMap: { [key: string]: number } = {};

    impactedResources.forEach((resource) => {
      policyCountMap[resource.Policy] = (policyCountMap[resource.Policy] || 0) + 1;
    });

    return Object.entries(policyCountMap).map(([policy, count]) => ({
      name: policy,
      value: count,
    }));
  };

  const renderPolicyPieChart = () => {
    const data = getImpactedResourcesByPolicy();

    return (
      <ResponsiveContainer 
      
      >
        <PieChart>
          <Pie
            activeIndex={activeIndex}
            activeShape={renderActiveShape}
            data={data}
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="70%"
            fill="#8884d8"
            dataKey="value"
            animationBegin={0}
            onMouseEnter={onPieEnter}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    );
  };



  const renderActiveShape = (props: any) => {
    const RADIAN = Math.PI / 180;
    const {
      cx,
      cy,
      midAngle,
      innerRadius,
      outerRadius,
      startAngle,
      endAngle,
      fill,
      payload,
      percent,
      value,
    } = props;
    const sin = Math.sin(-RADIAN * midAngle);
    const cos = Math.cos(-RADIAN * midAngle);
    //  which means the text is placed outside the pie chart
    const sx = cx + (outerRadius + 10) * cos;
    // which means the text is placed outside the pie chart
    const sy = cy + (outerRadius + 10) * sin;
    const mx = cx + (outerRadius + 30) * cos;
    const my = cy + (outerRadius + 30) * sin;
    const ex = mx + (cos >= 0 ? 1 : 0) * 22;
    const ey = my;
    const textAnchor = cos >= 5 ? 'start' : 'end';

    return (
      <g>
        <text x={cx} y={cy} dy={10} textAnchor="middle" fill={fill}>
          {payload.name}
        </text>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
        />
        <Sector
          cx={cx}
          cy={cy}
          startAngle={startAngle}
          endAngle={endAngle}
          innerRadius={outerRadius + 8}
          outerRadius={outerRadius + 10}
          fill={fill}
        />
        <path
          d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`}
          stroke={fill}
          fill="none"
        />
        <circle cx={ex} cy={ey} r={3} fill={fill} stroke="none" />
        <text
          x={ex + (cos >= 0 ? 1 : -1) * 12}
          y={ey}
          textAnchor={textAnchor}
          fill="#333"
        >{`${value}`}</text>
        <text
          x={ex + (cos >= 0 ? 1 : -1) * 10}
          y={ey}
          dy={16}
          textAnchor={textAnchor}
          fill="#999"
        >
          {`${(percent * 100).toFixed(2)}%`}
        </text>
      </g>
    );
  };
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

  return (
    <ThemeProvider theme={theme}>

      {/*  Add sidebar menu with material ui component*/}
      <Container maxWidth="xl">
       {/* add logo here and should stay at top left corner and be local to the repo and located in the public folder of my react app newacologo1.png and make it responsive */}
        {/* <img src="/newacologo1.png" alt="logo" style={{ position: 'fixed', width: 120, height: 100, top: 0, left: 0}}/> */}
      </Container>  
      <Container maxWidth="xl">
        <Typography variant="h4" sx={{ mt: 4, mb: 4, textAlign: 'center' }}>
          Team CSU Azure Infra - Cost Optimizer
        </Typography>

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
          <Grid item xl={6} marginRight={8} mb={2}
          >
            <Typography variant="h5" mb={2}>Policies</Typography>
            <TableContainer component={Paper
            } style={{ maxHeight: 400, overflow: 'auto' }
            }>
              <Table stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Policy Name</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell align="center">Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {policies.map((policy) => (
                    <TableRow
                      key={policy.name}
                      sx={{
                        // backgroundColor: policy.enabled ? '#C8E6C9' : '#CCCCCC', // Light green for enabled, light red for disabled
                      }}
                    >
                      <TableCell>{policy.name}</TableCell>
                      <TableCell>{policy.description}</TableCell>
                      <TableCell align="center">
                        <FormGroup>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={policy.enabled}
                                onChange={() => handleToggle(policy.name, policy.enabled)}
                                color="success"
                              />
                            }
                            label={policy.enabled ? 'Enabled' : 'Disabled'}
                          />
                        </FormGroup>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Grid>

          {/* Pie Chart for Impacted Resources by Policy */}
          <Grid item xl={4} marginLeft={8}
          >
            
              {renderPolicyPieChart()}
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
            {renderCostChart(filteredTrendData, selectedSubscription)}
          </Grid>

{/* Other Data Tables */}
          <Grid item xl={12} md={6}>
            <Typography variant="h5" mb={2}>Impacted Resources</Typography>
            {renderImpactedResourcesTable()}
          </Grid>
          <Grid item xl={12} md={6}>
            <Typography variant="h5" mb={2}>Execution Data</Typography>
            {renderExecutionTable()}
          </Grid>
 
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
          <Grid item xs={12} md={6}>
              <Typography variant="h5" mb={2}>Optimizer Logs</Typography>
              <Paper style={{ maxHeight: 300, overflow: 'auto' }}>
                {logs.map((log, index) => (
                  <Typography key={index} variant="body1">{log}</Typography>
                ))}
              </Paper>
          </Grid>
        </Grid>
      </Container>
    </ThemeProvider>
  );
};

export default App;
