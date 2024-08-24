import React, { useState, useEffect } from 'react';
import { Typography, useTheme } from '@mui/material';

interface TypewriterEffectProps {
  text: string;
  speed?: number;
  variant?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

const TypewriterEffect: React.FC<TypewriterEffectProps> = ({ text, speed = 100, variant = 'h3' }) => {
  const [displayedText, setDisplayedText] = useState('');
  const theme = useTheme(); // Access the current theme

  useEffect(() => {
    let currentIndex = 0;
    const intervalId = setInterval(() => {
      setDisplayedText((prev) => prev + text[currentIndex]);
      currentIndex += 1;
      if (currentIndex === text.length) {
        clearInterval(intervalId);
      }
    }, speed);

    return () => clearInterval(intervalId);
  }, [text, speed]);

  return (
    <Typography variant={variant} sx={{ mb: 4, textAlign: 'center', color: theme.palette.text.primary }}>
      {displayedText}
    </Typography>
  );
};

export default TypewriterEffect;
