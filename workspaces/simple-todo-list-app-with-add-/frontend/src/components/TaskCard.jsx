import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, Trash2, Clock, AlertCircle } from 'lucide-react';
import { ui } from '../design/theme'; // Assuming this file exists as per instructions

export function TaskCard({ task, onComplete, onDelete }) {
  const getStatusBadge = (status) => {
    switch (status) {
      case 'To Do':
        return (
          <Badge variant="outline" className="bg-blue-100 text-blue-800 hover:bg-blue-100">
            <Clock className="mr-1 h-3 w-3" /> To Do
          </Badge>
        );
      case 'In Progress':
        return (
          <Badge variant="outline" className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
            <AlertCircle className="mr-1 h-3 w-3" /> In Progress
          </Badge>
        );
      case 'Completed':
        return (
          <Badge variant="outline" className="bg-green-100 text-green-800 hover:bg-green-100">
            <CheckCircle className="mr-1 h-3 w-3" /> Completed
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary" className="hover:bg-secondary">
            <Clock className="mr-1 h-3 w-3" /> {status}
          </Badge>
        );
    }
  };

  return (
    <Card className={ui.card}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-semibold">{task.title}</CardTitle>
        {getStatusBadge(task.status)}
      </CardHeader>
      <CardContent className="space-y-4">
        <p className={ui.mutedText}>{task.content || 'No description provided.'}</p>
        <div className="flex justify-end gap-4 pt-2">
          {task.status !== 'Completed' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onComplete(task.id)}
              data-testid={`complete-task-button-${task.id}`}
            >
              <CheckCircle className="mr-2 h-4 w-4" /> Complete
            </Button>
          )}
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onDelete(task.id)}
            data-testid="delete-task-button"
          >
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
