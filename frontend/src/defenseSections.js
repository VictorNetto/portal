// The defense team's sections (D17): one page each in the left rail. Shared by the router,
// the rail, the list and the vulnerability page so they agree on names and paths.

// Where a vulnerability stands for the defense team.
export const SECTIONS = [
  {
    key: 'new', path: '/defense/new',
    test: (v) => v.status === 'sent' && !v.accepted_at,
    icon: 'M4 13h4l2 3h4l2-3h4M4 13l2.5-8h11l2.5 8v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z',            // inbox tray
  },
  {
    key: 'awaitingRvs', path: '/defense/awaiting-rvs',
    test: (v) => v.status === 'sent' && !!v.accepted_at,
    icon: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0zM12 7v5l3 2',                                     // clock
  },
  {
    key: 'inProgress', path: '/defense/in-progress',
    test: (v) => ['fixing', 'retesting'].includes(v.status),
    icon: 'M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z', // wrench
  },
  {
    key: 'fixed', path: '/defense/fixed',
    test: (v) => v.status === 'fixed',
    icon: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0zM8 12.5l2.8 2.8L16 9.5',                           // check in a circle
  },
  {
    key: 'riskAccepted', path: '/defense/risk-accepted',
    test: (v) => v.status === 'risk_accepted',
    icon: 'M12 3.5 2.5 20h19zM12 10v4.5M12 17.2h.01',                                              // warning triangle
  },
]

export const sectionOf = (v) => SECTIONS.find((s) => s.test(v)) || SECTIONS[0]
