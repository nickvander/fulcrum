export interface UserAuditLog {
  id: number;
  user_id: number | null;
  action_performed_by: number | null;
  action: string;
  details: string;
  ip_address?: string;
  user_agent?: string;
  created_at?: string;
  user_email?: string;  // Used for display purposes
  actor_email?: string; // Used for display purposes
}