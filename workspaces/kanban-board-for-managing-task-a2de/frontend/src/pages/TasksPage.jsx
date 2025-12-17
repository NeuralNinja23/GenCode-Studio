import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Search, Filter, Loader2, AlertCircle, X } from 'lucide-react';

import { mockColumns, mockTasks, mockAssignees, mockTags } from '../data/mock';
import TaskCard from '../components/TaskCard';

const TasksPage = () => {
  const [columns, setColumns] = useState(mockColumns);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDescription, setNewTaskDescription] = useState('');
  const [newTaskAssigneeId, setNewTaskAssigneeId] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState('medium');
  const [newTaskDueDate, setNewTaskDueDate] = useState('');
  const [newTaskTags, setNewTaskTags] = useState([]);
  const [isAddTaskDialogOpen, setIsAddTaskDialogOpen] = useState(false);
  const [currentColumnIdForNewTask, setCurrentColumnIdForNewTask] = useState('');

  // FIX 1 & 2: Placeholder states for loading and error indicators
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    // Simulate loading data
    setIsLoading(true);
    setTimeout(() => {
      // In a real app, you'd fetch data here
      setColumns(mockColumns.map(col => ({
        ...col,
        tasks: mockTasks.filter(task => task.status === col.id)
      })));
      setIsLoading(false);
      // setIsError(true); // Uncomment to test error state
    }, 1000);
  }, []);

  const handleAddTask = (columnId) => {
    if (!newTaskTitle.trim()) return;

    const newTaskId = `task-${Date.now()}`;
    const assignee = mockAssignees.find(a => a.id === newTaskAssigneeId);
    const selectedTags = mockTags.filter(tag => newTaskTags.includes(tag.id));

    const newTask = {
      id: newTaskId,
      title: newTaskTitle,
      description: newTaskDescription,
      status: columnId,
      priority: newTaskPriority,
      assignee: assignee || null,
      dueDate: newTaskDueDate || null,
      labels: selectedTags,
      subtasks: { completed: 0, total: 0 },
      created_at: new Date().toISOString(),
    };

    setColumns(prevColumns =>
      prevColumns.map(col =>
        col.id === columnId ? { ...col, tasks: [...col.tasks, newTask] } : col
      )
    );

    // Reset form
    setNewTaskTitle('');
    setNewTaskDescription('');
    setNewTaskAssigneeId('');
    setNewTaskPriority('medium');
    setNewTaskDueDate('');
    setNewTaskTags([]);
    setIsAddTaskDialogOpen(false);
  };

  const handleDeleteTask = (taskId, columnId) => {
    setColumns(prevColumns =>
      prevColumns.map(col =>
        col.id === columnId
          ? { ...col, tasks: col.tasks.filter(task => task.id !== taskId) }
          : col
      )
    );
  };

  const handleUpdateTask = (updatedTask) => {
    setColumns(prevColumns =>
      prevColumns.map(col => ({
        ...col,
        tasks: col.tasks.map(task =>
          task.id === updatedTask.id ? updatedTask : task
        )
      }))
    );
  };

  // Placeholder for drag and drop functionality
  const handleDrop = (taskId, targetColumnId) => {
    let taskToMove;
    let sourceColumnId;

    // Find the task and its source column
    setColumns(prevColumns => {
      const newCols = prevColumns.map(col => {
        const taskIndex = col.tasks.findIndex(task => task.id === taskId);
        if (taskIndex > -1) {
          taskToMove = { ...col.tasks[taskIndex], status: targetColumnId };
          sourceColumnId = col.id;
          return { ...col, tasks: col.tasks.filter(task => task.id !== taskId) };
        }
        return col;
      });

      // Add the task to the target column
      if (taskToMove) {
        return newCols.map(col =>
          col.id === targetColumnId ? { ...col, tasks: [...col.tasks, taskToMove] } : col
        );
      }
      return newCols;
    });
  };

  const handleDragStart = (e, taskId) => {
    e.dataTransfer.setData('taskId', taskId);
  };

  const handleDragOver = (e) => {
    e.preventDefault(); // Allows drop
  };

  const handleDropOnColumn = (e, columnId) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('taskId');
    handleDrop(taskId, columnId);
  };

  return (
    <main data-testid="page-root" className="flex flex-col h-screen bg-background">
      <header className="border-b p-4 flex justify-between items-center bg-card shadow-sm">
        <h1 data-testid="page-title" className="text-2xl font-bold">Build a kanban board for managing tasks across col</h1>
        <div className="flex gap-4">
          <Button variant="outline" data-testid="filter-button">
            <Filter className="mr-2 h-4 w-4" /> Filter
          </Button>
          <Button data-testid="search-button">
            <Search className="mr-2 h-4 w-4" /> Search
          </Button>
        </div>
      </header>

      {isLoading && (
        <div data-testid="loading-indicator" className="p-4 text-center text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin inline-block mr-2" /> Loading tasks...
        </div>
      )}

      {isError && (
        <div data-testid="error-message" className="p-4 text-center text-red-500 flex items-center justify-center">
          <AlertCircle className="h-5 w-5 mr-2" /> Failed to load tasks. Please try again.
        </div>
      )}

      <div data-testid="task-list" className="flex-1 overflow-x-auto p-4">
        <div className="inline-flex h-full space-x-4">
          {columns.map(column => (
            <Card
              key={column.id}
              className="w-80 flex-shrink-0 flex flex-col bg-secondary/20 border-border shadow-sm"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDropOnColumn(e, column.id)}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-lg font-semibold flex items-center gap-4">
                  {column.title}
                  <Badge variant="secondary" className="text-xs font-normal">{column.tasks.length}</Badge>
                </CardTitle>
                <Dialog open={isAddTaskDialogOpen && currentColumnIdForNewTask === column.id} onOpenChange={setIsAddTaskDialogOpen}>
                  <DialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      data-testid={`add-task-button-${column.id}`}
                      onClick={() => {
                        setCurrentColumnIdForNewTask(column.id);
                        setIsAddTaskDialogOpen(true);
                      }}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                      <DialogTitle>Add New Task to {column.title}</DialogTitle>
                      <DialogDescription>
                        Fill in the details for your new task.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="title" className="text-right">Title</Label>
                        <Input
                          id="title"
                          value={newTaskTitle}
                          onChange={(e) => setNewTaskTitle(e.target.value)}
                          className="col-span-3"
                          data-testid="new-task-title-input"
                        />
                      </div>
                      <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="description" className="text-right">Description</Label>
                        <Textarea
                          id="description"
                          value={newTaskDescription}
                          onChange={(e) => setNewTaskDescription(e.target.value)}
                          className="col-span-3"
                          data-testid="new-task-description-input"
                        />
                      </div>
                      <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="assignee" className="text-right">Assignee</Label>
                        <Select
                          onValueChange={setNewTaskAssigneeId}
                          value={newTaskAssigneeId}
                        >
                          <SelectTrigger className="col-span-3" data-testid="new-task-assignee-select">
                            <SelectValue placeholder="Select an assignee" />
                          </SelectTrigger>
                          <SelectContent>
                            {mockAssignees.map(assignee => (
                              <SelectItem key={assignee.id} value={assignee.id}>
                                {assignee.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="priority" className="text-right">Priority</Label>
                        <Select
                          onValueChange={setNewTaskPriority}
                          value={newTaskPriority}
                        >
                          <SelectTrigger className="col-span-3" data-testid="new-task-priority-select">
                            <SelectValue placeholder="Select priority" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="high">High</SelectItem>
                            <SelectItem value="medium">Medium</SelectItem>
                            <SelectItem value="low">Low</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="dueDate" className="text-right">Due Date</Label>
                        <Input
                          id="dueDate"
                          type="date"
                          value={newTaskDueDate}
                          onChange={(e) => setNewTaskDueDate(e.target.value)}
                          className="col-span-3"
                          data-testid="new-task-due-date-input"
                        />
                      </div>
                      {/* Tags selection could be a multi-select component */}
                    </div>
                    <DialogFooter>
                      <Button
                        type="submit"
                        onClick={() => handleAddTask(currentColumnIdForNewTask)}
                        data-testid="create-task-button"
                      >
                        Create Task
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto p-2">
                <ScrollArea className="h-full pr-2">
                  <div className="space-y-4">
                    {column.tasks.map(task => (
                      <div
                        key={task.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, task.id)}
                      >
                        <TaskCard
                          task={task}
                          onDelete={() => handleDeleteTask(task.id, column.id)}
                          onUpdate={handleUpdateTask}
                        />
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
              <CardFooter className="p-2 pt-0">
                <Input
                  placeholder="Quick add task..."
                  className="w-full"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleAddTask(column.id);
                    }
                  }}
                  data-testid={`quick-add-task-input-${column.id}`}
                />
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    </main>
  );
};

export default TasksPage;