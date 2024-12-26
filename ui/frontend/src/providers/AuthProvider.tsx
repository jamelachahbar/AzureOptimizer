import React, { createContext, useContext, useState, useEffect } from "react";
import {
  AuthenticationResult,
  EventType,
  PublicClientApplication,
  AccountInfo,
} from "@azure/msal-browser";
import { msalConfig } from "../authConfig";
import { MsalProvider } from "@azure/msal-react";

interface AuthContextProps {
  isAdmin: boolean;
  roles: string[];
  account: AccountInfo | null;
}

interface CustomIdTokenClaims {
  roles?: string[];
}

// Move msalInstance outside of the component to ensure it's stable across renders
const msalInstance = new PublicClientApplication(msalConfig);

const AuthContext = createContext<AuthContextProps>({
  isAdmin: false,
  roles: [],
  account: null,
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [roles, setRoles] = useState<string[]>([]);
  const [account, setAccount] = useState<AccountInfo | null>(null);

  // Helper function to parse roles from ID token
  const parseRolesFromToken = (idTokenClaims: CustomIdTokenClaims | undefined) => {
    if (idTokenClaims?.roles) {
      setRoles(idTokenClaims.roles);
    } else {
      console.warn("No roles found in token claims.");
      setRoles([]);
    }
  };
  

  useEffect(() => {
    // Check the active account on initialization
    const activeAccount = msalInstance.getActiveAccount();
    if (activeAccount?.idTokenClaims) {
      console.log("Active Account Claims:", activeAccount.idTokenClaims); // Debugging
      parseRolesFromToken(activeAccount.idTokenClaims as CustomIdTokenClaims);
      setAccount(activeAccount);
    }

    // Listen for login success events
    const callbackId = msalInstance.addEventCallback((event) => {
      if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
        const authResult = event.payload as AuthenticationResult;
        const loggedInAccount = authResult.account;

        msalInstance.setActiveAccount(loggedInAccount);
        setAccount(loggedInAccount);

        console.log("ID Token Claims After Login:", authResult.idTokenClaims); // Debugging
        parseRolesFromToken(authResult.idTokenClaims as CustomIdTokenClaims);
      }
    });

    // Cleanup event callback on unmount
    return () => {
      if (callbackId) msalInstance.removeEventCallback(callbackId);
    };
  }, []);

  // Check if the user has the "Admin" role
  const isAdmin = roles.includes("Admin");

  useEffect(() => {
    console.log("isAdmin:", isAdmin, "Roles:", roles); // Debugging
  }, [roles]);

  return (
    <AuthContext.Provider value={{ isAdmin, roles, account }}>
      <MsalProvider instance={msalInstance}>{children}</MsalProvider>
    </AuthContext.Provider>
  );
};

// Custom hook to consume the AuthContext
export const useAuth = () => useContext(AuthContext);
