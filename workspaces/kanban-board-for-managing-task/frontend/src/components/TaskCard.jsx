import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { format, isPast } from 'date-fns';
import { Trash2, Edit, CheckCircle, XCircle, Clock, AlertCircle, ListTodo, CalendarDays, User, Tag } from 'lucide-react';

export function TaskCard({ task, onDelete, onUpdateStatus }) {
  const getStatusBadge = (status) => {
    switch (status) {
      case 'backlog':
        return <Badge variant="outline" className="bg-gray-100 text-gray-700"><ListTodo className="mr-1 h-3 w-3" /> Backlog</Badge>;
      case 'in-progress':
        return <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-200"><Clock className="mr-1 h-3 w-3" /> In Progress</Badge>;
      case 'review':
        return <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-200"><AlertCircle className="mr-1 h-3 w-3" /> Review</Badge>;
      case 'done':
        return <Badge className="bg-green-100 text-green-700 hover:bg-green-200"><CheckCircle className="mr-1 h-3 w-3" /> Done</Badge>;
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'high':
        return <Badge variant="destructive" className="bg-red-100 text-red-700 hover:bg-red-200">High</Badge>;
      case 'medium':
        return <Badge variant="warning" className="bg-yellow-100 text-yellow-700 hover:bg-yellow-200">Medium</Badge>;
      case 'low':
        return <Badge variant="secondary" className="bg-gray-100 text-gray-700 hover:bg-gray-200">Low</Badge>;
      default:
        return null;
    }
  };

  const isTaskOverdue = task.dueDate && isPast(new Date(task.dueDate)) && task.status !== 'done';
  const subtaskProgress = task.subtasks.total > 0 ? (task.subtasks.completed / task.subtasks.total) * 100 : 0;

  return (
    <Card className="bg-card shadow-sm hover:shadow-md transition-shadow duration-200">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold flex justify-between items-start">
          {task.title}
          <div className="flex gap-4">
            {getPriorityBadge(task.priority)}
          </div>
        </CardTitle>
        <div className="flex flex-wrap gap-4 mt-1">
          {getStatusBadge(task.status)}
          {task.labels.map(label => (
            <Badge key={label} variant="outline" className="bg-blue-50/50 text-blue-700 hover:bg-blue-100/50 text-xs font-normal">
              <Tag className="mr-1 h-3 w-3" />{label}
            </Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground space-y-4">
        <p className="line-clamp-2">{task.description}</p>
        {task.dueDate && (
          <div className={`flex items-center gap-4 text-xs ${isTaskOverdue ? 'text-red-500 font-medium' : 'text-muted-foreground'}`}>
            <CalendarDays className="h-3 w-3" />
            <span>Due: {format(new Date(task.dueDate), 'MMM dd, yyyy')} {isTaskOverdue && '(Overdue)'}</span>
          </div>
        )}
        {task.subtasks.total > 0 && (
          <div className="space-y-4">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Subtasks</span>
              <span>{task.subtasks.completed}/{task.subtasks.total}</span>
            </div>
            <Progress value={subtaskProgress} className="h-2" />
          </div>
        )}
      </CardContent>
      <CardFooter className="flex justify-between items-center pt-2">
        <div className="flex items-center gap-4">
          {task.assignee ? (
            <Avatar className="h-6 w-6">
              <AvatarImage src={task.assignee.avatar} alt={task.assignee.name} />
              <AvatarFallback className="text-xs"><User className="h-4 w-4"/></AvatarFallback>
            </Avatar>
          ) : (
            <Avatar className="h-6 w-6 bg-muted">
              <AvatarFallback className="text-xs"><User className="h-4 w-4"/></AvatarFallback>
            </Avatar>
          )}
          <span className="text-xs text-muted-foreground">{task.assignee?.name || 'Unassigned'}</span>
        </div>
        <div className="flex gap-4">
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" data-testid={`edit-task-button-${task.id}`}>
            <Edit className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive hover:text-destructive" onClick={() => onDelete(task.id)} data-testid="delete-task-button">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
