import { Configuration, LogLevel } from "@azure/msal-browser";

export const msalConfig: Configuration = {
    auth: {
        clientId: "32cd1b4b-9eaa-44b7-9403-3736fdc0ecac", // Replace with your Azure AD client ID
        // authority: "https://login.microsoftonline.com/dc06fa00-1806-48fc-864d-c47c49f0138c", // Replace with your Azure AD tenant ID
        authority: "https://login.microsoftonline.com/organizations", // App is multi-tenant capable for applications processing accounts in any organizational directory (any Microsoft Entra directory)
        redirectUri: "http://localhost:3000", // Replace with your redirect URI
        postLogoutRedirectUri: '/'

    },
    cache: {
        cacheLocation: "localStorage",
        storeAuthStateInCookie: false,
    },
    system: {
        loggerOptions: {
            loggerCallback: (level: LogLevel, message: string, containsPii: boolean) => {
                if (containsPii) {
                    return;
                }
                switch (level) {
                    case LogLevel.Error:
                        console.error(message);
                        return;
                    case LogLevel.Info:
                        console.info(message);
                        return;
                    case LogLevel.Verbose:
                        console.debug(message);
                        return;
                    case LogLevel.Warning:
                        console.warn(message);
                        return;
                }
            },
            logLevel: LogLevel.Info, // Adjust the log level as needed
            piiLoggingEnabled: false,
        }
    }
};

export const loginRequest = {
    scopes: ["User.Read","openid", "Directory.Read.All", "Subscription.Read","profile", "api://32cd1b4b-9eaa-44b7-9403-3736fdc0ecac/.default","api://32cd1b4b-9eaa-44b7-9403-3736fdc0ecac/Admin","api://32cd1b4b-9eaa-44b7-9403-3736fdc0ecac/User"],

};
