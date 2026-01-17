import React, { useState, useMemo } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Chip,
  useTheme,
} from '@mui/material';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faServer, faHardDrive, faNetworkWired, faDatabase, faCloud } from '@fortawesome/free-solid-svg-icons';

interface ResourceData {
  Resource: string;
  Action: string;
  Status: string;
  Cost: number;
  Policy: string;
  SubscriptionId: string;
  ResourceType?: string;
}

interface TopWasteResourcesCardProps {
  impactedResources: ResourceData[];
}

type SortField = 'Resource' | 'Cost' | 'Policy';
type SortOrder = 'asc' | 'desc';

const getResourceIcon = (resourceName: string, policy: string) => {
  const lowerName = resourceName.toLowerCase();
  const lowerPolicy = policy.toLowerCase();

  if (lowerName.includes('vm') || lowerPolicy.includes('vm')) return faServer;
  if (lowerName.includes('disk') || lowerPolicy.includes('disk')) return faHardDrive;
  if (lowerName.includes('ip') || lowerPolicy.includes('ip') || lowerName.includes('nic')) return faNetworkWired;
  if (lowerName.includes('sql') || lowerName.includes('database')) return faDatabase;
  return faCloud;
};

const getResourceTypeFromPolicy = (policy: string): string => {
  const lowerPolicy = policy.toLowerCase();
  if (lowerPolicy.includes('vm')) return 'Virtual Machine';
  if (lowerPolicy.includes('disk')) return 'Disk';
  if (lowerPolicy.includes('ip')) return 'Public IP';
  if (lowerPolicy.includes('nic')) return 'Network Interface';
  if (lowerPolicy.includes('storage')) return 'Storage';
  if (lowerPolicy.includes('sql')) return 'SQL Database';
  return 'Resource';
};

const TopWasteResourcesCard: React.FC<TopWasteResourcesCardProps> = ({ impactedResources }) => {
  const theme = useTheme();
  const [sortField, setSortField] = useState<SortField>('Cost');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const sortedResources = useMemo(() => {
    const sorted = [...impactedResources].sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'Resource':
          comparison = a.Resource.localeCompare(b.Resource);
          break;
        case 'Cost':
          comparison = a.Cost - b.Cost;
          break;
        case 'Policy':
          comparison = a.Policy.localeCompare(b.Policy);
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });
    return sorted.slice(0, 10);
  }, [impactedResources, sortField, sortOrder]);

  const totalWaste = useMemo(() => {
    return impactedResources.reduce((sum, r) => sum + r.Cost, 0);
  }, [impactedResources]);

  if (impactedResources.length === 0) {
    return (
      <Card sx={{ width: '100%', boxShadow: 3, borderRadius: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Typography variant="h6" mb={2}>Top Waste Resources</Typography>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flex: 1,
              color: 'text.secondary',
            }}
          >
            <Typography variant="body2">
              Run optimizer to identify waste resources
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        width: '100%',
        height: '100%',
        boxShadow: 3,
        borderRadius: 3,
        display: 'flex',
        flexDirection: 'column',
        '&:hover': {
          boxShadow: 4,
          transition: 'box-shadow 0.3s',
        },
      }}
    >
      <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="h6">Top Waste Resources</Typography>
          <Chip
            label={`$${totalWaste.toFixed(2)} total waste`}
            color="error"
            variant="outlined"
            size="small"
          />
        </Box>

        <TableContainer component={Paper} sx={{ flex: 1, maxHeight: 300 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold' }}>Type</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>
                  <TableSortLabel
                    active={sortField === 'Resource'}
                    direction={sortField === 'Resource' ? sortOrder : 'asc'}
                    onClick={() => handleSort('Resource')}
                  >
                    Resource
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>
                  <TableSortLabel
                    active={sortField === 'Policy'}
                    direction={sortField === 'Policy' ? sortOrder : 'asc'}
                    onClick={() => handleSort('Policy')}
                  >
                    Policy
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                  <TableSortLabel
                    active={sortField === 'Cost'}
                    direction={sortField === 'Cost' ? sortOrder : 'asc'}
                    onClick={() => handleSort('Cost')}
                  >
                    Monthly Cost
                  </TableSortLabel>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedResources.map((resource, index) => (
                <TableRow
                  key={`${resource.Resource}-${index}`}
                  sx={{
                    '&:hover': {
                      backgroundColor: theme.palette.action.hover,
                    },
                  }}
                >
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <FontAwesomeIcon
                        icon={getResourceIcon(resource.Resource, resource.Policy)}
                        style={{ color: theme.palette.primary.main }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {getResourceTypeFromPolicy(resource.Policy)}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{
                        maxWidth: 200,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={resource.Resource}
                    >
                      {resource.Resource}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={resource.Policy} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      sx={{ color: '#f44336', fontWeight: 'bold' }}
                    >
                      ${resource.Cost.toFixed(2)}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {impactedResources.length > 10 && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mt: 1, display: 'block', textAlign: 'center' }}
          >
            Showing top 10 of {impactedResources.length} waste resources
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default TopWasteResourcesCard;
