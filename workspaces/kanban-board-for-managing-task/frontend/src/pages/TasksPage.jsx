import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Plus, Search, Filter, Users, Tag, Loader2, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { TaskCard } from '../components/TaskCard';
import { mockTasks, mockKanbanColumns, mockAssignees, mockTags } from '../data/mock';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

function TasksPage() {
  const [tasks, setTasks] = useState(mockTasks);
  const [newTaskForm, setNewTaskForm] = useState({ title: '', description: '', status: 'backlog', priority: 'medium', assignee: null, dueDate: '' });
  const [filterAssignee, setFilterAssignee] = useState(null);
  const [filterTag, setFilterTag] = useState(null);
  const [loading, setLoading] = useState(false); // Placeholder for loading state
  const [error, setError] = useState(null); // Placeholder for error state

  const handleCreateTask = () => {
    if (!newTaskForm.title) return;

    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      const newTask = {
        id: `task-${Date.now()}`,
        ...newTaskForm,
        assignee: newTaskForm.assignee || mockAssignees[0], // Default assignee
        dueDate: newTaskForm.dueDate || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // Default 7 days from now
        labels: [], // No labels on creation for simplicity
        subtasks: { completed: 0, total: 0 },
        created_at: new Date().toISOString(),
      };
      setTasks(prevTasks => [...prevTasks, newTask]);
      setNewTaskForm({ title: '', description: '', status: 'backlog', priority: 'medium', assignee: null, dueDate: '' });
      setLoading(false);
    }, 500);
  };

  const handleDeleteTask = (id) => {
    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setTasks(prevTasks => prevTasks.filter(task => task.id !== id));
      setLoading(false);
    }, 300);
  };

  const handleUpdateTaskStatus = (taskId, newStatus) => {
    setTasks(prevTasks =>
      prevTasks.map(task =>
        task.id === taskId ? { ...task, status: newStatus } : task
      )
    );
  };

  const filteredTasks = tasks.filter(task => {
    const matchesAssignee = filterAssignee ? task.assignee?.id === filterAssignee.id : true;
    const matchesTag = filterTag ? task.labels.includes(filterTag) : true;
    return matchesAssignee && matchesTag;
  });

  const getColumnTasks = (status) => {
    return filteredTasks.filter(task => task.status === status);
  };

  // Placeholder for ProjectSidebar
  const ProjectSidebar = () => (
    <aside className="w-64 border-r bg-card p-4 flex flex-col gap-4">
      <h2 className="text-xl font-semibold">Projects</h2>
      <Button variant="ghost" className="justify-start" data-testid="project-sidebar-button-1">Website Redesign</Button>
      <Button variant="ghost" className="justify-start" data-testid="project-sidebar-button-2">Mobile App</Button>
      <Button variant="ghost" className="justify-start" data-testid="project-sidebar-button-3">API Integration</Button>
      <Button variant="outline" className="mt-auto" data-testid="add-project-button"><Plus className="mr-2 h-4 w-4" /> Add Project</Button>
    </aside>
  );

  return (
    <div data-testid="page-root" className="flex h-screen bg-background text-foreground">
      <ProjectSidebar />
      <main className="flex-1 overflow-hidden flex flex-col">
        <header className="border-b p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-card">
          <div>
            <h1 data-testid="page-title" className="text-3xl font-bold">Task Board</h1>
            <p className="text-muted-foreground">Manage your tasks across different stages.</p>
          </div>
          <div className="flex flex-wrap gap-4">
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" data-testid="filter-assignee-button">
                  <Users className="mr-2 h-4 w-4" />
                  {filterAssignee ? filterAssignee.name : 'Filter by Assignee'}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[200px] p-0">
                <Command>
                  <CommandInput placeholder="Search assignee..." />
                  <CommandList>
                    <CommandEmpty>No assignees found.</CommandEmpty>
                    <CommandGroup>
                      {mockAssignees.map((assignee) => (
                        <CommandItem
                          key={assignee.id}
                          onSelect={() => {
                            setFilterAssignee(assignee);
                          }}
                          className="cursor-pointer"
                        >
                          <img src={assignee.avatar} alt={assignee.name} className="w-6 h-6 rounded-full mr-2" />
                          {assignee.name}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    {filterAssignee && (
                      <CommandGroup>
                        <CommandItem onSelect={() => setFilterAssignee(null)} className="text-red-500 cursor-pointer">
                          Clear Filter
                        </CommandItem>
                      </CommandGroup>
                    )}
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>

            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" data-testid="filter-tag-button">
                  <Tag className="mr-2 h-4 w-4" />
                  {filterTag ? filterTag : 'Filter by Tag'}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[200px] p-0">
                <Command>
                  <CommandInput placeholder="Search tag..." />
                  <CommandList>
                    <CommandEmpty>No tags found.</CommandEmpty>
                    <CommandGroup>
                      {mockTags.map((tag) => (
                        <CommandItem
                          key={tag}
                          onSelect={() => {
                            setFilterTag(tag);
                          }}
                          className="cursor-pointer"
                        >
                          {tag}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    {filterTag && (
                      <CommandGroup>
                        <CommandItem onSelect={() => setFilterTag(null)} className="text-red-500 cursor-pointer">
                          Clear Filter
                        </CommandItem>
                      </CommandGroup>
                    )}
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>

            <Button data-testid="create-task-button" onClick={handleCreateTask} disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
              Add Task
            </Button>
          </div>
        </header>

        {loading && (
          <div data-testid="loading-indicator" className="p-4 text-center text-muted-foreground flex items-center justify-center">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading tasks...
          </div>
        )}
        {error && (
          <div data-testid="error-message" className="p-4 text-center text-destructive flex items-center justify-center">
            <AlertCircle className="mr-2 h-5 w-5" /> {error}
          </div>
        )}

        <div data-testid="task-list" className="flex-1 overflow-x-auto p-4 flex gap-4">
          {mockKanbanColumns.map(column => (
            <Card key={column.id} className="w-[300px] flex-shrink-0 bg-secondary/30">
              <CardHeader className="border-b pb-3">
                <CardTitle className="flex justify-between items-center text-lg">
                  {column.title}
                  <span className="text-sm font-normal text-muted-foreground">({getColumnTasks(column.id).length})</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3 space-y-4 overflow-y-auto max-h-[calc(100vh-250px)]">
                {getColumnTasks(column.id).map(task => (
                  <TaskCard key={task.id} task={task} onDelete={handleDeleteTask} onUpdateStatus={handleUpdateTaskStatus} />
                ))}
                {/* Quick Add Task Input */}
                <Card className="p-3 bg-card/50 border-dashed border-2 text-muted-foreground">
                  <Input
                    placeholder={`Add new task to ${column.title}...`}
                    value={newTaskForm.status === column.id ? newTaskForm.title : ''}
                    onChange={(e) => setNewTaskForm(prev => ({ ...prev, title: e.target.value, status: column.id }))}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newTaskForm.title && newTaskForm.status === column.id) {
                        handleCreateTask();
                      }
                    }}
                    data-testid={`quick-add-task-input-${column.id}`}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full mt-2"
                    onClick={() => newTaskForm.title && newTaskForm.status === column.id && handleCreateTask()}
                    disabled={!newTaskForm.title || newTaskForm.status !== column.id}
                    data-testid={`quick-add-task-button-${column.id}`}
                  >
                    <Plus className="mr-2 h-4 w-4" /> Add Task
                  </Button>
                </Card>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}

export default TasksPage;
