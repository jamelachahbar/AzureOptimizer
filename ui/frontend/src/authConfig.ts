import { Configuration, LogLevel } from "@azure/msal-browser";

// Read from environment variables with fallback
const clientId = process.env.REACT_APP_AZURE_CLIENT_ID || "02fb84dd-8908-47de-bcec-daff54959a76";
const tenantId = process.env.REACT_APP_AZURE_TENANT_ID || "b98651dc-4756-44cb-ad4b-24f462ce02e0";

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
        postLogoutRedirectUri: '/'

    },
    cache: {
        cacheLocation: "sessionStorage",
        storeAuthStateInCookie: true,
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
