import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Search, User, Tag, ChevronDown, Loader2, Edit, Trash2, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { mockTasks, mockAssignees, mockTags } from '../data/mock';
import TaskCard from '../components/TaskCard';

const statusOptions = ["Backlog", "In Progress", "Review", "Done"];
const priorityOptions = ["Low", "Medium", "High"];

export default function TasksPage() {
  const [tasks, setTasks] = useState(mockTasks);
  const [filteredTasks, setFilteredTasks] = useState(mockTasks);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterAssignee, setFilterAssignee] = useState('all');
  const [filterTag, setFilterTag] = useState('all');
  const [showAddTaskForm, setShowAddTaskForm] = useState(false);
  const [newTaskForm, setNewTaskForm] = useState({
    title: '',
    description: '',
    status: 'Backlog',
    priority: 'Medium',
    assignee: null,
    dueDate: '',
    tags: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let currentTasks = tasks;

    if (searchTerm) {
      currentTasks = currentTasks.filter(task =>
        task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (filterAssignee !== 'all') {
      currentTasks = currentTasks.filter(task => task.assignee?.id === filterAssignee);
    }

    if (filterTag !== 'all') {
      currentTasks = currentTasks.filter(task => task.tags.some(tag => tag.id === filterTag));
    }

    setFilteredTasks(currentTasks);
  }, [tasks, searchTerm, filterAssignee, filterTag]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewTaskForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (name, value) => {
    setNewTaskForm(prev => ({
      ...prev,
      [name]: name === 'assignee' ? mockAssignees.find(a => a.id === value) : value
    }));
  };

  const handleTagToggle = (tagId) => {
    setNewTaskForm(prev => {
      const currentTags = prev.tags;
      const tagObject = mockTags.find(t => t.id === tagId);
      if (!tagObject) return prev;

      if (currentTags.some(t => t.id === tagId)) {
        return { ...prev, tags: currentTags.filter(t => t.id !== tagId) };
      } else {
        return { ...prev, tags: [...currentTags, tagObject] };
      }
    });
  };

  const handleAddTask = () => {
    if (!newTaskForm.title.trim()) {
      setError("Task title cannot be empty.");
      return;
    }
    setError(null);
    setLoading(true);
    setTimeout(() => {
      const newTask = {
        id: String(Date.now()),
        ...newTaskForm,
        created_at: new Date().toISOString(),
        subtasks: { completed: 0, total: 0 },
        assignee: newTaskForm.assignee || null,
        tags: newTaskForm.tags || []
      };
      setTasks(prev => [...prev, newTask]);
      setNewTaskForm({
        title: '', description: '', status: 'Backlog', priority: 'Medium',
        assignee: null, dueDate: '', tags: []
      });
      setShowAddTaskForm(false);
      setLoading(false);
    }, 500);
  };

  const handleDeleteTask = (id) => {
    setLoading(true);
    setTimeout(() => {
      setTasks(prev => prev.filter(task => task.id !== id));
      setLoading(false);
    }, 300);
  };

  const handleUpdateTask = (updatedTask) => {
    setLoading(true);
    setTimeout(() => {
      setTasks(prev => prev.map(task => (task.id === updatedTask.id ? updatedTask : task)));
      setLoading(false);
    }, 300);
  };

  return (
    <main data-testid="page-root" className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex justify-between items-center">
          <h1 data-testid="page-title" className="text-4xl font-extrabold tracking-tight lg:text-5xl">
            Task Management Board
          </h1>
          <Button
            data-testid="create-task-button"
            onClick={() => setShowAddTaskForm(true)}
            className="flex items-center gap-4"
          >
            <Plus className="h-4 w-4" /> Add New Task
          </Button>
        </div>

        {showAddTaskForm && (
          <Card className="p-6 space-y-4">
            <CardHeader>
              <CardTitle>Create New Task</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-4">
                <Label htmlFor="title">Title</Label>
                <Input
                  data-testid="new-task-title-input"
                  id="title"
                  name="title"
                  value={newTaskForm.title}
                  onChange={handleInputChange}
                  placeholder="Task title"
                />
              </div>
              <div className="space-y-4">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  data-testid="new-task-description-input"
                  id="description"
                  name="description"
                  value={newTaskForm.description}
                  onChange={handleInputChange}
                  placeholder="Task description"
                />
              </div>
              <div className="space-y-4">
                <Label htmlFor="status">Status</Label>
                <Select
                  value={newTaskForm.status}
                  onValueChange={(value) => handleSelectChange('status', value)}
                >
                  <SelectTrigger data-testid="new-task-status-select">
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
                <Label htmlFor="priority">Priority</Label>
                <Select
                  value={newTaskForm.priority}
                  onValueChange={(value) => handleSelectChange('priority', value)}
                >
                  <SelectTrigger data-testid="new-task-priority-select">
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
                <Label htmlFor="assignee">Assignee</Label>
                <Select
                  value={newTaskForm.assignee?.id || ''}
                  onValueChange={(value) => handleSelectChange('assignee', value)}
                >
                  <SelectTrigger data-testid="new-task-assignee-select">
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
                <Label htmlFor="dueDate">Due Date</Label>
                <Input
                  data-testid="new-task-due-date-input"
                  id="dueDate"
                  name="dueDate"
                  type="date"
                  value={newTaskForm.dueDate}
                  onChange={handleInputChange}
                />
              </div>
              <div className="space-y-4 col-span-full">
                <Label>Tags</Label>
                <div className="flex flex-wrap gap-4">
                  {mockTags.map(tag => (
                    <Button
                      key={tag.id}
                      variant={newTaskForm.tags.some(t => t.id === tag.id) ? 'default' : 'outline'}
                      onClick={() => handleTagToggle(tag.id)}
                      data-testid={`new-task-tag-${tag.name.toLowerCase()}`}
                    >
                      {tag.name}
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-end gap-4">
              <Button variant="outline" onClick={() => setShowAddTaskForm(false)}>Cancel</Button>
              <Button data-testid="add-task-submit-button" onClick={handleAddTask} disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />} Add Task
              </Button>
            </CardFooter>
            {error && <p data-testid="error-message" className="text-red-500 text-sm mt-2">{error}</p>}
          </Card>
        )}

        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              data-testid="task-search-input"
              placeholder="Search tasks..."
              className="pl-9"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Select value={filterAssignee} onValueChange={setFilterAssignee}>
            <SelectTrigger data-testid="assignee-filter-select" className="w-[180px]">
              <User className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Filter by Assignee" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Assignees</SelectItem>
              {mockAssignees.map(assignee => (
                <SelectItem key={assignee.id} value={assignee.id}>{assignee.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={filterTag} onValueChange={setFilterTag}>
            <SelectTrigger data-testid="tag-filter-select" className="w-[180px]">
              <Tag className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Filter by Tag" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Tags</SelectItem>
              {mockTags.map(tag => (
                <SelectItem key={tag.id} value={tag.id}>{tag.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {loading && (
          <div data-testid="loading-indicator" className="flex justify-center items-center h-32">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {error && !loading && (
          <div data-testid="error-message" className="p-4 bg-red-100 text-red-700 rounded-md">
            <AlertCircle className="inline h-5 w-5 mr-2" />
            {error}
          </div>
        )}

        {!loading && filteredTasks.length === 0 && (
          <p className="text-center text-muted-foreground">No tasks found matching your criteria.</p>
        )}

        <div data-testid="task-list" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {!loading && filteredTasks.map(task => (
            <TaskCard
              key={task.id}
              task={task}
              onDelete={handleDeleteTask}
              onUpdate={handleUpdateTask}
            />
          ))}
        </div>
      </div>
    </main>
  );
}
