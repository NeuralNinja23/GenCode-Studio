import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { Calendar, User, Tag, Flag, Trash2, Edit, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

const TaskCard = ({ task, onDelete, onUpdate }) => {
  const today = new Date();
  const dueDate = task.dueDate ? new Date(task.dueDate) : null;
  const isOverdue = dueDate && dueDate < today && task.status !== 'done';

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'high':
        return <Badge variant="destructive" className="bg-red-500 hover:bg-red-600">High</Badge>;
      case 'medium':
        return <Badge variant="warning" className="bg-orange-500 hover:bg-orange-600">Medium</Badge>;
      case 'low':
        return <Badge variant="secondary" className="bg-gray-500 hover:bg-gray-600">Low</Badge>;
      default:
        return <Badge variant="secondary">Medium</Badge>;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'done':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'in-progress':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'review':
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
      case 'backlog':
      default:
        return <ListTodo className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const subtaskProgress = task.subtasks.total > 0
    ? Math.round((task.subtasks.completed / task.subtasks.total) * 100)
    : 0;

  return (
    <Card className="bg-card shadow-sm hover:shadow-md transition-shadow duration-200 border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">{task.title}</CardTitle>
          {task.assignee && (
            <Avatar className="h-6 w-6">
              <AvatarImage src={task.assignee.avatar} alt={task.assignee.name} />
              <AvatarFallback>{task.assignee.name.charAt(0)}</AvatarFallback>
            </Avatar>
          )}
        </div>
        <CardDescription className="text-sm text-muted-foreground line-clamp-2">{task.description}</CardDescription>
      </CardHeader>
      <CardContent className="text-sm space-y-4 pb-2">
        <div className="flex items-center gap-4">
          <Flag className="h-4 w-4 text-muted-foreground" />
          {getPriorityBadge(task.priority)}
        </div>
        {dueDate && (
          <div className={`flex items-center gap-4 ${isOverdue ? 'text-red-500' : 'text-muted-foreground'}`}>
            <Calendar className="h-4 w-4" />
            <span>Due: {dueDate.toLocaleDateString()} {isOverdue && <span className="font-medium">(Overdue)</span>}</span>
          </div>
        )}
        {task.labels && task.labels.length > 0 && (
          <div className="flex flex-wrap gap-4">
            {task.labels.map(label => (
              <Badge key={label.id} className={`${label.color} text-white`} data-testid={`task-tag-${label.name.toLowerCase()}`}>
                {label.name}
              </Badge>
            ))}
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
      <CardFooter className="flex justify-end gap-4 pt-2">
        <Button variant="ghost" size="icon" onClick={onUpdate} data-testid="edit-task-button">
          <Edit className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={onDelete} data-testid="delete-task-button">
          <Trash2 className="h-4 w-4 text-red-500" />
        </Button>
      </CardFooter>
    </Card>
  );
};

export default TaskCard;