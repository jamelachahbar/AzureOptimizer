import { Configuration, LogLevel } from "@azure/msal-browser";

export const msalConfig: Configuration = {
    auth: {
        clientId: "271b4213-bf9a-4eea-a3c9-c0fcfb453ddd", // Replace with your Azure AD client ID
        authority: "https://login.microsoftonline.com/f705bf6c-fb69-450d-8604-da3aa8c09eb9", // Replace with your Azure AD tenant ID
        redirectUri: "http://localhost:3000", // Replace with your redirect URI
        postLogoutRedirectUri: '/'
    },
    cache: {
        cacheLocation: "sessionStorage",
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
    scopes: ["User.Read"], // Define the necessary scopes for your app
};
