export interface OwnerSummary {
  id: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  preferences?: OwnerPreferences;
  [key: string]: unknown;
}

export interface OwnerPet {
  id: string;
  name?: string;
  breed?: string;
  species?: string;
  pet_type?: string;
  birthdate?: string | null;
  files?: OwnerPetFile[];
  [key: string]: unknown;
}

export interface OwnerPetFile {
  id: string;
  name?: string;
  file_name?: string;
  content_type?: string;
  created_at?: string;
  url?: string | null;
  [key: string]: unknown;
}

export interface OwnerReservation {
  id: string;
  reservation_type?: string;
  status?: string;
  start_at?: string;
  end_at?: string;
  pet?: OwnerPet;
  pet_id?: string;
  location_id?: string;
  [key: string]: unknown;
}

export interface OwnerGroomingAppointment {
  id: string;
  pet?: OwnerPet;
  pet_id?: string;
  service?: { id?: string; name?: string } | null;
  service_id?: string | null;
  start_at?: string;
  status?: string;
  notes?: string | null;
  [key: string]: unknown;
}

export interface OwnerPackageSummary {
  id: string;
  package?: { id?: string; name?: string } | null;
  package_id?: string;
  package_name?: string;
  remaining?: number | null;
  balance?: number | null;
  status?: string;
  [key: string]: unknown;
}

export interface OwnerCreditLedgerEntry {
  id?: string;
  ts?: string;
  date?: string;
  type?: string;
  amount?: number | string;
  note?: string | null;
  [key: string]: unknown;
}

export interface OwnerCreditSummary {
  balance?: number | string;
  ledger?: OwnerCreditLedgerEntry[];
}

export interface OwnerInvoice {
  id: string;
  pet_name?: string;
  pet_id?: string;
  status?: string;
  total?: number | string;
  created_at?: string;
  [key: string]: unknown;
}

export interface OwnerReportCardMedia {
  id: string;
  display_url?: string | null;
  document?: { id: string; file_name?: string } | null;
  [key: string]: unknown;
}

export interface OwnerReportCard {
  id: string;
  pet_id?: string;
  pet?: OwnerPet;
  pet_name?: string;
  created_at?: string;
  occurred_on?: string;
  notes?: string | null;
  summary?: string | null;
  media?: OwnerReportCardMedia[];
  [key: string]: unknown;
}

export interface OwnerDocument {
  id: string;
  name?: string;
  file_name?: string;
  mime?: string;
  content_type?: string;
  created_at?: string;
  url?: string | null;
  [key: string]: unknown;
}

export interface OwnerPreferences {
  email_opt_in?: boolean;
  sms_opt_in?: boolean;
  quiet_hours?: string | null;
  [key: string]: unknown;
}
