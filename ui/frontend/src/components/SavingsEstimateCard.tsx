import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Collapse,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Tooltip,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPiggyBank, faChartLine, faServer, faHardDrive, faNetworkWired } from '@fortawesome/free-solid-svg-icons';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import RefreshIcon from '@mui/icons-material/Refresh';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import axios from 'axios';

interface ResourceEstimate {
  name: string;
  resource_id?: string;
  resource_group?: string;
  resource_type?: string;
  size?: string;
  size_gb?: number;
  sku?: string;
  ip_address?: string;
  allocation_method?: string;
  action?: string;
  status?: string;
  subscription_id?: string;
  estimated_monthly_cost: number;
  actual_cost?: number;  // Cost from Azure Cost Management (if available)
  is_estimate?: boolean; // True if cost is estimated, false if from Azure
}

interface PolicyEstimate {
  policy_name: string;
  resource_type: string;
  matching_resources: number;
  estimated_savings: number;
  resources: ResourceEstimate[];
  error?: string;
}

interface SavingsEstimate {
  subscription_id: string;
  estimated_monthly_savings: number;
  currency: string;
  breakdown: PolicyEstimate[];
  resources_analyzed: number;
  resources_impacted: number;
}

interface SavingsEstimateCardProps {
  subscriptionId?: string;
}

const getResourceIcon = (resourceType: string) => {
  switch (resourceType) {
    case 'azure.vm':
      return faServer;
    case 'azure.disk':
      return faHardDrive;
    case 'azure.publicip':
      return faNetworkWired;
    default:
      return faChartLine;
  }
};

const getResourceTypeLabel = (resourceType: string) => {
  switch (resourceType) {
    case 'azure.vm':
      return 'Virtual Machines';
    case 'azure.disk':
      return 'Disks';
    case 'azure.publicip':
      return 'Public IPs';
    case 'azure.storage':
      return 'Storage';
    case 'azure.sql':
      return 'SQL Databases';
    case 'azure.nic':
      return 'Network Interfaces';
    default:
      return resourceType;
  }
};

// Generate helpful tooltip explaining where the estimate comes from
const getEstimateTooltip = (resource: ResourceEstimate): string => {
  const resourceType = resource.resource_type?.toLowerCase() || '';
  const action = resource.action?.toLowerCase() || '';
  const actualCost = resource.actual_cost || 0;
  
  let explanation = '';
  
  if (actualCost === 0) {
    explanation = `Azure Cost Management returned $0.00 for this resource. `;
  }
  
  // Explain the estimate based on resource type
  if (resourceType.includes('nic') || resourceType.includes('network interface')) {
    explanation += `Network Interfaces don't have direct Azure charges. Estimate of $0.50/month is used to track orphaned resources.`;
  } else if (resourceType.includes('disk')) {
    explanation += `Estimated based on average unattached disk cost (~128GB Standard HDD at ~$0.05/GB = $6.40/month).`;
  } else if (resourceType.includes('public') || resourceType.includes('ip')) {
    explanation += `Based on Azure Static Public IP pricing (~$3.65/month).`;
  } else if (resourceType.includes('vm')) {
    if (action.includes('stop')) {
      explanation += `Stopping VM saves compute costs. Estimate based on average B-series VM (~$50/month).`;
    } else {
      explanation += `Based on average VM costs including compute and storage (~$75/month).`;
    }
  } else if (resourceType.includes('storage')) {
    explanation += `Based on typical storage account costs with SKU downgrade savings (~$15/month).`;
  } else if (resourceType.includes('sql') || resourceType.includes('database')) {
    explanation += `Based on average SQL Database DTU scaling savings (~$50/month).`;
  } else if (resourceType.includes('gateway')) {
    explanation += `Application Gateway costs vary by tier. Estimate based on Basic tier (~$100/month).`;
  } else {
    explanation += `Default estimate of $5/month used for unknown resource types.`;
  }
  
  return explanation;
};

