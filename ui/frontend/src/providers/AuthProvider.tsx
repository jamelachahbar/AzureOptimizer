import React, { createContext, useContext, useState, useEffect } from "react";
import { AuthenticationResult, EventType, PublicClientApplication, AccountInfo } from "@azure/msal-browser";
import { msalConfig } from "../authConfig";
import { MsalProvider } from "@azure/msal-react";

interface AuthContextProps {
  isAdmin: boolean;
  roles: string[];
  account: AccountInfo | null;
}

interface CustomIdTokenClaims extends AccountInfo {
  roles?: string[];
}

// Move msalInstance outside of the component to avoid recreating it on each render
const msalInstance = new PublicClientApplication(msalConfig);

const AuthContext = createContext<AuthContextProps>({
  isAdmin: false,
  roles: [],
  account: null,
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [roles, setRoles] = useState<string[]>([]);
  const [account, setAccount] = useState<AccountInfo | null>(null);

  useEffect(() => {
    // Set the active account if it exists
    const activeAccount = msalInstance.getActiveAccount();
    if (activeAccount && activeAccount.idTokenClaims) {
      parseRolesFromToken(activeAccount.idTokenClaims as unknown as CustomIdTokenClaims);
    }

    // Listen for login success events
    const callbackId = msalInstance.addEventCallback((event) => {
      if (event?.eventType === EventType.LOGIN_SUCCESS && event?.payload) {
        const authResult = event.payload as AuthenticationResult;
        const loggedInAccount = authResult.account;
        msalInstance.setActiveAccount(loggedInAccount);
        setAccount(loggedInAccount);

        if (authResult.idTokenClaims) {
          parseRolesFromToken(authResult.idTokenClaims as CustomIdTokenClaims);
        }
      }
    });

    return () => {
      if (callbackId) msalInstance.removeEventCallback(callbackId);
    };
  }, []); // No need to include msalInstance in dependencies, as it is now constant

  // Helper function to parse roles from the ID token
  const parseRolesFromToken = (idTokenClaims: CustomIdTokenClaims | null | undefined) => {
    if (idTokenClaims?.roles) {
      setRoles(idTokenClaims.roles);
    } else {
      setRoles([]);
    }
  };

  const isAdmin = roles.includes("Admin");

  return (
    <AuthContext.Provider value={{ isAdmin, roles, account }}>
      <MsalProvider instance={msalInstance}>{children}</MsalProvider>
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
