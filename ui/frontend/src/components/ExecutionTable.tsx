import React from 'react';
import { Typography, Paper } from '@mui/material';
import { Virtuoso } from 'react-virtuoso';

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
                return { backgroundColor: 'lightgreen' };
            case 'Failed':
                return { backgroundColor: 'red' };
            case 'Dry Run':
                return { backgroundColor: 'lightyellow' };
            default:
                return {};
        }
    };

    return (
        <Paper style={{ height: 500 }}>
            <div
                style={{
                    display: 'flex',
                    position: 'relative',
                    top: 0,
                    backgroundColor: '#f4f4f4',
                    zIndex: 1,
                    padding: '8px 16px',
                    borderBottom: '1px solid #e0e0e0',
                    marginBottom: -10,
                }}
            >
                <Typography style={{ flex: 1, fontWeight: 'bold' }}>Action</Typography>
                <Typography style={{ flex: 1, fontWeight: 'bold' }}>Message</Typography>
                <Typography style={{ flex: 1, fontWeight: 'bold' }}>Resource</Typography>
                <Typography style={{ flex: 1, fontWeight: 'bold' }}>Status</Typography>
                <Typography style={{ flex: 1, fontWeight: 'bold' }}>Subscription ID</Typography>
            </div>
            <Virtuoso
                data={filteredExecutionData}
                itemContent={(index, execution) => (
                    <div
                        style={{
                            display: 'flex',
                            padding: '8px 10px',
                            borderBottom: '1px solid #e0e0e0',
                            ...getRowStyle(execution.Status),
                        }}
                    >
                        <Typography style={{ flex: 1 }}>{execution.Action}</Typography>
                        <Typography style={{ flex: 1 }}>{execution.Message}</Typography>
                        <Typography style={{ flex: 1 }}>{execution.Resource}</Typography>
                        <Typography style={{ flex: 1 }}>{execution.Status}</Typography>
                        <Typography style={{ flex: 1 }}>{execution.SubscriptionId}</Typography>
                    </div>
                )}
                style={{ maxHeight: 500, width: '100%' }}
            />
        </Paper>
    );
};

export default ExecutionTable;
