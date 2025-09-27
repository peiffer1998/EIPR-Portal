import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";

import { useStaffAuth } from "../state/StaffAuthContext";

export default function RequireStaff({ children }: { children: ReactElement }) {
  const { isAuthed, user } = useStaffAuth();
  if (!isAuthed) return <Navigate to="/staff/login" replace />;
  if (user && user.role === "PET_PARENT") return <div className="p-6">No staff access.</div>;
  return children;
}
