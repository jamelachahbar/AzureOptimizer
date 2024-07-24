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
  