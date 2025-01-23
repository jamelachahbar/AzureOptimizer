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
    // Handle active account on load
    const activeAccount = msalInstance.getActiveAccount();
    if (activeAccount?.idTokenClaims) {
      parseTokenClaims(activeAccount.idTokenClaims as CustomIdTokenClaims);
      setAccount(activeAccount);
    }

    // Listen for login events
    const callbackId = msalInstance.addEventCallback(async (event) => {
      if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
        const authResult = event.payload as AuthenticationResult;
        const loggedInAccount = authResult.account;

        msalInstance.setActiveAccount(loggedInAccount);
        setAccount(loggedInAccount);

        // Parse claims from the ID token
        parseTokenClaims(authResult.idTokenClaims as CustomIdTokenClaims);

        
        // Fetch access token

        if (loggedInAccount) {
          try {
            const tokenResponse = await msalInstance.acquireTokenSilent({
              account: loggedInAccount,
              scopes: ["https://management.azure.com/.default"],
            });
            setToken(tokenResponse.accessToken);
          } catch (error) {
            if (error instanceof InteractionRequiredAuthError) {
              console.warn("Interaction required. Initiating popup consent flow.");
              try {
                const tokenResponse = await msalInstance.acquireTokenPopup({
                  scopes: ["https://management.azure.com/.default"],
                });
                setToken(tokenResponse.accessToken);
              } catch (popupError) {
                console.error("Error during interactive token acquisition:", popupError);
              }
            } else {
              console.error("Error acquiring token silently:", error);
            }
          }
        } else {
          console.error("No logged in account found. Cannot acquire token.");
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
