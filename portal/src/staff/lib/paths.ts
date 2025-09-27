export const P = {
  owners: {
    list: "/owners",
    byId: (id: string) => `/owners/${id}`,
    pets: (id: string) => `/owners/${id}/pets`,
  },
  pets: {
    list: "/pets",
    byId: (id: string) => `/pets/${id}`,
    vax: (id: string) => `/pets/${id}/vaccinations`,
  },
  reservations: {
    base: "/reservations",
  },
  grooming: {
    appts: "/grooming/appointments",
    availability: "/grooming/availability",
  },
  invoices: {
    list: "/invoices",
    byId: (id: string) => `/invoices/${id}`,
  },
  payments: {
    list: "/payments",
  },
  waitlist: {
    base: "/waitlist",
  },
  reportsMax: {
    revenue: (a: string, b: string) =>
      `/reports-max/revenue-by-date.csv?date_from=${a}&date_to=${b}`,
    occupancy: (a: string, b: string) =>
      `/reports-max/occupancy.csv?date_from=${a}&date_to=${b}`,
    payments: (a: string, b: string) =>
      `/reports-max/payments-by-method.csv?date_from=${a}&date_to=${b}`,
    deposits: (a: string, b: string) =>
      `/reports-max/deposits.csv?date_from=${a}&date_to=${b}`,
    commissions: (a: string, b: string) =>
      `/reports-max/grooming-commissions.csv?date_from=${a}&date_to=${b}`,
    tips: (a: string, b: string) =>
      `/reports-max/tips-by-user-and-day.csv?date_from=${a}&date_to=${b}`,
  },
  staff: {
    timeclock: "/timeclock",
    tips: "/tips",
    commissions: "/commissions",
    payroll: "/payroll/periods",
  },
  admin: {
    users: "/users",
    locations: "/locations",
    services: "/services",
    pricing: "/pricing-rules",
    capacity: "/capacity",
    tax: "/tax-rates",
    integrations: "/integrations",
  },
};
