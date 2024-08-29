import React, { useState, useEffect } from 'react';
import { Typography, Box } from '@mui/material';
import FlipText from './FlipWords'; // Adjust the path as needed

export const LandingScreen: React.FC<{ onFinished: () => void }> = ({ onFinished }) => {
  useEffect(() => {
    const timer = setTimeout(onFinished, 8500); // Adjust timing as needed
    return () => clearTimeout(timer);
  }, [onFinished]);

  return (
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: 'background.default',
          zIndex: 9999, // Ensure it stays on top
        }}
      >
        <div style={{ padding: "20px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Typography variant="h3" component="span" style={{ fontWeight: "bold" }}>
            &nbsp;
          </Typography>
          <FlipText
            texts={["Built with love💙", "and passion🔥", "for the Developer👨‍💻👩‍💻 Community Day"]}
            interval={2500}
            className="flip-text"
          />
          <Typography variant="h3" component="span" style={{ fontWeight: "bold" }}>
            &nbsp;&nbsp;
          </Typography>
        </div>
      </Box>
  );
};
