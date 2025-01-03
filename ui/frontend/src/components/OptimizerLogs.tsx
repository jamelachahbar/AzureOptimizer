import React, { useState } from 'react';
import {
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  useTheme,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

interface OptimizerLogsProps {
  logs: string[];
}

const OptimizerLogs: React.FC<OptimizerLogsProps> = ({ logs }) => {
  const [expanded, setExpanded] = useState(false);
  const theme = useTheme();

  return (
    <Accordion
      expanded={expanded}
      onChange={() => setExpanded(!expanded)}
      sx={{
        width: '100%',
        border: '1px solid #e0e0e0',
        borderRadius: 1,
        boxShadow: 1,
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          backgroundColor: theme.palette.background.paper,
          color: theme.palette.text.primary,
        }}
      >
        <Typography variant="body2">Expand to view logs</Typography>

        {/* Add a badge to show the number of logs */}
        <Typography
          variant="body2"
          sx={{
            backgroundColor: theme.palette.primary.main,
            color: theme.palette.primary.contrastText,
            padding: '2px 4px',
            borderRadius: 2,
            marginLeft: 1,
          }}
        >
          {logs.length}
        </Typography>
          
      </AccordionSummary>
      <AccordionDetails
        sx={{
          padding: 0, // Remove padding to avoid unnecessary spacing
        }}
      >
        <TableContainer
          sx={{
            maxHeight: 400,
            overflow: 'auto',
            backgroundColor: theme.palette.background.paper,
            position: 'relative', // Ensure proper stacking
          }}
        >
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell
                  sx={{
                    fontWeight: 'bold',
                    fontSize: '0.875rem',
                    color: theme.palette.text.primary,
                    backgroundColor: theme.palette.mode === 'light' ? '#f4f4f4' : '#1e1e1e',
                    zIndex: 2, // Ensure header is above content
                    position: 'sticky', // Stick to the top of the container
                    top: 0, // Stick at the top
                  }}
                >
                  Log Entry
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <TableRow key={index}>
                    <TableCell
                      sx={{
                        fontSize: '0.875rem',
                        color: theme.palette.text.secondary,
                        wordBreak: 'break-word',
                      }}
                    >
                      {log}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={1}
                    sx={{
                      fontSize: '0.875rem',
                      color: theme.palette.text.secondary,
                      textAlign: 'center',
                    }}
                  >
                    No logs available.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </AccordionDetails>
    </Accordion>
  );
};

export default OptimizerLogs;
