import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box,
  Button,
  Typography,
  TextField,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Collapse,
  Paper,
  useTheme,
  CircularProgress,
  FormControlLabel,
  Switch,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Divider,
  Tooltip,
  FormHelperText,
} from '@mui/material';
import { Delete, Edit, Add, Refresh, CheckCircle, Error as ErrorIcon } from '@mui/icons-material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

// API Base URL - must match backend
const API_BASE_URL = 'http://localhost:5000';

// Schema definitions with resource-specific options
// Each resource type has specific valid actions and filters
// Based on backend optimizer.py and app.py validation

interface ResourceConfig {
  value: string;
  label: string;
  description: string;
  actions: string[];
  filters: string[];
}

// Resource-specific configurations - MUST match backend optimizer.py and policies.yaml
const RESOURCE_CONFIGS: ResourceConfig[] = [
  {
    value: 'azure.vm',
    label: 'Virtual Machine',
    description: 'Stop unused VMs or downgrade disks of stopped VMs',
    actions: ['stop', 'downgrade_disks', 'log'],
    filters: ['last_used', 'tag', 'stopped'],
  },
  {
    value: 'azure.disk',
    label: 'Disk',
    description: 'Delete orphaned/unattached managed disks',
    actions: ['delete', 'log'],
    filters: ['unattached', 'tag'],
  },
  {
    value: 'azure.resourcegroup',
    label: 'Resource Group',
    description: 'Delete entire resource groups matching tags (e.g., dev environments)',
    actions: ['delete', 'log'],
    filters: ['tag'],
  },
  {
    value: 'azure.storage',
    label: 'Storage Account',
    description: 'Downgrade storage redundancy (e.g., GRS to LRS)',
    actions: ['update_sku', 'log'],
    filters: ['sku', 'tag'],
  },
  {
    value: 'azure.sql',
    label: 'SQL Database',
    description: 'Scale SQL DTUs during off-peak hours',
    actions: ['scale_dtu', 'log'],
    filters: ['tag'],
  },
  {
    value: 'azure.publicip',
    label: 'Public IP',
    description: 'Delete orphaned public IP addresses not attached to any resource',
    actions: ['delete', 'log'],
    filters: ['unattached', 'tag'],
  },
  {
    value: 'azure.applicationgateway',
    label: 'Application Gateway',
    description: 'Delete app gateways with empty backend pools',
    actions: ['delete', 'log'],
    filters: ['tag'],
  },
  {
    value: 'azure.nic',
    label: 'Network Interface',
    description: 'Delete orphaned NICs not attached to any VM',
    actions: ['delete', 'log'],
    filters: ['unattached', 'tag'],
  },
];

// All possible actions with labels and descriptions - from backend optimizer.py apply_actions()
interface ActionConfig {
  label: string;
  description: string;
  requiresSku?: boolean;
  requiresTiers?: boolean;
}

const ALL_ACTIONS: Record<string, ActionConfig> = {
  stop: {
    label: 'Stop VM',
    description: 'Deallocate the VM to stop billing for compute (storage still billed)',
  },
  delete: {
    label: 'Delete Resource',
    description: 'Permanently delete the resource (cannot be undone)',
  },
  update_sku: {
    label: 'Update Storage SKU',
    description: 'Change storage redundancy (e.g., GRS → LRS to reduce costs)',
    requiresSku: true,
  },
  scale_dtu: {
    label: 'Scale SQL DTU',
    description: 'Adjust SQL database DTU capacity based on tier configuration',
    requiresTiers: true,
  },
  log: {
    label: 'Log Only (Dry Run)',
    description: 'Only log what would happen, no changes applied',
  },
  downgrade_disks: {
    label: 'Downgrade VM Disks',
    description: 'Downgrade all managed disks attached to this VM to Standard HDD',
  },
};

// All possible filters with labels, descriptions and requirements - from backend optimizer.py evaluate_filters()
interface FilterConfig {
  label: string;
  description: string;
  requiresDays?: boolean;
  requiresThreshold?: boolean;
  requiresKey?: boolean;
  requiresValues?: boolean;
}

