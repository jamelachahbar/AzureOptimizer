import React, { createContext, useMemo, useState, useContext } from 'react';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';

// Define ColorModeContext
export const ColorModeContext = createContext({ toggleColorMode: () => {} });

// Create a custom theme with support for light/dark modes
function ToggleColorModeApp({ children }
: { children: React.ReactNode }
) {
    const [mode, setMode] = useState<'light' | 'dark'>('light');

    const colorMode = useMemo(
        () => ({
            toggleColorMode: () => {
                setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
            },
        }),
        []
    );

    // Define the theme based on the current mode
    const theme = useMemo(
        () => createTheme({
            palette: {
                mode,
                primary: {
                    main: mode === 'light' ? '#1976d2' : '#E7DDFF',
                },
                secondary: {
                    main: mode === 'light' ? '#dc004e' : '#6CE9A6',
                },
                background: {
                    default: mode === 'light' ? '#f4f4f4' : '#15292B',
                    paper: mode === 'light' ? '#ffffff' : '#181818',
                },
                text: {
                    primary: mode === 'light' ? '#333333' : '#ffffff',
                    secondary: mode === 'light' ? '#666666' : '#F8F6FC',
                },
            },
            components: {
                MuiButton: {
                    styleOverrides: {
                        root: {
                            borderRadius: 12,
                        },
                    },
                },
                MuiCard: {
                    styleOverrides: {
                        root: {
                            borderRadius: 16,
                            boxShadow: mode === 'light'
                                ? '0 8px 16px rgba(0,0,0,0.1)'
                                : '0 8px 16px rgba(0,0,0,0.5)',
                        },
                    },
                },
            },
        }),
        [mode]
    );

    return (
        <ColorModeContext.Provider value={colorMode}>
            <ThemeProvider theme={theme}>
                <CssBaseline /> {/* This ensures consistent background color */}
                {children} {/* The rest of the app will be passed as children */}
            </ThemeProvider>
        </ColorModeContext.Provider>
    );
}

export default ToggleColorModeApp;
