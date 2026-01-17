export interface CostData {
    date: string;
    cost: number;
    subscriptionId: string;
  }
  
  export interface ExecutionData {
    date: string;
    status: string;
    details: string;
  }
  
  export interface ResourceData {
    resource: string;
    action: string;
    status: string;
  }

export interface OptimizationScore {
  score: number;
  trend: number;
  issues: {
    wasteResources: number;
    disabledPolicies: number;
    potentialSavings: number;
  };
}

export interface AdvisorRecommendation {
  uuid: string;
  problem: string;
  solution: string;
  impact: 'High' | 'Medium' | 'Low';
  annualSavings: number;
  subscriptionId: string;
  resourceId: string;
}
