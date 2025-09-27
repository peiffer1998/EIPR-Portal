import type { ReactNode } from 'react';

import Toolbar from './Toolbar';

interface PageComponent {
  (props: { children: ReactNode }): JSX.Element;
  Header: (props: { title: string; sub?: string; actions?: ReactNode }) => JSX.Element;
}

const Page = (({ children }: { children: ReactNode }) => <div className="grid gap-3">{children}</div>) as PageComponent;

Page.Header = function PageHeader({ title, sub, actions }: { title: string; sub?: string; actions?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <div className="page-title">{title}</div>
        {sub ? <div className="page-sub">{sub}</div> : null}
      </div>
      {actions ? <Toolbar>{actions}</Toolbar> : null}
    </div>
  );
};

export default Page;
