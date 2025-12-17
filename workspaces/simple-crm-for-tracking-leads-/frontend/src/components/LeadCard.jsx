import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Edit, Trash2, Mail, Phone, Building, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
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

export default function LeadCard({ lead, onEdit, onDelete }) {
  return (
    <Card className={`${ui.card} w-full max-w-sm`}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          {lead.name}
          <Badge variant={getStatusVariant(lead.status)} className="flex items-center gap-4">
            {getStatusIcon(lead.status)} {lead.status}
          </Badge>
        </CardTitle>
        <CardDescription className="flex items-center gap-4 text-sm text-muted-foreground">
          <Building className="h-4 w-4" /> {lead.company}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="flex items-center gap-4">
          <Mail className="h-4 w-4 text-muted-foreground" /> {lead.email}
        </div>
        <div className="flex items-center gap-4">
          <Phone className="h-4 w-4 text-muted-foreground" /> {lead.phone}
        </div>
        <div className="text-xs text-muted-foreground">
          Created: {new Date(lead.created_at).toLocaleDateString()}
        </div>
        <div className="text-xs text-muted-foreground">
          Last Contacted: {new Date(lead.last_contacted).toLocaleDateString()}
        </div>
      </CardContent>
      <CardFooter className="flex justify-end gap-4">
        <Button data-testid={`edit-Lead-button-${lead.id}`} variant="outline" size="sm" onClick={() => onEdit(lead.id)}>
          <Edit className="h-4 w-4 mr-1" /> Edit
        </Button>
        <Button data-testid={`delete-Lead-button-${lead.id}`} variant="destructive" size="sm" onClick={() => onDelete(lead.id)}>
          <Trash2 className="h-4 w-4 mr-1" /> Delete
        </Button>
      </CardFooter>
    </Card>
  );
}
