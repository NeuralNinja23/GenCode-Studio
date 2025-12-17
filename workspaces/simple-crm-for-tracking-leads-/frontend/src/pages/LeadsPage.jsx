import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Plus, Trash2, Edit, Search, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { mockLeads } from '../data/mock';
import { ui } from '../design/theme';

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

const getStatusVariant = (status) => {
  switch (status) {
    case 'New':
      return 'outline';
    case 'Contacted':
      return 'secondary';
    case 'Qualified':
      return 'default';
    case 'Won':
      return 'success'; // Assuming a 'success' variant exists or can be styled
    case 'Lost':
      return 'destructive';
    default:
      return 'default';
  }
};

export default function LeadsPage() {
  const [leads, setLeads] = useState(mockLeads);
  const [searchTerm, setSearchTerm] = useState('');
  const [newLeadName, setNewLeadName] = useState('');
  const [newLeadCompany, setNewLeadCompany] = useState('');

  const filteredLeads = leads.filter(lead =>
    lead.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.status.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCreateLead = () => {
    if (newLeadName.trim() && newLeadCompany.trim()) {
      const newLead = {
        id: Date.now().toString(),
        name: newLeadName.trim(),
        company: newLeadCompany.trim(),
        email: `new.${newLeadName.toLowerCase().replace(/ s/g, '')}@example.com`,
        phone: `+1-555-${Math.floor(Math.random() * 900) + 100}-${Math.floor(Math.random() * 9000) + 1000}`,
        status: "New",
        created_at: new Date().toISOString(),
        last_contacted: new Date().toISOString(),
      };
      setLeads([...leads, newLead]);
      setNewLeadName('');
      setNewLeadCompany('');
    }
  };

  const handleDeleteLead = (id) => {
    setLeads(leads.filter(lead => lead.id !== id));
  };

  // In a real app, you'd have an edit dialog/page
  const handleEditLead = (id) => {
    console.log(`Edit lead with ID: ${id}`);
    // Implement dialog or navigation to edit page
  };

  return (
    <main data-testid="page-root" className={`${ui.pageRoot} p-6`}>
      <div className="max-w-7xl mx-auto space-y-6">
        <h1 data-testid="page-title" className="text-3xl font-bold">Leads Management</h1>
        <p className="text-muted-foreground">Track and manage your potential customers.</p>

        <Card className={ui.card}>
          <CardHeader>
            <CardTitle>Create New Lead</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col md:flex-row gap-4">
            <Input
              data-testid="new-lead-name-input"
              placeholder="Lead Name"
              value={newLeadName}
              onChange={(e) => setNewLeadName(e.target.value)}
              className="flex-1"
            />
            <Input
              data-testid="new-lead-company-input"
              placeholder="Company Name"
              value={newLeadCompany}
              onChange={(e) => setNewLeadCompany(e.target.value)}
              className="flex-1"
            />
            <Button data-testid="create-Lead-button" onClick={handleCreateLead} className={ui.primaryButton}>
              <Plus className="mr-2 h-4 w-4" /> Create Lead
            </Button>
          </CardContent>
        </Card>

        <Card className={ui.card}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-2xl font-bold">All Leads</CardTitle>
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                data-testid="search-leads-input"
                placeholder="Search leads..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8"
              />
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table data-testid="Lead-list">
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLeads.length > 0 ? (
                    filteredLeads.map((lead) => (
                      <TableRow key={lead.id}>
                        <TableCell className="font-medium">{lead.name}</TableCell>
                        <TableCell>{lead.company}</TableCell>
                        <TableCell>{lead.email}</TableCell>
                        <TableCell>{lead.phone}</TableCell>
                        <TableCell>
                          <Badge variant={getStatusVariant(lead.status)} className="flex items-center gap-4 w-fit">
                            {getStatusIcon(lead.status)} {lead.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            data-testid={`edit-Lead-button-${lead.id}`}
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEditLead(lead.id)}
                            className="mr-2"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            data-testid={`delete-Lead-button-${lead.id}`}
                            variant="destructive"
                            size="sm"
                            onClick={() => handleDeleteLead(lead.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                        No leads found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
