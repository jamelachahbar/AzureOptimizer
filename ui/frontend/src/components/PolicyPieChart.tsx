import React, { useCallback, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Sector } from 'recharts';

interface ResourceData {
  Resource: string;
  Action: string;
  Status: string;
  Cost: number;
  Policy: string;
  SubscriptionId: string;
}

interface PolicyPieChartProps {
  impactedResources: ResourceData[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AA00FF', '#FF4444'];

const PolicyPieChart: React.FC<PolicyPieChartProps> = ({ impactedResources }) => {
  const [activeIndex, setActiveIndex] = useState(0);

  const getImpactedResourcesByPolicy = () => {
    const policyCountMap: { [key: string]: number } = {};

    impactedResources.forEach((resource) => {
      policyCountMap[resource.Policy] = (policyCountMap[resource.Policy] || 0) + 1;
    });

    return Object.entries(policyCountMap).map(([policy, count]) => ({
      name: policy,
      value: count,
    }));
  };

  const onPieEnter = useCallback((_: any, index: number) => {
    setActiveIndex(index);
  }, []);

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
    const textAnchor = cos >= 5 ? 'start' : 'end';

    return (
      <g>
        <text x={cx} y={cy} dy={10} textAnchor="middle" fill={fill}>
          {payload.name}
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
          innerRadius={outerRadius + 8}
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
          fill="#333"
        >{`${value}`}</text>
        <text
          x={ex + (cos >= 0 ? 1 : -1) * 10}
          y={ey}
          dy={16}
          textAnchor={textAnchor}
          fill="#999"
        >
          {`${(percent * 100).toFixed(2)}%`}
        </text>
      </g>
    );
  };

  const data = getImpactedResourcesByPolicy();

  return (
    <ResponsiveContainer>
      <PieChart>
        <Pie
          activeIndex={activeIndex}
          activeShape={renderActiveShape}
          data={data}
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="70%"
          fill="#8884d8"
          dataKey="value"
          animationBegin={0}
          onMouseEnter={onPieEnter}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
};

export default PolicyPieChart;