const ALL_FILTERS: Record<string, FilterConfig> = {
  last_used: {
    label: 'Last Used (CPU)',
    description: 'Match VMs with average CPU below threshold over X days',
    requiresDays: true,
    requiresThreshold: true,
  },
  unattached: {
    label: 'Unattached/Orphaned',
    description: 'Match resources not attached to any parent resource',
  },
  tag: {
    label: 'Tag Match',
    description: 'Match resources with a specific tag key and value',
    requiresKey: true,
  },
  sku: {
    label: 'SKU Match',
    description: 'Match resources with specific SKU names',
    requiresValues: true,
  },
  stopped: {
    label: 'VM Deallocated',
    description: 'Match VMs that are stopped (deallocated state)',
  },
};

// Helper to get valid actions for a resource type
const getActionsForResource = (resourceType: string): { value: string; label: string; description: string }[] => {
  const config = RESOURCE_CONFIGS.find((r) => r.value === resourceType);
  if (!config) return [{ value: 'log', label: 'Log Only', description: 'Only log what would happen' }];
  return config.actions.map((a) => ({
    value: a,
    label: ALL_ACTIONS[a]?.label || a,
    description: ALL_ACTIONS[a]?.description || '',
  }));
};

// Helper to get valid filters for a resource type
const getFiltersForResource = (resourceType: string): { value: string; label: string; description: string; requiresDays?: boolean; requiresThreshold?: boolean; requiresKey?: boolean; requiresValues?: boolean }[] => {
  const config = RESOURCE_CONFIGS.find((r) => r.value === resourceType);
  if (!config) return [];
  return config.filters.map((f) => ({ value: f, ...ALL_FILTERS[f] }));
};

interface PolicyFilter {
  type: string;
  days?: number;
  threshold?: number;
  key?: string;
  value?: string;
  values?: string[];
}

interface PolicyAction {
  type: string;
  sku?: string;
  tiers?: Array<{
    name: string;
    min_dtu: number;
    max_dtu: number;
    off_peak_dtu: number;
    peak_dtu: number;
  }>;
  tiersRaw?: string;
}

interface Policy {
  name: string;
  description?: string;
  resource: string;
  enabled: boolean;
  filters: PolicyFilter[];
  actions: PolicyAction[];
}

interface ValidationErrors {
  [key: string]: string;
}

interface PolicyEditorProps {
  policies: any[];
  setPolicies: React.Dispatch<React.SetStateAction<any[]>>;
  isLoading: boolean;
}

