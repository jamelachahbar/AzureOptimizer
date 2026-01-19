import React, { createContext, useContext, useState, useEffect } from "react";
import {
  AuthenticationResult,
  EventType,
  PublicClientApplication,
  AccountInfo,
} from "@azure/msal-browser";
import { msalConfig } from "../authConfig";
import { MsalProvider } from "@azure/msal-react";
import { InteractionRequiredAuthError } from "@azure/msal-browser";

interface AuthContextProps {
  token: any;
  isAdmin: boolean;
  roles: string[];
  account: AccountInfo | null;
  tenantId: string;
}

interface CustomIdTokenClaims {
  roles?: string[];
  tid?: string; // Tenant ID
}

// Initialize MSAL instance outside the component
const msalInstance = new PublicClientApplication(msalConfig);

const AuthContext = createContext<AuthContextProps>({
  isAdmin: false,
  roles: [],
  account: null,
  tenantId: "",
  token: undefined
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [roles, setRoles] = useState<string[]>([]);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [tenantId, setTenantId] = useState<string>("");
  const [token, setToken] = useState<string | null>(null);
  
  // Helper function to parse roles and tenantId from ID token claims
  const parseTokenClaims = (idTokenClaims: CustomIdTokenClaims | undefined) => {
    if (!idTokenClaims) {
      console.warn("No ID token claims found.");
      setRoles([]);
      setTenantId("");
      return;
    }
    setRoles(idTokenClaims.roles || []);
    setTenantId(idTokenClaims.tid || "");
  };

  useEffect(() => {
    // Listen for MSAL events - MsalProvider handles redirect promise internally
    const callbackId = msalInstance.addEventCallback(async (event) => {
      // Handle successful login (both redirect and popup)
      if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
        const authResult = event.payload as AuthenticationResult;
        const loggedInAccount = authResult.account;

        console.log("Login successful:", loggedInAccount?.username);
        msalInstance.setActiveAccount(loggedInAccount);
        setAccount(loggedInAccount);
        parseTokenClaims(authResult.idTokenClaims as CustomIdTokenClaims);
        
        // Acquire access token for Azure Management API
        if (loggedInAccount) {
          try {
            const tokenResponse = await msalInstance.acquireTokenSilent({
              account: loggedInAccount,
              scopes: ["https://management.azure.com/.default"],
            });
            setToken(tokenResponse.accessToken);
          } catch (error) {
            console.error("Error acquiring token after login:", error);
          }
        }
      }
      
      // Handle redirect end - check for existing accounts
      if (event.eventType === EventType.HANDLE_REDIRECT_END) {
        const activeAccount = msalInstance.getActiveAccount();
        if (activeAccount) {
          setAccount(activeAccount);
          parseTokenClaims(activeAccount.idTokenClaims as CustomIdTokenClaims);
          
          // Try to acquire token silently
          try {
            const tokenResponse = await msalInstance.acquireTokenSilent({
              account: activeAccount,
              scopes: ["https://management.azure.com/.default"],
            });
            setToken(tokenResponse.accessToken);
          } catch (error) {
            if (!(error instanceof InteractionRequiredAuthError)) {
              console.error("Error acquiring token:", error);
            }
          }
        }
      }
    });
    
    return () => {
      if (callbackId) msalInstance.removeEventCallback(callbackId);
    };
  }, []);

  // Check for admin role
  const isAdmin = roles.includes("Admin");

  return (
    <AuthContext.Provider value={{ isAdmin, roles, account, tenantId, token }}>
      <MsalProvider instance={msalInstance}>{children}</MsalProvider>
    </AuthContext.Provider>
  );
};

// Custom hook to consume AuthContext
export const useAuth = () => useContext(AuthContext);
