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
  tenantId: string;
}

interface CustomIdTokenClaims {
  roles?: string[];
  tid?: string;
}

// MSAL instance outside the component
const msalInstance = new PublicClientApplication(msalConfig);

const AuthContext = createContext<AuthContextProps>({
  isAdmin: false,
  roles: [],
  account: null,
  tenantId: "",
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [roles, setRoles] = useState<string[]>([]);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [tenantId, setTenantId] = useState<string>("");

  // Parse roles and tenant ID from the token
  const parseRolesFromToken = (idTokenClaims: CustomIdTokenClaims | undefined) => {
    setRoles(idTokenClaims?.roles || []);
  };

  const parseTenantIdFromToken = (idTokenClaims: CustomIdTokenClaims | undefined) => {
    setTenantId(idTokenClaims?.tid || "");
  };

  // Load the active account from MSAL and restore roles/tenantId
  const loadActiveAccount = () => {
    const activeAccount = msalInstance.getActiveAccount();
    if (activeAccount?.idTokenClaims) {
      parseRolesFromToken(activeAccount.idTokenClaims as CustomIdTokenClaims);
      parseTenantIdFromToken(activeAccount.idTokenClaims as CustomIdTokenClaims);
      setAccount(activeAccount);
    } else {
      console.warn("No active account found.");
    }
  };

  useEffect(() => {
    // Load the active account on component mount
    loadActiveAccount();

    // Listen for login success events
    const callbackId = msalInstance.addEventCallback((event) => {
      if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
        const authResult = event.payload as AuthenticationResult;
        const loggedInAccount = authResult.account;

        msalInstance.setActiveAccount(loggedInAccount); // Persist active account
        parseRolesFromToken(authResult.idTokenClaims as CustomIdTokenClaims);
        parseTenantIdFromToken(authResult.idTokenClaims as CustomIdTokenClaims);
        setAccount(loggedInAccount);
      }
    });

    // Cleanup event callback
    return () => {
      if (callbackId) msalInstance.removeEventCallback(callbackId);
    };
  }, []);

  // Persist active account roles/tenantId across tabs
  useEffect(() => {
    window.addEventListener("storage", loadActiveAccount);
    return () => {
      window.removeEventListener("storage", loadActiveAccount);
    };
  }, []);

  const isAdmin = roles.includes("Admin");

  return (
    <AuthContext.Provider value={{ isAdmin, roles, account, tenantId }}>
      <MsalProvider instance={msalInstance}>{children}</MsalProvider>
    </AuthContext.Provider>
  );
};

// Custom hook to consume the AuthContext
export const useAuth = () => useContext(AuthContext);