const PolicyEditor: React.FC<PolicyEditorProps> = ({ policies, setPolicies, isLoading }) => {
  const theme = useTheme();
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [newPolicy, setNewPolicy] = useState<Partial<Policy>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [open, setOpen] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [isEditorExpanded, setIsEditorExpanded] = useState<boolean>(true);

  // Fetch policies from backend
  const fetchPolicies = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/policies`);
      setPolicies(response.data.policies || []);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error fetching policies');
      console.error(err);
    }
  };

  useEffect(() => {
    if (policies.length === 0 && !isLoading) {
      fetchPolicies();
    }
  }, [policies, isLoading]);

  const handleEdit = (policy: any) => {
    setSelectedPolicy(policy);
    setNewPolicy({ ...policy });
    setIsEditing(true);
    setValidationErrors({});
    setError(null);
    setSuccess(null);
    setOpen(true);
  };

  const handleDelete = async (policyName: string) => {
    if (!window.confirm(`Are you sure you want to delete policy "${policyName}"?`)) {
      return;
    }
    try {
      await axios.delete(`${API_BASE_URL}/api/policies/policyeditor/${policyName}`);
      setSuccess(`Policy "${policyName}" deleted successfully`);
      setError(null);
      fetchPolicies();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error deleting policy');
      console.error(err);
    }
  };

  // Local validation before API call
  const validateLocally = (): boolean => {
    const errors: ValidationErrors = {};
    
    if (!newPolicy.name?.trim()) {
      errors.name = 'Policy name is required';
    } else if (!/^[a-zA-Z0-9-_]+$/.test(newPolicy.name)) {
      errors.name = 'Policy name can only contain letters, numbers, hyphens, and underscores';
    }
    
    if (!newPolicy.resource) {
      errors.resource = 'Resource type is required';
    } else if (!isEditing) {
      // Check for duplicate resource type when creating new policy
      const existingPolicyWithResource = policies.find(
        (p: any) => p.resource === newPolicy.resource
      );
      if (existingPolicyWithResource) {
        errors.resource = `A policy for "${RESOURCE_CONFIGS.find(r => r.value === newPolicy.resource)?.label || newPolicy.resource}" already exists: "${existingPolicyWithResource.name}". Edit the existing policy instead.`;
      }
    }
    
    if (!newPolicy.actions || newPolicy.actions.length === 0) {
      errors.actions = 'At least one action is required';
    } else if (newPolicy.resource) {
      // Validate actions are valid for the selected resource
      const validActionsForResource = getActionsForResource(newPolicy.resource).map(a => a.value);
      newPolicy.actions.forEach((action, i) => {
        if (!validActionsForResource.includes(action.type)) {
          errors[`actions_${i}`] = `"${ALL_ACTIONS[action.type] || action.type}" is not valid for this resource type`;
        }
      });
    }
    
    // Validate filters
    if (newPolicy.resource) {
      const validFiltersForResource = getFiltersForResource(newPolicy.resource).map(f => f.value);
      newPolicy.filters?.forEach((filter, i) => {
        if (!validFiltersForResource.includes(filter.type)) {
          errors[`filters_${i}`] = `"${ALL_FILTERS[filter.type]?.label || filter.type}" is not valid for this resource type`;
        }
        if (filter.type === 'last_used' && (!filter.days || filter.days <= 0)) {
          errors[`filters_${i}_days`] = 'Days must be a positive number';
        }
        if (filter.type === 'tag' && !filter.key?.trim()) {
          errors[`filters_${i}_key`] = 'Tag key is required';
        }
        if (filter.type === 'sku' && (!filter.values || !Array.isArray(filter.values) || filter.values.length === 0)) {
          errors[`filters_${i}_values`] = 'SKU values are required (at least one)';
        }
      });

      // Validate action-specific requirements
      newPolicy.actions?.forEach((action, i) => {
        if (action.type === 'update_sku' && !action.sku?.trim()) {
          errors[`actions_${i}_sku`] = 'Target SKU is required';
        }
        if (action.type === 'scale_dtu' && (!action.tiers || !Array.isArray(action.tiers) || action.tiers.length === 0)) {
          errors[`actions_${i}_tiers`] = 'Tier configuration is required';
        }
      });
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Validate against backend schema
  const validateWithBackend = async (): Promise<boolean> => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/policies/validate`, newPolicy);
      if (response.data.valid) {
        return true;
      }
      return false;
    } catch (err: any) {
      const errors = err.response?.data?.errors || [];
      const errorMap: ValidationErrors = {};
      errors.forEach((e: { field: string; message: string }) => {
        errorMap[e.field] = e.message;
      });
      setValidationErrors(prev => ({ ...prev, ...errorMap }));
      setError('Validation failed. Please fix the errors below.');
      return false;
    }
  };

  const handleSave = async () => {
    // Local validation first
    if (!validateLocally()) {
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccess(null);

    // Prepare policy with defaults
    const policyToSave: Policy = {
      name: newPolicy.name!,
      description: newPolicy.description || '',
      resource: newPolicy.resource!,
      enabled: newPolicy.enabled ?? true,
      filters: newPolicy.filters || [],
      actions: newPolicy.actions || [{ type: 'log' }],
    };

    // Validate against backend
    const isValid = await validateWithBackend();
    if (!isValid) {
      setIsSaving(false);
      return;
    }

    try {
      if (isEditing && selectedPolicy) {
        await axios.put(
          `${API_BASE_URL}/api/policies/policyeditor/${selectedPolicy.name}`,
          policyToSave
        );
        setSuccess(`Policy "${policyToSave.name}" updated successfully`);
      } else {
        // Check if name already exists
        if (policies.some((p: any) => p.name === policyToSave.name)) {
          setValidationErrors({ name: 'A policy with this name already exists' });
          setIsSaving(false);
          return;
        }
        await axios.post(
          `${API_BASE_URL}/api/policies/policyeditor/${policyToSave.name}`,
          policyToSave
        );
        setSuccess(`Policy "${policyToSave.name}" created successfully`);
      }
      
      setIsEditing(false);
      setSelectedPolicy(null);
      setNewPolicy({});
      setOpen(false);
      fetchPolicies();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error saving policy');
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };
  
  

  const handleFieldChange = (field: string, value: any) => {
    setNewPolicy((prev: any) => ({
      ...prev,
      [field]: value,
    }));
    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors((prev) => {
        const updated = { ...prev };
        delete updated[field];
        return updated;
      });
    }
  };

  const handleNestedFieldChange = (field: string, index: number, key: string, value: any) => {
    setNewPolicy((prev: any) => ({
      ...prev,
      [field]: prev[field].map((item: any, i: number) => {
        if (i !== index) return item;
        
        // When changing filter or action type, reset the object to just the new type with defaults
        if (key === 'type' && field === 'filters') {
          const newFilter: any = { type: value };
          if (value === 'last_used') {
            newFilter.days = 30;
            newFilter.threshold = 10;
          } else if (value === 'sku') {
            newFilter.values = [];
          } else if (value === 'tag') {
            newFilter.key = '';
            newFilter.value = '';
          }
          // For 'unattached' and 'stopped', just the type is needed
          return newFilter;
        }
        
        if (key === 'type' && field === 'actions') {
          const newAction: any = { type: value };
          if (value === 'update_sku') {
            newAction.sku = 'Standard_LRS';
          } else if (value === 'scale_dtu') {
            newAction.tiers = [{ name: 'Basic', min_dtu: 5, max_dtu: 5, off_peak_dtu: 5, peak_dtu: 5 }];
          }
          return newAction;
        }
        
        // For non-type changes, just update the field
        return { ...item, [key]: value };
      }),
    }));
  };

  const handleAddFilter = () => {
    // Get available filters for the selected resource
    const availableFilters = getFiltersForResource(newPolicy.resource || '');
    if (availableFilters.length === 0) return;
    
    // Use the first available filter type, with defaults if needed
    const firstFilter = availableFilters[0];
    const newFilter: any = { type: firstFilter.value };
    
    // Set sensible defaults based on filter type
    if (firstFilter.value === 'last_used') {
      newFilter.days = 30;
      newFilter.threshold = 10; // 10% CPU threshold
    } else if (firstFilter.value === 'sku') {
      newFilter.values = [];
    } else if (firstFilter.value === 'tag') {
      newFilter.key = '';
      newFilter.value = '';
    }
    
    setNewPolicy((prev: any) => ({
      ...prev,
      filters: [...(prev.filters || []), newFilter],
    }));
  };

  const handleRemoveFilter = (index: number) => {
    setNewPolicy((prev: any) => ({
      ...prev,
      filters: prev.filters?.filter((_: any, i: number) => i !== index),
    }));
  };

  const handleAddAction = () => {
    // Get available actions for the selected resource
    const availableActions = getActionsForResource(newPolicy.resource || '');
    if (availableActions.length === 0) return;
    
    // Default to 'log' if available, otherwise first available action
    const defaultAction = availableActions.find(a => a.value === 'log') || availableActions[0];
    const newAction: any = { type: defaultAction.value };
    
    // Set defaults for actions that need extra parameters
    if (defaultAction.value === 'update_sku') {
      newAction.sku = 'Standard_LRS';
    } else if (defaultAction.value === 'scale_dtu') {
      newAction.tiers = [
        { name: 'Basic', min_dtu: 5, max_dtu: 5, off_peak_dtu: 5, peak_dtu: 5 }
      ];
    }
    
    setNewPolicy((prev: any) => ({
      ...prev,
      actions: [...(prev.actions || []), newAction],
    }));
  };

  const handleRemoveAction = (index: number) => {
    setNewPolicy((prev: any) => ({
      ...prev,
      actions: prev.actions?.filter((_: any, i: number) => i !== index),
    }));
  };

  const handleOpenNewPolicy = () => {
    setIsEditing(false);
    setSelectedPolicy(null);
    setNewPolicy({
      name: '',
      description: '',
      resource: '',
      enabled: true,
      filters: [],
      actions: [{ type: 'log' }],
    });
    setValidationErrors({});
    setError(null);
    setSuccess(null);
    setOpen(true);
  };

  const handleToggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const handleEditorToggle = () => {
    setIsEditorExpanded(!isEditorExpanded);
  };

  return (
    <Box
      p={2}
      border={1}
      borderRadius={2}
      borderColor={theme.palette.mode === 'light' ? 'grey.300' : 'grey.700'}
      bgcolor={theme.palette.background.paper}
      sx={{ maxHeight: 550, overflowY: 'auto' }}
    >
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Typography variant="h5">Policy Editor</Typography>
        <Tooltip title="Refresh policies">
          <IconButton onClick={fetchPolicies} size="small">
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      <Box
        mt={2}
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        mb={2}
        onClick={handleEditorToggle}
        sx={{ cursor: 'pointer' }}
      >
        <Typography variant="h6">Manage Policies ({policies.length})</Typography>
        {isEditorExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
      </Box>

      <Collapse in={isEditorExpanded} timeout="auto" unmountOnExit>
        <Button
          variant="contained"
          color="primary"
          startIcon={<Add />}
          onClick={handleOpenNewPolicy}
          sx={{ mb: 2 }}
        >
          Add New Policy
        </Button>

        {isLoading ? (
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        ) : policies.length === 0 ? (
          <Typography color="text.secondary" sx={{ p: 2 }}>
            No policies found. Click "Add New Policy" to create one.
          </Typography>
        ) : (
          <List>
            {policies.map((policy, index) => (
              <React.Fragment key={policy.name}>
                <ListItem
                  sx={{
                    bgcolor: theme.palette.mode === 'light' ? 'grey.50' : 'grey.900',
                    borderRadius: 1,
                    mb: 1,
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                    {policy.enabled !== false ? (
                      <Tooltip title="Enabled">
                        <CheckCircle color="success" fontSize="small" />
                      </Tooltip>
                    ) : (
                      <Tooltip title="Disabled">
                        <ErrorIcon color="disabled" fontSize="small" />
                      </Tooltip>
                    )}
                  </Box>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography fontWeight="medium">{policy.name}</Typography>
                        <Chip
                          label={RESOURCE_CONFIGS.find(r => r.value === policy.resource)?.label || policy.resource}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                    }
                    secondary={policy.description || 'No description'}
                    onClick={() => handleToggleExpand(index)}
                    sx={{ cursor: 'pointer' }}
                  />
                  <IconButton
                    edge="end"
                    aria-label="edit"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEdit(policy);
                    }}
                  >
                    <Edit />
                  </IconButton>
                  <IconButton
                    edge="end"
                    aria-label="delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(policy.name);
                    }}
                    sx={{ ml: 1 }}
                  >
                    <Delete />
                  </IconButton>
                  <IconButton onClick={() => handleToggleExpand(index)}>
                    {expandedIndex === index ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </IconButton>
                </ListItem>
                <Collapse in={expandedIndex === index} timeout="auto" unmountOnExit>
                  <Paper elevation={1} sx={{ p: 2, mb: 2, ml: 4 }}>
                    <Typography variant="subtitle2" color="text.secondary">Filters:</Typography>
                    {policy.filters?.length > 0 ? (
                      <Box display="flex" gap={1} flexWrap="wrap" mb={1}>
                        {policy.filters.map((f: any, i: number) => (
                          <Chip
                            key={i}
                            label={`${f.type}${f.days ? `: ${f.days} days` : ''}${f.key ? `: ${f.key}` : ''}`}
                            size="small"
                          />
                        ))}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">No filters</Typography>
                    )}
                    <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 1 }}>Actions:</Typography>
                    <Box display="flex" gap={1} flexWrap="wrap">
                      {policy.actions?.map((a: any, i: number) => (
                        <Chip
                          key={i}
                          label={ALL_ACTIONS[a.type]?.label || a.type}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Paper>
                </Collapse>
              </React.Fragment>
            ))}
          </List>
        )}
      </Collapse>

      {/* Policy Edit/Create Dialog */}
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {isEditing ? `Edit Policy: ${selectedPolicy?.name}` : 'Create New Policy'}
        </DialogTitle>
        <DialogContent dividers>
          {/* Basic Information */}
          <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
            Basic Information
          </Typography>
          
          <TextField
            label="Policy Name"
            value={newPolicy.name || ''}
            onChange={(e) => handleFieldChange('name', e.target.value)}
            fullWidth
            margin="normal"
            variant="outlined"
            required
            disabled={isEditing}
            error={!!validationErrors.name}
            helperText={validationErrors.name || 'Unique identifier (letters, numbers, hyphens, underscores)'}
          />
          
          <TextField
            label="Description"
            value={newPolicy.description || ''}
            onChange={(e) => handleFieldChange('description', e.target.value)}
            fullWidth
            margin="normal"
            variant="outlined"
            multiline
            rows={2}
            helperText="Optional description of what this policy does"
          />
          
          <FormControl fullWidth margin="normal" required error={!!validationErrors.resource}>
            <InputLabel>Resource Type</InputLabel>
            <Select
              value={newPolicy.resource || ''}
              onChange={(e) => {
                const newResource = e.target.value;
                handleFieldChange('resource', newResource);
                // Reset actions and filters when resource type changes (they may not be valid for new type)
                if (newResource !== newPolicy.resource) {
                  setNewPolicy(prev => ({
                    ...prev,
                    resource: newResource,
                    actions: [{ type: 'log' }],
                    filters: [],
                  }));
                }
              }}
              label="Resource Type"
              disabled={isEditing} // Can't change resource type when editing
            >
              {RESOURCE_CONFIGS.map((r) => {
                const existingPolicy = policies.find((p: any) => p.resource === r.value);
                const isDisabled = !isEditing && !!existingPolicy;
                return (
                  <MenuItem 
                    key={r.value} 
                    value={r.value}
                    disabled={isDisabled}
                    sx={isDisabled ? { opacity: 0.6 } : {}}
                  >
                    {r.label}
                    {isDisabled && (
                      <Chip 
                        label={`Used by: ${existingPolicy.name}`} 
                        size="small" 
                        sx={{ ml: 1 }} 
                        color="warning"
                      />
                    )}
                  </MenuItem>
                );
              })}
            </Select>
            <FormHelperText error={!!validationErrors.resource}>
              {validationErrors.resource || (isEditing ? 'Resource type cannot be changed when editing' : 'Select the Azure resource type - each resource can only have one policy')}
            </FormHelperText>
          </FormControl>

          <FormControlLabel
            control={
              <Switch
                checked={newPolicy.enabled ?? true}
                onChange={(e) => handleFieldChange('enabled', e.target.checked)}
                color="primary"
              />
            }
            label="Policy Enabled"
            sx={{ my: 2, display: 'block' }}
          />

          <Divider sx={{ my: 2 }} />

          {/* Filters Section */}
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
            <Typography variant="subtitle1" fontWeight="medium">
              Filters (Optional)
            </Typography>
            <Button 
              size="small" 
              startIcon={<Add />} 
              onClick={handleAddFilter}
              disabled={!newPolicy.resource || getFiltersForResource(newPolicy.resource).length === 0}
            >
              Add Filter
            </Button>
          </Box>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Filters narrow down which resources the policy applies to.
            {newPolicy.resource && (
              <strong> Available for {RESOURCE_CONFIGS.find(r => r.value === newPolicy.resource)?.label}: {getFiltersForResource(newPolicy.resource).map(f => f.label).join(', ') || 'None'}</strong>
            )}
          </Typography>

          {!newPolicy.resource && (
            <Alert severity="info" sx={{ mb: 2 }}>Select a resource type first to see available filters.</Alert>
          )}

          {(newPolicy.filters || []).map((filter: any, index: number) => {
            const selectedFilter = getFiltersForResource(newPolicy.resource || '').find(f => f.value === filter.type);
            return (
            <Paper key={index} variant="outlined" sx={{ p: 2, mb: 2 }}>
              {validationErrors[`filters_${index}`] && (
                <Alert severity="error" sx={{ mb: 1 }}>{validationErrors[`filters_${index}`]}</Alert>
              )}
              <Box display="flex" alignItems="flex-start" gap={2} flexWrap="wrap">
                <FormControl sx={{ minWidth: 200 }}>
                  <InputLabel>Filter Type</InputLabel>
                  <Select
                    value={filter.type || ''}
                    onChange={(e) => handleNestedFieldChange('filters', index, 'type', e.target.value)}
                    label="Filter Type"
                    size="small"
                  >
                    {getFiltersForResource(newPolicy.resource || '').map((f) => (
                      <MenuItem key={f.value} value={f.value}>
                        {f.label}
                      </MenuItem>
                    ))}
                  </Select>
                  {selectedFilter && (
                    <FormHelperText>{selectedFilter.description}</FormHelperText>
                  )}
                </FormControl>

                {filter.type === 'last_used' && (
                  <>
                    <TextField
                      label="Days"
                      type="number"
                      value={filter.days || ''}
                      onChange={(e) => handleNestedFieldChange('filters', index, 'days', parseInt(e.target.value) || 0)}
                      size="small"
                      sx={{ width: 100 }}
                      error={!!validationErrors[`filters_${index}_days`]}
                      helperText={validationErrors[`filters_${index}_days`] || 'Lookback period'}
                    />
                    <TextField
                      label="CPU Threshold %"
                      type="number"
                      value={filter.threshold || ''}
                      onChange={(e) => handleNestedFieldChange('filters', index, 'threshold', parseInt(e.target.value) || 0)}
                      size="small"
                      sx={{ width: 130 }}
                      helperText="Below this = unused"
                    />
                  </>
                )}

                {filter.type === 'sku' && (
                  <TextField
                    label="SKU Values (comma-separated)"
                    value={Array.isArray(filter.values) ? filter.values.join(', ') : filter.values || ''}
                    onChange={(e) => {
                      const values = e.target.value.split(',').map(v => v.trim()).filter(v => v);
                      handleNestedFieldChange('filters', index, 'values', values);
                    }}
                    size="small"
                    sx={{ minWidth: 250 }}
                    error={!!validationErrors[`filters_${index}_values`]}
                    helperText={validationErrors[`filters_${index}_values`] || 'e.g. Standard_GRS, Standard_ZRS'}
                  />
                )}

                {filter.type === 'tag' && (
                  <>
                    <TextField
                      label="Tag Key"
                      value={filter.key || ''}
                      onChange={(e) => handleNestedFieldChange('filters', index, 'key', e.target.value)}
                      size="small"
                      error={!!validationErrors[`filters_${index}_key`]}
                      helperText={validationErrors[`filters_${index}_key`] || 'Required'}
                    />
                    <TextField
                      label="Tag Value (optional)"
                      value={filter.value || ''}
                      onChange={(e) => handleNestedFieldChange('filters', index, 'value', e.target.value)}
                      size="small"
                    />
                  </>
                )}

                <IconButton onClick={() => handleRemoveFilter(index)} color="error" size="small">
                  <Delete />
                </IconButton>
              </Box>
            </Paper>
          );
          })}

          <Divider sx={{ my: 2 }} />

          {/* Actions Section */}
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
            <Typography variant="subtitle1" fontWeight="medium">
              Actions *
            </Typography>
            <Button 
              size="small" 
              startIcon={<Add />} 
              onClick={handleAddAction}
              disabled={!newPolicy.resource}
            >
              Add Action
            </Button>
          </Box>
          {validationErrors.actions && (
            <Alert severity="error" sx={{ mb: 1 }}>{validationErrors.actions}</Alert>
          )}
          <Typography variant="body2" color="text.secondary" mb={2}>
            Actions define what happens to matching resources.
            {newPolicy.resource && (
              <strong> Available for {RESOURCE_CONFIGS.find(r => r.value === newPolicy.resource)?.label}: {getActionsForResource(newPolicy.resource).map(a => a.label).join(', ')}</strong>
            )}
          </Typography>

          {!newPolicy.resource && (
            <Alert severity="info" sx={{ mb: 2 }}>Select a resource type first to see available actions.</Alert>
          )}

          {(newPolicy.actions || []).map((action: any, index: number) => {
            const selectedAction = getActionsForResource(newPolicy.resource || '').find(a => a.value === action.type);
            return (
            <Paper key={index} variant="outlined" sx={{ p: 2, mb: 2 }}>
              {validationErrors[`actions_${index}`] && (
                <Alert severity="error" sx={{ mb: 1 }}>{validationErrors[`actions_${index}`]}</Alert>
              )}
              <Box display="flex" alignItems="flex-start" gap={2} flexWrap="wrap">
                <FormControl sx={{ minWidth: 220 }}>
                  <InputLabel>Action Type</InputLabel>
                  <Select
                    value={action.type || ''}
                    onChange={(e) => handleNestedFieldChange('actions', index, 'type', e.target.value)}
                    label="Action Type"
                    size="small"
                  >
                    {getActionsForResource(newPolicy.resource || '').map((a) => (
                      <MenuItem key={a.value} value={a.value}>
                        {a.label}
                      </MenuItem>
                    ))}
                  </Select>
                  {selectedAction && (
                    <FormHelperText>{selectedAction.description}</FormHelperText>
                  )}
                </FormControl>

                <IconButton
                  onClick={() => handleRemoveAction(index)}
                  color="error"
                  size="small"
                  disabled={(newPolicy.actions?.length || 0) <= 1}
                >
                  <Delete />
                </IconButton>
              </Box>

              {/* Action-specific parameters */}
              {action.type === 'update_sku' && (
                <Box mt={2}>
                  <TextField
                    label="Target SKU"
                    value={action.sku || ''}
                    onChange={(e) => handleNestedFieldChange('actions', index, 'sku', e.target.value)}
                    size="small"
                    fullWidth
                    error={!!validationErrors[`actions_${index}_sku`]}
                    helperText={validationErrors[`actions_${index}_sku`] || 'e.g. Standard_LRS for storage accounts'}
                  />
                </Box>
              )}

              {action.type === 'scale_dtu' && (
                <Box mt={2}>
                  <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                    DTU tier configurations (JSON format). Example: Basic tier with 5 DTU
                  </Typography>
                  <TextField
                    label="Tiers Configuration"
                    value={action.tiers ? JSON.stringify(action.tiers, null, 2) : ''}
                    onChange={(e) => {
                      try {
                        const tiers = JSON.parse(e.target.value);
                        handleNestedFieldChange('actions', index, 'tiers', tiers);
                      } catch {
                        // Invalid JSON, just store raw value for editing
                        handleNestedFieldChange('actions', index, 'tiersRaw', e.target.value);
                      }
                    }}
                    size="small"
                    fullWidth
                    multiline
                    rows={4}
                    error={!!validationErrors[`actions_${index}_tiers`]}
                    helperText={validationErrors[`actions_${index}_tiers`] || '[{"name": "Basic", "min_dtu": 5, "max_dtu": 5, "off_peak_dtu": 5, "peak_dtu": 5}]'}
                  />
                </Box>
              )}
            </Paper>
          );
          })}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} disabled={isSaving}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            variant="contained"
            color="primary"
            disabled={isSaving}
            startIcon={isSaving ? <CircularProgress size={20} /> : undefined}
          >
            {isSaving ? 'Saving...' : 'Save Policy'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PolicyEditor;
