import React from 'react';
import { motion } from 'framer-motion';
import { useTheme } from '@mui/material/styles';

export const Highlight: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const theme = useTheme();

  const lightModeBackground = 'linear-gradient(90deg, rgba(137, 127, 250, 1) 0%, rgba(172, 124, 251, 1) 100%)';
  const darkModeBackground = 'linear-gradient(90deg, rgba(105, 94, 251, 1) 0%, rgba(134, 87, 255, 1) 100%)';

  return (
    // Highlight animation for the text and make it sequencially appear
    // with the background color
    // https://www.framer.com/api/motion/motion-value/
    // https://www.framer.com/api/motion/motion-component/
    <motion.span
      initial={{ backgroundSize: '0% 100%' }}
      animate={{ backgroundSize: '100% 100%' }}
      transition={{ duration: 0.5 }}
      style={{
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'left center',
        display: 'inline-block',
        padding: '0 0.5rem',
        borderRadius: '0.25rem',
        backgroundImage: theme.palette.mode === 'light' ? lightModeBackground : darkModeBackground,
      }}
    >
      {children}
    </motion.span>
  );
};

