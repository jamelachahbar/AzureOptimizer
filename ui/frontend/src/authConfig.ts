import { Configuration, LogLevel } from "@azure/msal-browser";

// Extend Window interface to include _env_
declare global {
    interface Window {
        _env_?: {
            REACT_APP_AZURE_CLIENT_ID?: string;
            REACT_APP_AZURE_TENANT_ID?: string;
            BACKEND_URL?: string;
            VITE_API_URL?: string;
            VITE_APP_TITLE?: string;
            VITE_ENABLE_ANALYTICS?: string;
        };
    }
}

// Read from runtime environment (window._env_), then process.env - NO hardcoded fallbacks
const clientId = (typeof window !== 'undefined' && window._env_?.REACT_APP_AZURE_CLIENT_ID) 
    || process.env.REACT_APP_AZURE_CLIENT_ID 
    || "";
const tenantId = (typeof window !== 'undefined' && window._env_?.REACT_APP_AZURE_TENANT_ID) 
    || process.env.REACT_APP_AZURE_TENANT_ID 
    || "";

// Use window.location.origin for dynamic redirect URI (works in both localhost and deployed environments)
const redirectUri = typeof window !== 'undefined' ? window.location.origin : "http://localhost:3000";

// Debug logging
console.log("Auth Config Debug:");
console.log("- Client ID from env:", process.env.REACT_APP_AZURE_CLIENT_ID);
console.log("- Client ID used:", clientId);
console.log("- Tenant ID:", tenantId);
console.log("- Redirect URI:", redirectUri);

// Validate client ID
if (!clientId || clientId === "") {
    console.error("CRITICAL: REACT_APP_AZURE_CLIENT_ID is not set!");
}

export const msalConfig: Configuration = {
    auth: {
        clientId: clientId,
        // Use specific tenant ID to ensure login to your tenant only
        authority: `https://login.microsoftonline.com/${tenantId}`,
        redirectUri: redirectUri,
        postLogoutRedirectUri: '/',
        navigateToLoginRequestUrl: true,
    },
    cache: {
        cacheLocation: "localStorage",  // Changed from sessionStorage - more reliable for redirects
        storeAuthStateInCookie: true,   // Helps with IE11/Edge issues
    },
    system: {
        loggerOptions: {
            loggerCallback: (level: LogLevel, message: string, containsPii: boolean) => {
                if (containsPii) {
                    return;
                }
                switch (level) {
                    case LogLevel.Error:
                        console.error("MSAL Error:", message);
                        return;
                    case LogLevel.Info:
                        console.info("MSAL Info:", message);
                        return;
                    case LogLevel.Verbose:
                        console.debug("MSAL Verbose:", message);
                        return;
                    case LogLevel.Warning:
                        console.warn("MSAL Warning:", message);
                        return;
                }
            },
            logLevel: LogLevel.Verbose, // Increased to Verbose for more debugging
            piiLoggingEnabled: false,
        }
    }
};

// Log the complete MSAL config at module load time
console.log("=== MSAL Config at Module Load ===");
console.log("Full msalConfig:", JSON.stringify(msalConfig, null, 2));

export const loginRequest = {
    scopes: [
        "User.Read",
        "openid",
        "profile",
        "https://management.azure.com/user_impersonation"
    ],
};
