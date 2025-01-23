import React, { useEffect, useState, useRef } from "react";
import {
  Table,
  TableContainer,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Paper,
  Typography,
  CircularProgress,
  Box,
  Button
} from "@mui/material";
import RollingMessage from "./RollingMessage";
import { exportToCsv } from "../utils/exportToCsv"; // Import the CSV export utility

const AnomaliesDisplay: React.FC = () => {
  const [anomalies, setAnomalies] = useState<any[]>([]); // Holds anomaly data
  const [loading, setLoading] = useState(true); // Loading state
  const [error, setError] = useState<string | null>(null); // Error state
  const [showMessage, setShowMessage] = useState(true); // Controls RollingMessage visibility
  const tableRef = useRef<HTMLDivElement>(null); // Reference to the table for smooth scrolling

  // Fetch anomalies on component mount
  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/anomalies")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("Fetched anomalies:", data);
        if (Array.isArray(data)) {
          setAnomalies(
            data.map((anomaly) => ({
              date: anomaly.Date || anomaly.date,
              cost: anomaly.Cost || anomaly.cost,
              subscription_id: anomaly.SubscriptionId || "Unknown",
            }))
          );
        } else {
          setError("Unexpected data format.");
        }
        setLoading(false);
      })
      .catch((error) => {
        console.error("Error fetching anomalies:", error);
        setError("Failed to load anomalies data.");
        setLoading(false);
      });
  }, []);

  // Dismiss RollingMessage
  const handleDismiss = () => setShowMessage(false);

  // Scroll to table
  const handleNavigate = () => {
    if (tableRef.current) {
      tableRef.current.scrollIntoView({ behavior: "auto" });
    }
  };
  // Handle CSV export
  const handleDownload = () => {
    exportToCsv("anomalies_data.csv", anomalies);
  };
  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100%",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Typography color="error" variant="h6" align="center">
        {error}
      </Typography>
    );
  }

  return (
    <Box>
      {/* RollingMessage */}
      {showMessage && anomalies.length > 0 && (
        <RollingMessage
          anomaliesCount={anomalies.length}
          onDismiss={handleDismiss}
          onNavigate={handleNavigate}
          width="80%" // Compact size
        />
      )}

      {/* Page Content */}
      <Box 
      >
        {anomalies.length === 0 ? (
          <Typography>No anomalies detected.</Typography>
        ) : (
          <Box>
            {/* <Typography variant="h6" sx={{ marginBottom: "16px" }}>
              Detected Anomalies
            </Typography> */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                marginBottom: "2px",
              }}
            >
              <Button
                variant="contained"
                color="primary"
                size="small"
                onClick={handleDownload}
              >
                Download CSV
              </Button>
            </Box>
            <div ref={tableRef}>
              <TableContainer component={Paper} style={{ maxHeight: 400 }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Cost (USD)</TableCell>
                      <TableCell>Subscription ID</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {anomalies.map((anomaly, index) => (
                      <TableRow key={index}>
                        <TableCell>{anomaly.date}</TableCell>
                        <TableCell>${anomaly.cost.toFixed(2)}</TableCell>
                        <TableCell>{anomaly.subscription_id}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </div>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default AnomaliesDisplay;
