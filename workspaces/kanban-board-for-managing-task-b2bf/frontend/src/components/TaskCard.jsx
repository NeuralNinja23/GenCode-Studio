import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { Edit, Trash2, Calendar, User, Tag, Clock, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { mockAssignees, mockTags } from '../data/mock';

const statusOptions = ["Backlog", "In Progress", "Review", "Done"];
const priorityOptions = ["Low", "Medium", "High"];

export default function TaskCard({ task, onDelete, onUpdate }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTask, setEditedTask] = useState(task);

  const getPriorityBadgeVariant = (priority) => {
    switch (priority) {
      case 'High': return 'destructive';
      case 'Medium': return 'default';
      case 'Low': return 'outline';
      default: return 'secondary';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Done': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'In Progress': return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'Review': return <AlertCircle className="h-4 w-4 text-orange-500" />;
      case 'Backlog': return <XCircle className="h-4 w-4 text-red-500" />;
      default: return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const isOverdue = task.dueDate && new Date(task.dueDate) < new Date() && task.status !== 'Done';

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setEditedTask(prev => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (name, value) => {
    setEditedTask(prev => ({
      ...prev,
      [name]: name === 'assignee' ? mockAssignees.find(a => a.id === value) : value
    }));
  };

  const handleTagToggle = (tagId) => {
    setEditedTask(prev => {
      const currentTags = prev.tags || [];
      const tagObject = mockTags.find(t => t.id === tagId);
      if (!tagObject) return prev;

      if (currentTags.some(t => t.id === tagId)) {
        return { ...prev, tags: currentTags.filter(t => t.id !== tagId) };
      } else {
        return { ...prev, tags: [...currentTags, tagObject] };
      }
    });
  };

  const handleSave = () => {
    onUpdate(editedTask);
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <Card className="w-full shadow-md p-4 space-y-4">
        <div className="space-y-4">
          <Label htmlFor="edit-title">Title</Label>
          <Input
            id="edit-title"
            name="title"
            value={editedTask.title}
            onChange={handleInputChange}
            placeholder="Task title"
          />
        </div>
        <div className="space-y-4">
          <Label htmlFor="edit-description">Description</Label>
          <Textarea
            id="edit-description"
            name="description"
            value={editedTask.description}
            onChange={handleInputChange}
            placeholder="Task description"
          />
        </div>
        <div className="space-y-4">
          <Label htmlFor="edit-status">Status</Label>
          <Select value={editedTask.status} onValueChange={(value) => handleSelectChange('status', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select status" />
            </SelectTrigger>
            <SelectContent>
              {statusOptions.map(status => (
                <SelectItem key={status} value={status}>{status}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-4">
          <Label htmlFor="edit-priority">Priority</Label>
          <Select value={editedTask.priority} onValueChange={(value) => handleSelectChange('priority', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select priority" />
            </SelectTrigger>
            <SelectContent>
              {priorityOptions.map(priority => (
                <SelectItem key={priority} value={priority}>{priority}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-4">
          <Label htmlFor="edit-assignee">Assignee</Label>
          <Select value={editedTask.assignee?.id || ''} onValueChange={(value) => handleSelectChange('assignee', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select assignee" />
            </SelectTrigger>
            <SelectContent>
              {mockAssignees.map(assignee => (
                <SelectItem key={assignee.id} value={assignee.id}>{assignee.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-4">
          <Label htmlFor="edit-dueDate">Due Date</Label>
          <Input
            id="edit-dueDate"
            name="dueDate"
            type="date"
            value={editedTask.dueDate}
            onChange={handleInputChange}
          />
        </div>
        <div className="space-y-4">
          <Label>Tags</Label>
          <div className="flex flex-wrap gap-4">
            {mockTags.map(tag => (
              <Button
                key={tag.id}
                variant={(editedTask.tags || []).some(t => t.id === tag.id) ? 'default' : 'outline'}
                onClick={() => handleTagToggle(tag.id)}
              >
                {tag.name}
              </Button>
            ))}
          </div>
        </div>
        <CardFooter className="flex justify-end gap-4 p-0 pt-4">
          <Button variant="outline" onClick={() => setIsEditing(false)}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="w-full shadow-md hover:shadow-lg transition-shadow duration-200 ease-in-out">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div className="space-y-4">
          <CardTitle className="text-lg font-semibold">{task.title}</CardTitle>
          <CardDescription className="text-sm text-muted-foreground line-clamp-2">
            {task.description}
          </CardDescription>
        </div>
        <div className="flex items-center gap-4">
          <Button data-testid="edit-task-button" variant="ghost" size="icon" onClick={() => setIsEditing(true)}>
            <Edit className="h-4 w-4" />
          </Button>
          <Button data-testid="delete-task-button" variant="ghost" size="icon" onClick={() => onDelete(task.id)}>
            <Trash2 className="h-4 w-4 text-red-500" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="flex items-center gap-4">
          {getStatusIcon(task.status)}
          <span className="font-medium">{task.status}</span>
          <Badge variant={getPriorityBadgeVariant(task.priority)}>{task.priority}</Badge>
        </div>
        {task.assignee && (
          <div className="flex items-center gap-4">
            <Avatar className="h-6 w-6">
              <AvatarImage src={task.assignee.avatar} alt={task.assignee.name} />
              <AvatarFallback>{task.assignee.name.charAt(0)}</AvatarFallback>
            </Avatar>
            <span>{task.assignee.name}</span>
          </div>
        )}
        {task.dueDate && (
          <div className={`flex items-center gap-4 ${isOverdue ? 'text-red-500' : 'text-muted-foreground'}`}>
            <Calendar className="h-4 w-4" />
            <span>Due: {new Date(task.dueDate).toLocaleDateString()} {isOverdue && '(Overdue)'}</span>
          </div>
        )}
        {(task.tags && task.tags.length > 0) && (
          <div className="flex flex-wrap gap-4">
            {task.tags.map(tag => (
              <Badge key={tag.id} className={`${tag.color} text-white`}><Tag className="h-3 w-3 mr-1"/>{tag.name}</Badge>
            ))}
          </div>
        )}
        {task.subtasks && task.subtasks.total > 0 && (
          <div className="space-y-4">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Subtasks</span>
              <span>{task.subtasks.completed}/{task.subtasks.total}</span>
            </div>
            <Progress value={(task.subtasks.completed / task.subtasks.total) * 100} className="h-2" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
