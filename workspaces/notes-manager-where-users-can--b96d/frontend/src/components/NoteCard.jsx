import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Edit, Trash2, CheckCircle, Clock } from 'lucide-react';

export function NoteCard({ note, onEdit, onDelete }) {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'Active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'Draft':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'Active':
        return 'bg-green-600/20 text-green-400';
      case 'Draft':
        return 'bg-yellow-600/20 text-yellow-400';
      default:
        return '';
    }
  };

  return (
    <Card className="bg-card border-border shadow-md hover:shadow-lg transition-shadow duration-200 ease-in-out flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xl font-semibold line-clamp-1">{note.title}</CardTitle>
        <Badge className={getStatusBadgeClass(note.status)}>
          {getStatusIcon(note.status)} <span className="ml-1">{note.status}</span>
        </Badge>
      </CardHeader>
      <CardContent className="flex-grow space-y-4">
        <p className="text-muted-foreground text-sm line-clamp-3">{note.content}</p>
        <div className="flex justify-end gap-4 pt-4">
          <Button
            data-testid="edit-note-button"
            variant="outline"
            size="sm"
            onClick={() => onEdit(note)}
            className="text-primary hover:bg-primary/10 border-primary/50"
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            data-testid="delete-note-button"
            variant="destructive"
            size="sm"
            onClick={() => onDelete(note.id)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
