import api from './api';
import {
  writeOwner,
  writeToken,
  readToken,
  readOwner,
} from './storage';
import type { StoredOwnerSummary } from './storage';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  phoneNumber?: string;
  accountSlug?: string;
}

export interface PortalOwner extends StoredOwnerSummary {
  preferredContactMethod?: string | null;
}

interface RegisterResponse {
  access_token: string;
  owner: {
    id: string;
    preferred_contact_method: string | null;
    user: {
      first_name: string;
      last_name: string;
      email: string;
    };
  };
}

export const login = async (payload: LoginPayload): Promise<string> => {
  const { data } = await api.post<{ access_token: string }>('/portal/login', {
    email: payload.email,
    password: payload.password,
  });
  const token = data.access_token;
  writeToken(token);
  return token;
};

export const registerOwner = async (payload: RegisterPayload): Promise<{ token: string; owner: PortalOwner }> => {
  const { data } = await api.post<RegisterResponse>('/portal/register_owner', {
    first_name: payload.firstName,
    last_name: payload.lastName,
    email: payload.email,
    password: payload.password,
    phone_number: payload.phoneNumber,
    account_slug: payload.accountSlug,
  });
  const owner: PortalOwner = {
    id: data.owner.id,
    firstName: data.owner.user.first_name,
    lastName: data.owner.user.last_name,
    email: data.owner.user.email,
    preferredContactMethod: data.owner.preferred_contact_method,
  };
  writeToken(data.access_token);
  writeOwner(owner);
  return { token: data.access_token, owner };
};

export const getMe = async <T>(): Promise<T> => {
  const { data } = await api.get<T>('/portal/me');
  return data;
};

export const logout = (): void => {
  writeToken(null);
  writeOwner(null);
};

export const getExistingToken = (): string | null => readToken();
export const getExistingOwner = (): StoredOwnerSummary | null => readOwner();
