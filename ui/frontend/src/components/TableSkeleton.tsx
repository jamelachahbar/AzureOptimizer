import React from 'react';
import { Box, Skeleton, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';

interface TableSkeletonProps {
  /**
   * Number of rows to render in the skeleton
   */
  rows?: number;
  /**
   * Number of columns to render in the skeleton
   */
  columns?: number;
  /**
   * Whether to show a header row
   */
  showHeader?: boolean;
  /**
   * Height of each row
   */
  rowHeight?: number;
  /**
   * Custom column widths (percentages)
   */
  columnWidths?: number[];
}

/**
 * TableSkeleton Component
 * 
 * Displays a loading skeleton that mimics the structure of a data table.
 * Use this instead of empty tables while data is being fetched.
 * 
 * Usage:
 *   {loading ? <TableSkeleton rows={5} columns={4} /> : <ActualTable data={data} />}
 */
const TableSkeleton: React.FC<TableSkeletonProps> = ({
  rows = 5,
  columns = 4,
  showHeader = true,
  rowHeight = 53,
  columnWidths,
}) => {
  // Generate default equal column widths if not provided
  const widths = columnWidths || Array(columns).fill(100 / columns);

  return (
    <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
      <Table>
        {showHeader && (
          <TableHead>
            <TableRow>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <TableCell key={`header-${colIndex}`} sx={{ width: `${widths[colIndex]}%` }}>
                  <Skeleton 
                    animation="wave" 
                    variant="text" 
                    height={24}
                    sx={{ borderRadius: 1 }}
                  />
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
        )}
        <TableBody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <TableRow key={`row-${rowIndex}`} sx={{ height: rowHeight }}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <TableCell key={`cell-${rowIndex}-${colIndex}`}>
                  <Skeleton 
                    animation="wave" 
                    variant="text" 
                    height={20}
                    width={`${70 + Math.random() * 30}%`}
                    sx={{ borderRadius: 1 }}
                  />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

interface CardSkeletonProps {
  /**
   * Number of cards to show
   */
  count?: number;
  /**
   * Height of each card
   */
  height?: number;
  /**
   * Whether to show in a grid layout
   */
  grid?: boolean;
  /**
   * Number of columns in grid
   */
  gridColumns?: number;
}

/**
 * CardSkeleton Component
 * 
 * Displays a loading skeleton for card-based layouts.
 */
const CardSkeleton: React.FC<CardSkeletonProps> = ({
  count = 3,
  height = 150,
  grid = true,
  gridColumns = 3,
}) => {
  return (
    <Box
      sx={{
        display: grid ? 'grid' : 'flex',
        gridTemplateColumns: grid ? `repeat(${gridColumns}, 1fr)` : undefined,
        gap: 2,
        width: '100%',
      }}
    >
      {Array.from({ length: count }).map((_, index) => (
        <Paper
          key={`card-${index}`}
          sx={{
            p: 2,
            borderRadius: 2,
            height,
            display: 'flex',
            flexDirection: 'column',
            gap: 1,
          }}
        >
          <Skeleton 
            animation="wave" 
            variant="text" 
            height={28}
            width="60%"
            sx={{ borderRadius: 1 }}
          />
          <Skeleton 
            animation="wave" 
            variant="text" 
            height={20}
            width="80%"
            sx={{ borderRadius: 1 }}
          />
          <Skeleton 
            animation="wave" 
            variant="rectangular" 
            height={60}
            sx={{ borderRadius: 1, mt: 'auto' }}
          />
        </Paper>
      ))}
    </Box>
  );
};

interface ContentSkeletonProps {
  /**
   * Type of content to simulate
   */
  type?: 'text' | 'chart' | 'mixed';
  /**
   * Height of the skeleton area
   */
  height?: number;
}

/**
 * ContentSkeleton Component
 * 
 * Displays a loading skeleton for various content types.
 */
const ContentSkeleton: React.FC<ContentSkeletonProps> = ({
  type = 'mixed',
  height = 300,
}) => {
  if (type === 'chart') {
    return (
      <Paper sx={{ p: 2, borderRadius: 2, height }}>
        <Skeleton 
          animation="wave" 
          variant="text" 
          height={24}
          width="30%"
          sx={{ mb: 2, borderRadius: 1 }}
        />
        <Skeleton 
          animation="wave" 
          variant="rectangular" 
          height={height - 80}
          sx={{ borderRadius: 1 }}
        />
      </Paper>
    );
  }

  if (type === 'text') {
    return (
      <Box sx={{ width: '100%' }}>
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton 
            key={`text-${index}`}
            animation="wave" 
            variant="text" 
            height={20}
            width={`${60 + Math.random() * 40}%`}
            sx={{ mb: 1, borderRadius: 1 }}
          />
        ))}
      </Box>
    );
  }

  // Mixed content
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', gap: 2 }}>
        <Skeleton 
          animation="wave" 
          variant="circular" 
          width={48}
          height={48}
        />
        <Box sx={{ flex: 1 }}>
          <Skeleton 
            animation="wave" 
            variant="text" 
            height={24}
            width="40%"
            sx={{ borderRadius: 1 }}
          />
          <Skeleton 
            animation="wave" 
            variant="text" 
            height={18}
            width="60%"
            sx={{ borderRadius: 1 }}
          />
        </Box>
      </Box>
      <Skeleton 
        animation="wave" 
        variant="rectangular" 
        height={height - 100}
        sx={{ borderRadius: 1 }}
      />
    </Box>
  );
};

interface DashboardSkeletonProps {
  /**
   * Show the full dashboard skeleton layout
   */
  showCards?: boolean;
  showTable?: boolean;
  showChart?: boolean;
}

/**
 * DashboardSkeleton Component
 * 
 * Displays a complete dashboard loading skeleton matching the optimizer layout.
 */
const DashboardSkeleton: React.FC<DashboardSkeletonProps> = ({
  showCards = true,
  showTable = true,
  showChart = true,
}) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, p: 2 }}>
      {showCards && (
        <CardSkeleton count={4} height={120} gridColumns={4} />
      )}
      
      {showChart && (
        <ContentSkeleton type="chart" height={300} />
      )}
      
      {showTable && (
        <TableSkeleton rows={6} columns={5} />
      )}
    </Box>
  );
};

export { TableSkeleton, CardSkeleton, ContentSkeleton, DashboardSkeleton };
export default TableSkeleton;