const SavingsEstimateCard: React.FC<SavingsEstimateCardProps> = ({ subscriptionId }) => {
  const [estimate, setEstimate] = useState<SavingsEstimate | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [expandedPolicies, setExpandedPolicies] = useState<Set<string>>(new Set());

  const fetchEstimate = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = subscriptionId ? { subscription_id: subscriptionId } : {};
      const { data } = await axios.get<SavingsEstimate>('http://localhost:5000/api/estimate-savings', { params });
      setEstimate(data);
    } catch (err: any) {
      console.error('Error fetching savings estimate:', err);
      setError(err.response?.data?.error || 'Failed to fetch savings estimate');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEstimate();
  }, [subscriptionId]);

  const togglePolicyExpansion = (policyName: string) => {
    setExpandedPolicies(prev => {
      const newSet = new Set(prev);
      if (newSet.has(policyName)) {
        newSet.delete(policyName);
      } else {
        newSet.add(policyName);
      }
      return newSet;
    });
  };

  if (loading) {
    return (
      <Card sx={{ width: '100%', height: '100%', boxShadow: 3, borderRadius: 3, display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <CircularProgress size={40} />
          <Typography variant="body1" sx={{ ml: 2 }}>
            Analyzing resources...
          </Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ width: '100%', height: '100%', boxShadow: 3, borderRadius: 3, display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flex: 1 }}>
          <Alert severity="error" action={
            <IconButton size="small" onClick={fetchEstimate}>
              <RefreshIcon />
            </IconButton>
          }>
            {error}
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!estimate) {
    return null;
  }

  const hasSavings = estimate.estimated_monthly_savings > 0;

  return (
    <Card
      sx={{
        width: '100%',
        height: '100%',
        boxShadow: 3,
        borderRadius: 3,
        border: hasSavings ? '2px solid #4caf50' : undefined,
        display: 'flex',
        flexDirection: 'column',
        '&:hover': {
          boxShadow: 4,
          transition: 'box-shadow 0.3s',
        },
      }}
    >
      <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header */}
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" sx={{ minWidth: 0 }}>
            <FontAwesomeIcon
              icon={faPiggyBank}
              style={{ marginRight: 12, color: hasSavings ? '#4caf50' : '#9e9e9e', fontSize: 24, flexShrink: 0 }}
            />
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h6" component="div" noWrap>
                Estimated Monthly Savings
              </Typography>
              <Typography variant="body2" color="text.secondary" noWrap>
                {estimate.resources_analyzed} resources analyzed
              </Typography>
            </Box>
          </Box>
          <Box display="flex" alignItems="center" gap={0.5} flexShrink={0}>
            <Tooltip title="Refresh estimate">
              <IconButton onClick={fetchEstimate} size="small">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <IconButton onClick={() => setExpanded(!expanded)} size="small">
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        </Box>

        {/* Main Savings Amount */}
        <Box
          sx={{
            backgroundColor: hasSavings ? '#e8f5e9' : '#f5f5f5',
            borderRadius: 2,
            p: 2,
            mb: 2,
            textAlign: 'center',
          }}
        >
          <Typography
            variant="h3"
            component="div"
            sx={{ color: hasSavings ? '#2e7d32' : '#757575', fontWeight: 'bold' }}
          >
            ${estimate.estimated_monthly_savings.toFixed(2)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            per month • {estimate.resources_impacted} resources impacted
          </Typography>
        </Box>

        {/* Breakdown Summary */}
        {estimate.breakdown.length > 0 && (
          <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
            {estimate.breakdown.filter(p => p.matching_resources > 0).map((policy) => (
              <Chip
                key={policy.policy_name}
                icon={<FontAwesomeIcon icon={getResourceIcon(policy.resource_type)} />}
                label={`${policy.policy_name}: $${policy.estimated_savings.toFixed(2)}`}
                color="success"
                variant="outlined"
                size="small"
              />
            ))}
          </Box>
        )}

        {/* Expanded Details */}
        <Collapse in={expanded}>
          {estimate.breakdown.length === 0 ? (
            <Alert severity="info">
              No enabled policies found. Enable policies to see potential savings.
            </Alert>
          ) : (
            <Box mt={2}>
              {estimate.breakdown.map((policy) => (
                <Card key={policy.policy_name} variant="outlined" sx={{ mb: 2 }}>
                  <CardContent sx={{ pb: 1 }}>
                    <Box
                      display="flex"
                      alignItems="center"
                      justifyContent="space-between"
                      onClick={() => togglePolicyExpansion(policy.policy_name)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <Box display="flex" alignItems="center">
                        <FontAwesomeIcon
                          icon={getResourceIcon(policy.resource_type)}
                          style={{ marginRight: 8, color: '#1976d2' }}
                        />
                        <Box>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {policy.policy_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {getResourceTypeLabel(policy.resource_type)} • {policy.matching_resources} resources
                          </Typography>
                        </Box>
                      </Box>
                      <Box display="flex" alignItems="center">
                        <Typography
                          variant="h6"
                          sx={{ color: policy.estimated_savings > 0 ? '#2e7d32' : '#757575', mr: 1 }}
                        >
                          ${policy.estimated_savings.toFixed(2)}
                        </Typography>
                        {policy.resources.length > 0 && (
                          expandedPolicies.has(policy.policy_name) ? <ExpandLessIcon /> : <ExpandMoreIcon />
                        )}
                      </Box>
                    </Box>

                    {policy.error && (
                      <Alert severity="warning" sx={{ mt: 1 }}>
                        {policy.error}
                      </Alert>
                    )}

                    <Collapse in={expandedPolicies.has(policy.policy_name)}>
                      {policy.resources.length > 0 && (
                        <Box sx={{ mt: 2 }}>
                          {policy.resources.map((resource, idx) => (
                            <Box
                              key={idx}
                              sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                py: 1,
                                px: 1.5,
                                borderBottom: '1px solid',
                                borderColor: 'divider',
                                '&:last-child': { borderBottom: 'none' },
                              }}
                            >
                              <Box sx={{ minWidth: 0, flex: 1 }}>
                                <Typography variant="body2" fontWeight="medium" noWrap title={resource.name}>
                                  {resource.name}
                                </Typography>
                                <Box display="flex" gap={0.5} flexWrap="wrap">
                                  {resource.action && (
                                    <Chip
                                      label={resource.action}
                                      size="small"
                                      color={resource.action.toLowerCase().includes('delete') ? 'error' : 'primary'}
                                      variant="outlined"
                                      sx={{ height: 20, fontSize: '0.7rem' }}
                                    />
                                  )}
                                  {resource.status && (
                                    <Chip
                                      label={resource.status}
                                      size="small"
                                      color={resource.status === 'Success' ? 'success' : resource.status === 'Pending' ? 'warning' : 'default'}
                                      sx={{ height: 20, fontSize: '0.7rem' }}
                                    />
                                  )}
                                </Box>
                              </Box>
                              <Tooltip
                                title={
                                  resource.is_estimate
                                    ? getEstimateTooltip(resource)
                                    : `Actual: $${resource.actual_cost?.toFixed(2)}`
                                }
                                arrow
                              >
                                <Typography
                                  variant="body2"
                                  color="success.main"
                                  fontWeight="bold"
                                  sx={{ ml: 2, flexShrink: 0 }}
                                >
                                  ${resource.estimated_monthly_cost.toFixed(2)}
                                  {resource.is_estimate && (
                                    <InfoOutlinedIcon sx={{ fontSize: 12, ml: 0.5, verticalAlign: 'middle' }} />
                                  )}
                                </Typography>
                              </Tooltip>
                            </Box>
                          ))}
                        </Box>
                      )}
                    </Collapse>
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default SavingsEstimateCard;
