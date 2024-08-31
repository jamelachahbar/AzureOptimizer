// src/components/LoginButton.tsx
import React from "react";
import { Button } from "@mui/material";
import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../authConfig";

const LoginButton: React.FC = () => {
  const { instance } = useMsal();

  const handleLogin = () => {
    instance.loginPopup(loginRequest).catch((error) => {
      console.error(error);
    });
  };

  return (
    <Button variant="contained" color="primary" onClick={handleLogin}>
      Log In
    </Button>
  );
};

export default LoginButton;
