import React from 'react';
import { TableContainer, Table, TableHead, TableRow, TableCell, TableBody, Paper, Typography } from '@mui/material';

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
    const filteredExecutionData =
        selectedSubscription === 'All Subscriptions'
            ? executionData
            : executionData.filter((data) => data.SubscriptionId === selectedSubscription);

    const getRowStyle = (status: string) => {
        switch (status) {
            case 'Success':
                return { backgroundColor: '#7DDA58' };
            case 'Failed':
                return { backgroundColor: '#E4080A' };
            case 'Dry Run':
                return { backgroundColor: '#f5f5'  };
            default:
                return {
                    // backgroundColor: 'white',
                };
        }
    };

    return (
        <TableContainer component={TableContainer} style={{ maxHeight: 400 }}>
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
