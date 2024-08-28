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
  Grid,
  useTheme,
  CircularProgress,
} from '@mui/material';
import { Delete, Edit, Add } from '@mui/icons-material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

interface PolicyEditorProps {
  policies: any[];
  setPolicies: React.Dispatch<React.SetStateAction<any[]>>;
  isLoading: boolean;
}

const PolicyEditor: React.FC<PolicyEditorProps> = ({ policies, setPolicies, isLoading }) => {
  const theme = useTheme();
  const [selectedPolicy, setSelectedPolicy] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [newPolicy, setNewPolicy] = useState<any>({});
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [isEditorExpanded, setIsEditorExpanded] = useState<boolean>(true);

  const fetchPolicies = async () => {
    try {
      const response = await axios.get('/api/policies-from-blob'); // Adjust your endpoint accordingly
      setPolicies(response.data.policies);
    } catch (err) {
      setError('Error fetching policies');
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
    setNewPolicy({ ...policy }); // Ensure the newPolicy state is correctly set with the selected policy data
    setIsEditing(true);
    setOpen(true);
  };

  const handleDelete = async (policyName: string) => {
    try {
      await axios.delete(`/api/policies/policyeditor/${policyName}`); // Updated the endpoint
      fetchPolicies();
    } catch (err) {
      setError('Error deleting policy');
      console.error(err);
    }
};


const handleSave = async () => {
  try {
      await axios.put(`/api/policies/policyeditor/${newPolicy.name}`, newPolicy);
      setIsEditing(false);
      setSelectedPolicy(null);
      setNewPolicy({});
      setOpen(false);
      fetchPolicies();
  } catch (err) {
      setError('Error saving policy');
      console.error(err);
  }
};
  
  

  const handleFieldChange = (field: string, value: any) => {
    setNewPolicy((prev: any) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleNestedFieldChange = (field: string, index: number, key: string, value: any) => {
    setNewPolicy((prev: any) => ({
      ...prev,
      [field]: prev[field].map((item: any, i: number) =>
        i === index ? { ...item, [key]: value } : item
      ),
    }));
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
      m={2}
      border={1}
      borderRadius={2}
      borderColor={theme.palette.mode === 'light' ? 'grey.300' : 'grey.700'}
      bgcolor={theme.palette.background.paper}
    >
      <Typography variant="h5" gutterBottom>
        Policy Editor
      </Typography>

      <Box
        mt={2}
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        mb={2}
        onClick={handleEditorToggle}
        sx={{ cursor: 'pointer' }}
      >
        <Typography variant="h6">Manage Policies</Typography>
        {isEditorExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
      </Box>

      <Collapse in={isEditorExpanded} timeout="auto" unmountOnExit>
        <Button
          variant="contained"
          color="primary"
          onClick={() => {
            setIsEditing(false);
            setNewPolicy({});
            setOpen(true);
          }}
          sx={{ mb: 2 }}
        >
          Add New Policy
        </Button>

        {error && <Typography color="error">{error}</Typography>}

        {isLoading ? (
          <CircularProgress />
        ) : (
          <List>
            {policies.map((policy, index) => (
              <React.Fragment key={policy.name}>
                <ListItem button onClick={() => handleToggleExpand(index)}>
                  <ListItemText primary={policy.name} secondary={policy.description} />
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
                  >
                    <Delete />
                  </IconButton>
                  {expandedIndex === index ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </ListItem>
                <Collapse in={expandedIndex === index} timeout="auto" unmountOnExit>
                  <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
                    <Typography variant="body1"><strong>Resource:</strong> {policy.resource}</Typography>
                    <Typography variant="body1"><strong>Filters:</strong> {JSON.stringify(policy.filters)}</Typography>
                    <Typography variant="body1"><strong>Actions:</strong> {JSON.stringify(policy.actions)}</Typography>
                  </Paper>
                </Collapse>
              </React.Fragment>
            ))}
          </List>
        )}
      </Collapse>

      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>{isEditing ? 'Edit Policy' : 'Add Policy'}</DialogTitle>
        <DialogContent>
          <TextField
            label="Name"
            value={newPolicy.name || ''}
            onChange={(e) => handleFieldChange('name', e.target.value)}
            fullWidth
            margin="normal"
            variant="outlined"
          />
          <TextField
            label="Description"
            value={newPolicy.description || ''}
            onChange={(e) => handleFieldChange('description', e.target.value)}
            fullWidth
            margin="normal"
            variant="outlined"
          />
          <TextField
            label="Resource"
            value={newPolicy.resource || ''}
            onChange={(e) => handleFieldChange('resource', e.target.value)}
            fullWidth
            margin="normal"
            variant="outlined"
          />
          <Box mb={2}>
            <Typography variant="h6">Filters</Typography>
            {(newPolicy.filters || []).map((filter: any, index: number) => (
              <Box key={index} mb={2} pl={2} borderLeft={1} borderColor="grey.500">
                {Object.keys(filter).map((key) => (
                  <TextField
                    key={key}
                    label={key}
                    value={filter[key] || ''}
                    onChange={(e) => handleNestedFieldChange('filters', index, key, e.target.value)}
                    fullWidth
                    margin="normal"
                    variant="outlined"
                  />
                ))}
              </Box>
            ))}
          </Box>
          <Box mb={2}>
            <Typography variant="h6">Actions</Typography>
            {(newPolicy.actions || []).map((action: any, index: number) => (
              <Box key={index} mb={2} pl={2} borderLeft={1} borderColor="grey.500">
                {Object.keys(action).map((key) => (
                  <TextField
                    key={key}
                    label={key}
                    value={action[key] || ''}
                    onChange={(e) => handleNestedFieldChange('actions', index, key, e.target.value)}
                    fullWidth
                    margin="normal"
                    variant="outlined"
                  />
                ))}
              </Box>
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} color="primary">
            Cancel
          </Button>
          <Button onClick={handleSave} color="primary">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PolicyEditor;
