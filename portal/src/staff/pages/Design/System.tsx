import Badge from '../../../ui/Badge';
import Button from '../../../ui/Button';
import { Card, CardHeader } from '../../../ui/Card';
import { Input, Label, Select, Textarea } from '../../../ui/Inputs';
import Page from '../../../ui/Page';
import Table from '../../../ui/Table';

export default function DesignSystem() {
  return (
    <Page>
      <Page.Header title="Design System" sub="Preview of shared UI primitives" />

      <Card>
        <CardHeader title="Buttons" />
        <div className="flex flex-wrap gap-2">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
        </div>
      </Card>

      <Card>
        <CardHeader title="Badges" />
        <div className="flex gap-2">
          <Badge>Default</Badge>
          <Badge variant="success">Success</Badge>
          <Badge variant="info">Info</Badge>
          <Badge variant="danger">Danger</Badge>
        </div>
      </Card>

      <Card>
        <CardHeader title="Inputs" />
        <div className="grid gap-3 md:grid-cols-3">
          <Label>
            <span>Text</span>
            <Input placeholder="Type here" />
          </Label>
          <Label>
            <span>Select</span>
            <Select>
              <option>One</option>
              <option>Two</option>
            </Select>
          </Label>
          <Label>
            <span>Textarea</span>
            <Textarea rows={3} />
          </Label>
        </div>
      </Card>

      <Card>
        <CardHeader title="Table" />
        <div className="overflow-auto">
          <Table>
            <thead>
              <tr>
                <th className="px-3 py-2 text-left text-slate-500">Column A</th>
                <th className="px-3 py-2 text-left text-slate-500">Column B</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t">
                <td className="px-3 py-2">Hello</td>
                <td className="px-3 py-2">World</td>
              </tr>
            </tbody>
          </Table>
        </div>
      </Card>
    </Page>
  );
}
