import React from "react";
import { useMsal } from "@azure/msal-react";
import { Button } from "@mui/material";

const LogoutButton: React.FC = () => {
  const { instance } = useMsal();

  const handleLogout = () => {
    instance.logoutPopup({
      postLogoutRedirectUri: "/",
    });
  };

  return (
    <Button variant="contained" color="secondary" onClick={handleLogout}>
      Log Out
    </Button>
  );
};

export default LogoutButton;
