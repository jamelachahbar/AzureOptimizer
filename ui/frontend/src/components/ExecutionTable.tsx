import React from 'react';
import {
    TableContainer,
    Table,
    TableHead,
    TableRow,
    TableCell,
    TableBody,
    Paper,
    useTheme
} from '@mui/material';

interface ExecutionData {
    Action: string;
    Cost: number;
    Message: string;
    Resource: string;
    Status: string;
    SubscriptionId: string;
}

interface ExecutionTableProps {
    executionData: ExecutionData[];
    selectedSubscription: string;
}

const ExecutionTable: React.FC<ExecutionTableProps> = ({ executionData, selectedSubscription }) => {
    const theme = useTheme();

    const filteredExecutionData =
        selectedSubscription === 'All Subscriptions'
            ? executionData
            : executionData.filter((data) => data.SubscriptionId === selectedSubscription);

    // Create row style based on status and color mode
    const getRowStyle = (status: string) => {
        switch (status) {
            case 'Success':
                return {
                    backgroundColor: theme.palette.mode === 'light' ? '#E6F4EA' : '#004D40',
                    color: theme.palette.mode === 'light' ? '#2E7D32' : '#A5D6A7',
                };
            case 'Failed':
                return {
                    backgroundColor: theme.palette.mode === 'light' ? '#FDECEA' : '#B71C1C',
                    color: theme.palette.mode === 'light' ? '#C62828' : '#FFCDD2',
                };
            case 'Dry Run':
                return {
                    backgroundColor: theme.palette.mode === 'light' ? '#FFFFFF' : '#333333',
                    color: theme.palette.mode === 'light' ? '#EF6C00' : '#FFE0B2',
                };
            default:
                return {
                    backgroundColor: theme.palette.background.paper,
                    color: theme.palette.text.primary,
                };
        }
    };

    return (
        <TableContainer component={Paper} style={{ maxHeight: 400 }}>
            <Table stickyHeader>
                <TableHead>
                    <TableRow>
                        <TableCell>Action</TableCell>
                        <TableCell>Message</TableCell>
                        <TableCell>Resource</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Subscription ID</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {filteredExecutionData.map((execution, index) => (
                        <TableRow key={index} style={getRowStyle(execution.Status)}>
                            <TableCell style={{ wordBreak: 'break-word' }}>{execution.Action}</TableCell>
                            <TableCell style={{ wordBreak: 'break-word' }}>{execution.Message}</TableCell>
                            <TableCell style={{ wordBreak: 'break-word' }}>{execution.Resource}</TableCell>
                            <TableCell style={{ wordBreak: 'break-word' }}>{execution.Status}</TableCell>
                            <TableCell style={{ wordBreak: 'break-word' }}>{execution.SubscriptionId}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
};

export default ExecutionTable;
