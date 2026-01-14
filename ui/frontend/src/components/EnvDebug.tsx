import React from "react";
import { Box, Typography, Paper } from "@mui/material";

const EnvDebug: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h5" gutterBottom>
          Environment Variables Debug
        </Typography>
        <Typography variant="body2" component="pre">
          {JSON.stringify({
            REACT_APP_AZURE_CLIENT_ID: process.env.REACT_APP_AZURE_CLIENT_ID,
            REACT_APP_AZURE_TENANT_ID: process.env.REACT_APP_AZURE_TENANT_ID,
            REACT_APP_REDIRECT_URI: process.env.REACT_APP_REDIRECT_URI,
            NODE_ENV: process.env.NODE_ENV,
            ALL_ENV_VARS: Object.keys(process.env).filter(key => key.startsWith('REACT_APP_'))
          }, null, 2)}
        </Typography>
      </Paper>
    </Box>
  );
};

export default EnvDebug;
