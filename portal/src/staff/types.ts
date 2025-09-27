export type StaffUserRole =
  | 'superadmin'
  | 'admin'
  | 'manager'
  | 'staff'
  | 'pet_parent';

export interface StaffUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string | null;
  role: StaffUserRole;
  account_id: string;
}
