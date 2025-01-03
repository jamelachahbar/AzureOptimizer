import React, { useState, useMemo, createContext, useContext } from 'react';
import { Container, CssBaseline, Tabs, Tab } from '@mui/material';
import { createTheme, ThemeProvider, useTheme } from '@mui/material/styles';
import Header from './components/Header';
import Optimizer from './Optimizer';
import LLMInteraction_FinopsHubs from './components/LLMInteraction_FinopsHubs';
import { useIsAuthenticated } from "@azure/msal-react";
import { AuthProvider } from './providers/AuthProvider';
import LoginButton from './components/LoginButton';

import {
  Grid,
  CircularProgress,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  SelectChangeEvent,
  IconButton,
} from '@mui/material';

export const ColorModeContext = createContext({ toggleColorMode: () => { } });
export default function ToggleColorModeApp() {
  const [mode, setMode] = useState<'light' | 'dark'>('light');
  const colorMode = useMemo(
    () => ({
      toggleColorMode: () => {
        setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
      },
    }),
    []
  );

  const theme = useMemo(
    () =>
      createTheme({
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
          MuiCssBaseline: {
            styleOverrides: {
              body: {
                backgroundColor: mode === 'light' ? '#FFFFFF' : '#121212',
              },
            },
          },
          MuiButton: {
            styleOverrides: {
              root: {
                borderRadius: 12,
                padding: '8px 16px',
                margin: '0 8px',
                fontSize: '0.70rem',
              },
              containedPrimary: {
                color: mode === 'light' ? '#ffffff' : '#121212',
              },
            },
          },
          MuiTable: {
            styleOverrides: {
              root: {
                borderRadius: 12,
                boxShadow: mode === 'light' ? '0 8px 16px rgba(0,0,0,0.1)' : '0 8px 16px rgba(0,0,0,0.5)',
              },
            },
          },
          MuiTableCell: {
            styleOverrides: {
              root: {
                maxWidth: '1200px', // Set a wider max-width
                padding: '8px', // Add padding
                // padding: '8px 16px',
                borderBottom: '1px solid #e0e0e0',
              },
              head: {
                backgroundColor: mode === 'light' ? '#f4f4f4' : '#E7DDFF',
                color: mode === 'light' ? '#333333' : '#121212',
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
                transition: '0.3s',
                '&:hover': {
                  boxShadow: mode === 'light'
                    ? '0 16px 32px rgba(0,0,0,0.2)'
                    : '0 16px 32px rgba(0,0,0,0.6)',
                },
                marginBottom: '16px',
              },
            },
          },
          MuiTypography: {
            styleOverrides: {
              h3: {
                fontWeight: 'bold',
                marginBottom: '12px',
                marginTop: '12px',
                color: mode === 'light' ? '#333333' : '#FFFFFF',
              },
              h5: {
                fontWeight: 'bold',
                marginBottom: '12px',
                marginTop: '12px',
                color: mode === 'light' ? '#333333' : '#FFFFFF',
              },
              h6: {
                fontWeight: 'bold',
                marginBottom: '12px',
                marginTop: '12px',
                color: mode === 'light' ? '#333333' : '#FFFFFF',
              },
              body1: {
                marginBottom: '12px',
                color: mode === 'light' ? '#333333' : '#FFFFFF',
              }
            },
          },

          MuiContainer: {
            styleOverrides: {
              root: {
                ...(mode === 'light' && {
                  backgroundColor: '#ffffff',
                  color: '#333333',
                }),
                ...(mode === 'dark' && {
                  backgroundColor: '#1f1f1f',
                  color: '#ffffff',
                }),
              },
            },
          },
          MuiPaper: {
            styleOverrides: {
              root: {
                boxShadow: mode === 'light'
                  ? '0 8px 10px rgba(0,0,0,0.1)'
                  : '0 8px 10px rgba(0,0,0,0.5)',
                transition: '0.3s',
                backgroundColor: mode === 'light' ? '#ffffff' : '#1f1f1f',
                color: mode === 'light' ? '#333333' : '#F5F2FD',
              },
            },
          },
          MuiListItem: {
            styleOverrides: {
              root: {
                '&$selected': {
                  backgroundColor: mode === 'light' ? '#f4f4f4' : '#E7DDFF',
                  color: mode === 'light' ? '#333333' : '#121212',
                },
              },
            },
          },
        },
      }),
    [mode]
  );

  const [tabIndex, setTabIndex] = useState(0);
  const isAuthenticated = useIsAuthenticated();

  const handleTabChange = (event: React.ChangeEvent<{}>, newValue: number) => {
    setTabIndex(newValue);
  };

  return (
    <AuthProvider>
      <ColorModeContext.Provider value={colorMode}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <Box
            sx={{
              position: 'relative',
              display: 'flex',
              flexDirection: 'column',
              minHeight: '100dvh',
              // backgroundImage: theme.palette.mode === 'light' 
              // ? 'url(https://www.transparenttextures.com/patterns/axiom-pattern.png)' 
              // : 'url(https://www.transparenttextures.com/patterns/pinstripe-dark.png)', 
              backgroundImage: theme.palette.mode === 'light'
                ? "url('axiom-pattern.png')"
                : "url('pinstripe-dark.png')",
              backgroundRepeat: 'repeat',
              // zIndex: 1, // Ensures that the background is behind everything
            }}
          >
            <Header />
            <Tabs
              value={tabIndex}
              onChange={handleTabChange}
              centered
              sx={{ backgroundColor: theme.palette.background.paper }}
            >
              <Tab label="Optimizer Dashboard" />
              <Tab label="Assessment" />
            </Tabs>
            <Container>

              {tabIndex === 0 && <Optimizer />}
              {tabIndex === 1 && <LLMInteraction_FinopsHubs />}
            </Container>
          </Box>
        </ThemeProvider>
      </ColorModeContext.Provider>
    </AuthProvider>
  );
}