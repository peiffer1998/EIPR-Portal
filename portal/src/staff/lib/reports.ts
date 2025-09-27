import type { AxiosRequestConfig } from 'axios';

import { staffApi } from './client';

interface DateRangeFilters {
  dateFrom: string;
  dateTo: string;
}

type ReportType = 'revenue' | 'occupancy' | 'grooming-commissions';

type ReportConfig = {
  csvPath: string;
  csvParams: (filters: DateRangeFilters) => Record<string, unknown>;
  fallbackPath: string;
  fallbackParams: (filters: DateRangeFilters) => Record<string, unknown>;
  fallbackToCsv: (data: unknown) => string;
  fileName: (filters: DateRangeFilters) => string;
};

const reportConfigs: Record<ReportType, ReportConfig> = {
  revenue: {
    csvPath: '/reports-max/revenue-by-date.csv',
    csvParams: ({ dateFrom, dateTo }) => ({ date_from: dateFrom, date_to: dateTo }),
    fallbackPath: '/reports/revenue',
    fallbackParams: ({ dateFrom, dateTo }) => ({ start_date: dateFrom, end_date: dateTo }),
    fallbackToCsv: (raw) => {
      const rows = [['Date', 'Location', 'Total Revenue']];
      if (raw && typeof raw === 'object' && 'entries' in raw) {
        const entries = (raw as any).entries as Array<{
          location_name: string;
          period_start: string;
          total_revenue: string | number;
        }>;
        entries.forEach((entry) => {
          rows.push([
            String(entry.period_start ?? ''),
            entry.location_name,
            typeof entry.total_revenue === 'number'
              ? entry.total_revenue.toFixed(2)
              : entry.total_revenue,
          ]);
        });
      }
      return rows.map((row) => row.join(',')).join('\n');
    },
    fileName: ({ dateFrom, dateTo }) => `revenue_${dateFrom}_${dateTo}.csv`,
  },
  occupancy: {
    csvPath: '/reports-max/occupancy.csv',
    csvParams: ({ dateFrom, dateTo }) => ({ date_from: dateFrom, date_to: dateTo }),
    fallbackPath: '/reports/occupancy',
    fallbackParams: ({ dateFrom, dateTo }) => ({ start_date: dateFrom, end_date: dateTo }),
    fallbackToCsv: (raw) => {
      const rows = [['Date', 'Location', 'Type', 'Booked', 'Capacity', 'Occupancy Rate']];
      if (Array.isArray(raw)) {
        raw.forEach((entry) => {
          rows.push([
            String(entry.date ?? ''),
            entry.location_name,
            entry.reservation_type,
            String(entry.booked ?? ''),
            String(entry.capacity ?? ''),
            entry.occupancy_rate != null ? String(entry.occupancy_rate) : '',
          ]);
        });
      }
      return rows.map((row) => row.join(',')).join('\n');
    },
    fileName: ({ dateFrom, dateTo }) => `occupancy_${dateFrom}_${dateTo}.csv`,
  },
  'grooming-commissions': {
    csvPath: '/reports-max/grooming-commissions.csv',
    csvParams: ({ dateFrom, dateTo }) => ({ date_from: dateFrom, date_to: dateTo }),
    fallbackPath: '/grooming/reports/commissions',
    fallbackParams: ({ dateFrom, dateTo }) => ({ date_from: dateFrom, date_to: dateTo }),
    fallbackToCsv: (raw) => {
      const rows = [['Specialist ID', 'Specialist', 'Appointments', 'Total Commission']];
      if (Array.isArray(raw)) {
        raw.forEach((entry) => {
          rows.push([
            entry.specialist_id,
            entry.specialist_name ?? '',
            String(entry.appointment_count ?? ''),
            typeof entry.total_commission === 'number'
              ? entry.total_commission.toFixed(2)
              : String(entry.total_commission ?? ''),
          ]);
        });
      }
      return rows.map((row) => row.join(',')).join('\n');
    },
    fileName: ({ dateFrom, dateTo }) => `grooming_commissions_${dateFrom}_${dateTo}.csv`,
  },
};

const triggerDownload = (content: BlobPart, filename: string, type = 'text/csv') => {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
};

const attemptCsvFetch = async (
  path: string,
  params: Record<string, unknown>,
  filename: string,
) => {
  const config: AxiosRequestConfig = {
    params,
    responseType: 'blob',
    validateStatus: (status) => status >= 200 && status < 400,
  };
  const response = await staffApi.get(path, config);
  const blob = response.data as Blob;
  triggerDownload(blob, filename, blob.type || 'text/csv');
};

export const downloadReportCsv = async (
  type: ReportType,
  filters: DateRangeFilters,
): Promise<void> => {
  const config = reportConfigs[type];
  const fileName = config.fileName(filters);
  try {
    await attemptCsvFetch(config.csvPath, config.csvParams(filters), fileName);
    return;
  } catch (error) {
    // Fallback to JSON conversion if CSV endpoint is unavailable
    if ((error as any)?.response && (error as any).response.status !== 404) {
      throw error instanceof Error ? error : new Error('Failed to download report');
    }
  }

  const { data } = await staffApi.get(config.fallbackPath, {
    params: config.fallbackParams(filters),
  });
  const csv = config.fallbackToCsv(data);
  if (!csv) {
    throw new Error('Report had no data to export');
  }
  triggerDownload(csv, fileName);
};
