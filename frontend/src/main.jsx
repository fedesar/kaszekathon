import React from 'react';
import ReactDOM from 'react-dom/client';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import './styles/variables.css';
import './components/roi/RoiExtra.css';
import App from './App.jsx';

const theme = createTheme({
  palette: {
    primary: {
      main: '#419FFF',
      dark: '#1C2E62',
      light: '#6AB8FF',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#4F7AB0',
      contrastText: '#FFFFFF',
    },
    success: { main: '#40D390' },
    warning: { main: '#ECB22E' },
    error:   { main: '#FF3366' },
    background: {
      default: '#F9F9F9',
      paper:   '#FFFFFF',
    },
  },
  typography: {
    fontFamily: "'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif",
    fontSize: 14,
  },
  shape: { borderRadius: 8 },
  components: {
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          fontSize: '14px',
          minHeight: '48px',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none' },
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
