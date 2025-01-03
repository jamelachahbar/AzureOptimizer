import { webDarkTheme } from '@fluentui/react-components';

// Example of overriding tokens for the dark theme in Fluent UI
export const customDarkTheme = {
  ...webDarkTheme, // Extend the base dark theme
  fonts: {
    base: {
      fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      fontSize: '16px',
    },
  },
  colorBrandForeground1: '#1976d2', // Set custom brand color for text
  colorNeutralBackground1: '#121212', // Darker background for cards or pages
  colorNeutralForeground1: '#ffffff', // Set the text color for dark mode
};
