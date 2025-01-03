import { webLightTheme, makeStyles } from '@fluentui/react-components';

// Example of overriding tokens in Fluent UI
export const customLightTheme = {
  ...webLightTheme, // Extend the base light theme
  fonts: {
    base: {
      fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      fontSize: '16px',
    },
  },
  colorBrandForeground1: '#1976d2', // Set custom brand color
  colorNeutralBackground1: '#ffffff', // Card background or page background
  colorNeutralForeground1: '#000000', // Set the text color for light mode
  
};
