import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  IconButton,
  Typography,
  Tabs,
  Tab,
  useTheme,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PolicyTable from './PolicyTable';
import PolicyEditor from './PolicyEditor';

interface Policy {
  name: string;
  description: string;
  enabled: boolean;
}

interface PolicySettingsModalProps {
  open: boolean;
  onClose: () => void;
  policies: Policy[];
  setPolicies: React.Dispatch<React.SetStateAction<Policy[]>>;
  handleTogglePolicy: (policyName: string, enabled: boolean) => void;
  isLoading: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`policy-tabpanel-${index}`}
      aria-labelledby={`policy-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
}

const PolicySettingsModal: React.FC<PolicySettingsModalProps> = ({
  open,
  onClose,
  policies,
  setPolicies,
  handleTogglePolicy,
  isLoading,
}) => {
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          minHeight: '60vh',
          maxHeight: '80vh',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: `1px solid ${theme.palette.divider}`,
          pb: 1,
        }}
      >
        <Typography variant="h6" component="span">
          Policy Settings
        </Typography>
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{ color: theme.palette.grey[500] }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ p: 0 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Toggle Policies" />
            <Tab label="Edit Policies" />
          </Tabs>
        </Box>
        <Box sx={{ p: 2, maxHeight: 'calc(80vh - 140px)', overflowY: 'auto' }}>
          <TabPanel value={tabValue} index={0}>
            <PolicyTable policies={policies} handleToggle={handleTogglePolicy} />
          </TabPanel>
          <TabPanel value={tabValue} index={1}>
            <PolicyEditor
              policies={policies}
              setPolicies={setPolicies}
              isLoading={isLoading}
            />
          </TabPanel>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default PolicySettingsModal;
