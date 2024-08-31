import React, { ReactNode } from "react";
import { PublicClientApplication, EventType, AuthenticationResult } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { msalConfig } from "../authConfig";

interface AuthProviderProps {
  children: ReactNode;
}

const msalInstance = new PublicClientApplication(msalConfig);

const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  // Handle setting the active account after login
  msalInstance.addEventCallback((event) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
      const payload = event.payload as AuthenticationResult;
      if (payload.account) {
        msalInstance.setActiveAccount(payload.account);
      }
    }
  });

  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
};

export default AuthProvider;
