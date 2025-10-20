export interface UserAuditLog {
  id: number;
  user_id: number;
  action_performed_by: number;
  action: string;
  details: string;
  timestamp: string; // ISO string format
  ip_address: string;
  user_agent: string;
  user_email?: string;      // Loaded separately for display
  actor_email?: string;     // Loaded separately for display
}