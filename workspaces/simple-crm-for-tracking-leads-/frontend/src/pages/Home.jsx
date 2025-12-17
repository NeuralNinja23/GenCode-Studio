import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Plus, Users, TrendingUp, DollarSign, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { mockLeads, mockLeadStats } from '../data/mock';
import { ui } from '../design/theme';

const StatsCard = ({ title, value, icon: Icon, description, colorClass }) => (
  <Card className={ui.card}>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      {Icon && <Icon className={`h-4 w-4 ${colorClass || 'text-muted-foreground'}`} />}
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
      {description && <p className="text-xs text-muted-foreground">{description}</p>}
    </CardContent>
  </Card>
);

const getStatusIcon = (status) => {
  switch (status) {
    case 'New':
      return <Clock className="h-4 w-4 text-blue-500" />;
    case 'Contacted':
      return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    case 'Qualified':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'Won':
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    case 'Lost':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return null;
  }
};

export default function Home() {
  const recentLeads = mockLeads.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5);

  return (
    <main data-testid="page-root" className={`${ui.pageRoot} p-6`}>
      <div className="max-w-7xl mx-auto space-y-8">
        <h1 data-testid="page-title" className="text-3xl font-bold">CRM Dashboard Overview</h1>
        <p className="text-muted-foreground">Manage your leads efficiently and get a quick overview of your sales pipeline.</p>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <StatsCard
            title="Total Leads"
            value={mockLeadStats.total}
            icon={Users}
            colorClass="text-blue-500"
            description="Overall leads in your system"
          />
          <StatsCard
            title="New Leads"
            value={mockLeadStats.New}
            icon={Clock}
            colorClass="text-blue-500"
            description="Leads awaiting first contact"
          />
          <StatsCard
            title="Qualified Leads"
            value={mockLeadStats.Qualified}
            icon={CheckCircle}
            colorClass="text-green-500"
            description="Leads ready for next stage"
          />
          <StatsCard
            title="Won Leads"
            value={mockLeadStats.Won}
            icon={DollarSign}
            colorClass="text-green-600"
            description="Successfully converted leads"
          />
          <StatsCard
            title="Lost Leads"
            value={mockLeadStats.Lost}
            icon={XCircle}
            colorClass="text-red-500"
            description="Leads that did not convert"
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <Card className={`${ui.card} lg:col-span-4`}>
            <CardHeader>
              <CardTitle>Recent Leads</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentLeads.length > 0 ? (
                    recentLeads.map((lead) => (
                      <TableRow key={lead.id}>
                        <TableCell className="font-medium">{lead.name}</TableCell>
                        <TableCell>{lead.company}</TableCell>
                        <TableCell className="flex items-center gap-4">
                          {getStatusIcon(lead.status)} {lead.status}
                        </TableCell>
                        <TableCell>{new Date(lead.created_at).toLocaleDateString()}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                        No recent leads.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card className={`${ui.card} lg:col-span-3 flex flex-col justify-between`}>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button data-testid="create-Lead-button" className={`${ui.primaryButton} w-full`}>
                <Plus className="mr-2 h-4 w-4" /> Add New Lead
              </Button>
              <Button variant="outline" className="w-full">
                <TrendingUp className="mr-2 h-4 w-4" /> View Reports
              </Button>
              <Button variant="outline" className="w-full">
                <Users className="mr-2 h-4 w-4" /> Manage Customers
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
