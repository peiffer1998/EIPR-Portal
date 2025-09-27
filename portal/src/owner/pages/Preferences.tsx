import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Page from '../../ui/Page';
import Loading from '../../ui/Loading';
import { Card, CardHeader } from '../../ui/Card';
import { toast } from '../../ui/Toast';
import { myPreferences, updatePreferences } from '../lib/fetchers';
import type { OwnerPreferences } from '../types';

const OwnerPreferencesPage = (): JSX.Element => {
  const queryClient = useQueryClient();

  const preferencesQuery = useQuery({ queryKey: ['owner', 'preferences'], queryFn: myPreferences });

  const updateMutation = useMutation({
    mutationFn: (patch: Partial<OwnerPreferences>) => updatePreferences(patch),
    onSuccess: (next) => {
      queryClient.setQueryData(['owner', 'preferences'], next);
      toast('Preferences saved', 'success');
    },
    onError: () => {
      toast('Unable to update preferences. Please try again.', 'error');
    },
  });

  if (preferencesQuery.isLoading) {
    return <Loading text="Loading preferences…" />;
  }

  if (preferencesQuery.isError) {
    return (
      <Page>
        <Page.Header title="Preferences" />
        <Card>
          <CardHeader title="Unable to load preferences" sub="Please refresh or contact the resort." />
        </Card>
      </Page>
    );
  }

  const preferences = preferencesQuery.data ?? { email_opt_in: true, sms_opt_in: true };

  return (
    <Page>
      <Page.Header title="Preferences" sub="Fine-tune how the resort contacts you." />
      <Card className="p-4">
        <CardHeader title="Notifications" sub="Choose which channels you prefer" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
            <input
              type="checkbox"
              defaultChecked={preferences.email_opt_in ?? true}
              onChange={(event) => updateMutation.mutate({ email_opt_in: event.target.checked })}
            />
            <span>Email updates</span>
          </label>
          <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
            <input
              type="checkbox"
              defaultChecked={preferences.sms_opt_in ?? true}
              onChange={(event) => updateMutation.mutate({ sms_opt_in: event.target.checked })}
            />
            <span>Text messages</span>
          </label>
          <label className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
            <span className="font-medium text-slate-600">Quiet hours</span>
            <input
              className="input"
              defaultValue={preferences.quiet_hours ?? '21:00-08:00'}
              onBlur={(event) => updateMutation.mutate({ quiet_hours: event.target.value })}
              placeholder="21:00-08:00"
            />
          </label>
        </div>
      </Card>
      <Card className="p-4">
        <CardHeader
          title="Need anything else?"
          sub="Call or email the resort and we'll update your profile right away."
        />
        <p className="text-sm text-slate-600">
          You can also request to remove your data or change how we contact you at any time.
        </p>
      </Card>
    </Page>
  );
};

export default OwnerPreferencesPage;
