import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Trash2, Edit, CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react';

function NoteCard({ note, onDelete, onEdit, loading }) {
  const getStatusBadge = (status) => {
    switch (status) {
      case 'Active':
        return <Badge className="bg-green-500 hover:bg-green-500/80 text-white"><CheckCircle className="mr-1 h-3 w-3" /> Active</Badge>;
      case 'Draft':
        return <Badge className="bg-yellow-500 hover:bg-yellow-500/80 text-white"><Clock className="mr-1 h-3 w-3" /> Draft</Badge>;
      case 'Pending':
        return <Badge className="bg-orange-500 hover:bg-orange-500/80 text-white"><AlertCircle className="mr-1 h-3 w-3" /> Pending</Badge>;
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  const truncatedContent = note.content.length > 150
    ? note.content.substring(0, 147) + '...'
    : note.content;

  return (
    <Card className="bg-card border border-border shadow-lg flex flex-col h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-semibold line-clamp-1">{note.title}</CardTitle>
          {getStatusBadge(note.status)}
        </div>
      </CardHeader>
      <CardContent className="flex-1 text-sm text-muted-foreground space-y-4">
        <p className="line-clamp-3">{truncatedContent}</p>
        <p className="text-xs text-gray-500">Created: {new Date(note.created_at).toLocaleDateString()}</p>
      </CardContent>
      <CardFooter className="flex justify-end gap-4 pt-4">
        <Button
          data-testid="edit-note-button"
          variant="outline"
          size="sm"
          onClick={() => onEdit(note)}
          disabled={loading}
        >
          <Edit className="h-4 w-4" />
          <span className="sr-only">Edit Note</span>
        </Button>
        <Button
          data-testid="delete-note-button"
          variant="destructive"
          size="sm"
          onClick={() => onDelete(note.id)}
          disabled={loading}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          <span className="sr-only">Delete Note</span>
        </Button>
      </CardFooter>
    </Card>
  );
}

export default NoteCard;
