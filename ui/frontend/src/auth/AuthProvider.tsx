import React, { createContext, useContext, useState, useEffect } from "react";
import { AuthenticationResult, EventType, PublicClientApplication, AccountInfo } from "@azure/msal-browser";
import { msalConfig } from "../authConfig";
import { MsalProvider } from "@azure/msal-react";

interface AuthContextProps {
  isAdmin: boolean;
  roles: string[];
  account: AccountInfo | null;
}

const AuthContext = createContext<AuthContextProps>({
  isAdmin: false,
  roles: [],
  account: null,
});

const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [roles, setRoles] = useState<string[]>([]);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const msalInstance = new PublicClientApplication(msalConfig);

  useEffect(() => {
    // Set the active account if it exists
    const activeAccount = msalInstance.getActiveAccount();
    if (activeAccount) {
      setAccount(activeAccount);
      parseRolesFromToken(activeAccount.idTokenClaims);
    }

    // Listen for login success events
    const callbackId = msalInstance.addEventCallback((event) => {
      if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
        const authResult = event.payload as AuthenticationResult;
        const loggedInAccount = authResult.account;
        msalInstance.setActiveAccount(loggedInAccount);
        setAccount(loggedInAccount);

        parseRolesFromToken(authResult.idTokenClaims);
      }
    });

    return () => {
      if (callbackId) msalInstance.removeEventCallback(callbackId);
    };
  }, [msalInstance]);

  // Helper function to parse roles from the ID token
  const parseRolesFromToken = (idTokenClaims: any) => {
    if (idTokenClaims) {
      const userRoles = idTokenClaims.roles || [];
      setRoles(userRoles);
    } else {
      setRoles([]);
    }
  };

  const isAdmin = roles.includes('Admin');

  return (
    <AuthContext.Provider value={{ isAdmin, roles, account }}>
      <MsalProvider instance={msalInstance}>{children}</MsalProvider>
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

export default AuthProvider;