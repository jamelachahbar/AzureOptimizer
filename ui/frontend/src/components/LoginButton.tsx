import React from "react";
import { useMsal } from "@azure/msal-react";
import { Button, Box, Typography } from "@mui/material";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowDownLong } from "@fortawesome/free-solid-svg-icons";

const LoginButton: React.FC = () => {
  const { instance } = useMsal();

  const handleLogin = () => {
    instance.loginPopup().catch((error) => {
      console.error(error);
    });
  };

  return (
    <Box sx={{ textAlign: 'center', mt: 5 }}>
      <Typography variant="h3" sx={{ mb: 2 }}>
        Welcome to Azure Optimizer
      </Typography>
      <Typography variant="body1" sx={{ mb: 1 }}>
        Log in to continue
      </Typography>
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
        <FontAwesomeIcon icon={faArrowDownLong} size="2x" />
      </Box>
      <Button
        variant="contained"
        color="primary"
        onClick={handleLogin}
        sx={{
          animation: 'bounce 3s infinite',
          '@keyframes bounce': {
            '0%, 20%, 50%, 80%, 100%': {
              transform: 'translateY(0)',
            },
            '40%': {
              transform: 'translateY(-10px)',
            },
            '60%': {
              transform: 'translateY(-5px)',
            },
          },
        }}
      >
        Log In
      </Button>
    </Box>
  );
};

export default LoginButton;
