export interface UserAuditLog {
  id: number;
  user_id: number;
  action_performed_by: number;
  action: string;
  details: string;
  ip_address?: string;
  user_agent?: string;
  created_at?: string;
  user_email?: string;  // Used for display purposes
  actor_email?: string; // Used for display purposes
}