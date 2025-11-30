export interface User {
  id: number;
  email: string;
  employee_id: string | null;
  first_name: string | null;
  last_name: string | null;
  user_type: 'admin' | 'employee' | 'customer' | null;
  is_active: boolean;
  is_superuser: boolean;
  force_password_change: boolean;
  avatar?: string | null;
  created_at?: string;
  updated_at?: string;
}
