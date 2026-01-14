import React from 'react';
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { Button, Box, Typography, Paper } from "@mui/material";

const TestLogin: React.FC = () => {
  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const handleLogin = async () => {
    try {
      console.log("Starting login...");
      const response = await instance.loginPopup({
        scopes: ["User.Read", "openid", "profile"]
      });
      console.log("Login successful:", response);
    } catch (error) {
      console.error("Login error:", error);
      alert(`Login failed: ${JSON.stringify(error)}`);
    }
  };

  return (
    <Paper sx={{ p: 3, m: 3 }}>
      <Typography variant="h5" gutterBottom>
        Authentication Test
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2">
          <strong>Authenticated:</strong> {isAuthenticated ? "Yes" : "No"}
        </Typography>
        <Typography variant="body2">
          <strong>Accounts:</strong> {accounts.length}
        </Typography>
        {accounts.length > 0 && (
          <Typography variant="body2">
            <strong>User:</strong> {accounts[0].username}
          </Typography>
        )}
      </Box>

      {!isAuthenticated && (
        <Button
          variant="contained"
          color="primary"
          onClick={handleLogin}
        >
          Test Login
        </Button>
      )}

      {isAuthenticated && (
        <Button
          variant="outlined"
          color="secondary"
          onClick={() => instance.logout()}
        >
          Logout
        </Button>
      )}
    </Paper>
  );
};

export default TestLogin;
