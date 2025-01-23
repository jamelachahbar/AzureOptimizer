import React from "react";
import { Box, Typography, Button, useTheme, useMediaQuery } from "@mui/material";

interface RollingMessageProps {
  anomaliesCount: number;
  onDismiss: () => void;
  onNavigate: () => void;
  width?: string | number; // Optional: Allows custom width
}

const RollingMessage: React.FC<RollingMessageProps> = ({
  anomaliesCount,
  onDismiss,
  onNavigate,
  width = "100%", // Default to full width
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm")); // For mobile devices

  if (anomaliesCount === 0) return null; // Show message only if anomalies exist

  return (
    <Box
      sx={{
        maxWidth: isMobile ? "90%" : "400px", // Responsive width
        backgroundColor:
          theme.palette.mode === "light"
            ? "rgba(255, 235, 238, 0.95)" // Light background for light mode
            : "rgba(50, 0, 0, 0.95)", // Dark background for dark mode
        color: theme.palette.mode === "light" ? "#b71c1c" : "#f8d7da", // Text color adjustment
        padding: "16px",
        position: "fixed",
        top: "16px",
        left: "50%",
        transform: "translateX(-50%)", // Center horizontally
        zIndex: 1000,
        display: "flex",
        flexDirection: "column", // Stack content vertically
        alignItems: "center",
        borderRadius: "8px",
        boxShadow: "0px 4px 12px rgba(0, 0, 0, 0.2)", // Elevated shadow
        border: `1px solid ${
          theme.palette.mode === "light" ? "#f44336" : "#d32f2f"
        }`,
      }}
    >
      <Typography
        variant="subtitle1"
        sx={{
          fontWeight: "bold",
          textAlign: "center",
          marginBottom: "12px",
          fontSize: "14px",
        }}
      >
        ⚠️ {anomaliesCount} anomalies detected!
      </Typography>
      <Typography
        variant="body2"
        sx={{
          textAlign: "center",
          marginBottom: "12px",
          fontSize: "12px",
        }}
      >
        Click below to view details or dismiss this message.
      </Typography>
      <Box sx={{ display: "flex", gap: "2px" }}>
        <Button
          variant="contained"
          size="small"
          color="error"
          sx={{
            fontWeight: "bold",
            fontSize: "12px",
            padding: "4px 12px",
          }}
          onClick={onNavigate}
        >
          View Anomalies
        </Button>
        <Button
          variant="outlined"
          size="small"
          sx={{
            fontWeight: "bold",
            fontSize: "12px",
            padding: "4px 8px",
            borderColor: theme.palette.mode === "light" ? "#f44336" : "#d32f2f",
            color: theme.palette.mode === "light" ? "#f44336" : "#f8d7da",
          }}
          onClick={onDismiss}
        >
          Dismiss
        </Button>
      </Box>
    </Box>
  );
};

export default RollingMessage;
