import React, { useCallback, useState, useMemo } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  useTheme,
} from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Sector } from 'recharts';

interface ResourceData {
  Resource: string;
  Action: string;
  Status: string;
  Cost: number;
  Policy: string;
  SubscriptionId: string;
}

interface ResourceTypeDistributionCardProps {
  impactedResources: ResourceData[];
  onSliceClick?: (resourceType: string) => void;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AA00FF', '#FF4444', '#4CAF50', '#9C27B0'];

const getResourceTypeFromPolicy = (policy: string): string => {
  const lowerPolicy = policy.toLowerCase();
  if (lowerPolicy.includes('vm') || lowerPolicy.includes('virtual')) return 'Virtual Machines';
  if (lowerPolicy.includes('disk')) return 'Disks';
  if (lowerPolicy.includes('public') || lowerPolicy.includes('ip')) return 'Public IPs';
  if (lowerPolicy.includes('nic') || lowerPolicy.includes('network interface')) return 'Network Interfaces';
  if (lowerPolicy.includes('storage')) return 'Storage';
  if (lowerPolicy.includes('sql') || lowerPolicy.includes('database')) return 'SQL Databases';
  if (lowerPolicy.includes('gateway')) return 'Gateways';
  return 'Other';
};

const ResourceTypeDistributionCard: React.FC<ResourceTypeDistributionCardProps> = ({
  impactedResources,
  onSliceClick,
}) => {
  const theme = useTheme();
  const [activeIndex, setActiveIndex] = useState(0);

  const chartData = useMemo(() => {
    const typeMap: { [key: string]: { count: number; cost: number } } = {};

    impactedResources.forEach((resource) => {
      const resourceType = getResourceTypeFromPolicy(resource.Policy);
      if (!typeMap[resourceType]) {
        typeMap[resourceType] = { count: 0, cost: 0 };
      }
      typeMap[resourceType].count += 1;
      typeMap[resourceType].cost += resource.Cost;
    });

    return Object.entries(typeMap)
      .map(([name, data]) => ({
        name,
        value: data.count,
        cost: data.cost,
      }))
      .sort((a, b) => b.value - a.value);
  }, [impactedResources]);

  const onPieEnter = useCallback((_: any, index: number) => {
    setActiveIndex(index);
  }, []);

  const handleClick = (data: any) => {
    if (onSliceClick && data?.name) {
      onSliceClick(data.name);
    }
  };

  const renderActiveShape = (props: any) => {
    const RADIAN = Math.PI / 180;
    const {
      cx,
      cy,
      midAngle,
      innerRadius,
      outerRadius,
      startAngle,
      endAngle,
      fill,
      payload,
      percent,
      value,
    } = props;
    const sin = Math.sin(-RADIAN * midAngle);
    const cos = Math.cos(-RADIAN * midAngle);
    const sx = cx + (outerRadius + 10) * cos;
    const sy = cy + (outerRadius + 10) * sin;
    const mx = cx + (outerRadius + 30) * cos;
    const my = cy + (outerRadius + 30) * sin;
    const ex = mx + (cos >= 0 ? 1 : 0) * 22;
    const ey = my;
    const textAnchor = cos >= 0 ? 'start' : 'end';

    return (
      <g>
        <text
          x={cx}
          y={cy - 10}
          dy={8}
          textAnchor="middle"
          fill={theme.palette.text.primary}
          fontSize="14px"
          fontWeight="bold"
        >
          {payload.name}
        </text>
        <text
          x={cx}
          y={cy + 10}
          dy={8}
          textAnchor="middle"
          fill={theme.palette.text.secondary}
          fontSize="12px"
        >
          ${payload.cost.toFixed(2)}
        </text>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
        />
        <Sector
          cx={cx}
          cy={cy}
          startAngle={startAngle}
          endAngle={endAngle}
          innerRadius={outerRadius + 6}
          outerRadius={outerRadius + 10}
          fill={fill}
        />
        <path
          d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`}
          stroke={fill}
          fill="none"
        />
        <circle cx={ex} cy={ey} r={3} fill={fill} stroke="none" />
        <text
          x={ex + (cos >= 0 ? 1 : -1) * 12}
          y={ey}
          textAnchor={textAnchor}
          fill={theme.palette.text.primary}
          fontSize="12px"
        >
          {`${value} resources`}
        </text>
        <text
          x={ex + (cos >= 0 ? 1 : -1) * 12}
          y={ey}
          dy={16}
          textAnchor={textAnchor}
          fill={theme.palette.text.secondary}
          fontSize="12px"
        >
          {`${(percent * 100).toFixed(1)}%`}
        </text>
      </g>
    );
  };

  if (impactedResources.length === 0) {
    return (
      <Card sx={{ width: '100%', boxShadow: 3, borderRadius: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Typography variant="h6" mb={2}>Resource Type Distribution</Typography>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flex: 1,
              color: 'text.secondary',
            }}
          >
            <Typography variant="body2">
              Run optimizer to see resource distribution
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        width: '100%',
        height: '100%',
        boxShadow: 3,
        borderRadius: 3,
        display: 'flex',
        flexDirection: 'column',
        '&:hover': {
          boxShadow: 4,
          transition: 'box-shadow 0.3s',
        },
      }}
    >
      <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Typography variant="h6" mb={1}>Resource Type Distribution</Typography>
        <Typography variant="body2" color="text.secondary" mb={1}>
          Click a slice to filter resources
        </Typography>
        <Box sx={{ height: 300, width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                activeIndex={activeIndex}
                activeShape={renderActiveShape}
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius="50%"
                outerRadius="65%"
                fill="#8884d8"
                dataKey="value"
                animationBegin={0}
                onMouseEnter={onPieEnter}
                onClick={handleClick}
                style={{ cursor: onSliceClick ? 'pointer' : 'default' }}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ResourceTypeDistributionCard;
