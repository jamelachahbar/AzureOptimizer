import React, { useRef } from "react";
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
  Button,
} from "@mui/material";
import RollingMessage from "./RollingMessage";
import { exportToCsv } from "../utils/exportToCsv";

interface AnomaliesDisplayProps {
  anomalies: any[]; // Pass anomaly data from parent
  loading: boolean; // Parent controls the loading state
  error: string | null; // Parent handles and passes error messages
}

const AnomaliesDisplay: React.FC<AnomaliesDisplayProps> = ({
  anomalies = [],
  loading,
  error,
}) => {
  const tableRef = useRef<HTMLDivElement>(null); // Reference to the table for smooth scrolling
  const [showMessage, setShowMessage] = React.useState(true); // Controls RollingMessage visibility

  // Dismiss RollingMessage
  const handleDismiss = () => setShowMessage(false);

  // Scroll to table
  const handleNavigate = () => {
    if (tableRef.current) {
      tableRef.current.scrollIntoView({ behavior: "smooth" });
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

      {/* Anomalies Table */}
      <Box>
        {anomalies.length === 0 ? (
          <Typography>No anomalies detected.</Typography>
        ) : (
          <Box>
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
                        <TableCell>{anomaly?.date || "Unknown"}</TableCell>
                        <TableCell>
                          $
                          {typeof anomaly?.cost === "number"
                            ? anomaly.cost.toFixed(2)
                            : "N/A"}
                        </TableCell>
                        <TableCell>
                          {anomaly?.SubscriptionId || "Unknown"}
                        </TableCell>
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
