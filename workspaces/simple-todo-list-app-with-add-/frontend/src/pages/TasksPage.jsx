import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Plus } from 'lucide-react';
import { TaskCard } from '../components/TaskCard';
import { mockTasks } from '../data/mock';
import { ui } from '../design/theme'; // Assuming this file exists as per instructions

export default function TasksPage() {
  const [tasks, setTasks] = useState(mockTasks);
  const [newTaskForm, setNewTaskForm] = useState({
    title: '',
    content: '',
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewTaskForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateTask = () => {
    if (!newTaskForm.title.trim()) return;

    const newTask = {
      id: Date.now().toString(),
      title: newTaskForm.title.trim(),
      content: newTaskForm.content.trim(),
      status: 'To Do',
      created_at: new Date().toISOString(),
    };
    setTasks((prev) => [...prev, newTask]);
    setNewTaskForm({ title: '', content: '' });
  };

  const handleCompleteTask = (id) => {
    setTasks((prev) =>
      prev.map((task) =>
        task.id === id ? { ...task, status: 'Completed' } : task
      )
    );
  };

  const handleDeleteTask = (id) => {
    setTasks((prev) => prev.filter((task) => task.id !== id));
  };

  return (
    <main data-testid="page-root" className={ui.pageRoot}>
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        <h1 data-testid="page-title" className="text-3xl font-bold">Manage Your Tasks</h1>
        <p className={ui.mutedText}>
          Add, complete, and delete your productivity tasks.
        </p>

        <Card className={ui.card}>
          <CardHeader>
            <CardTitle>Add New Task</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4">
              <Label htmlFor="task-title">Task Title</Label>
              <Input
                data-testid="new-task-title-input"
                id="task-title"
                name="title"
                placeholder="e.g., Finish project report"
                value={newTaskForm.title}
                onChange={handleInputChange}
              />
            </div>
            <div className="grid gap-4">
              <Label htmlFor="task-content">Description (Optional)</Label>
              <Textarea
                data-testid="new-task-content-input"
                id="task-content"
                name="content"
                placeholder="Details about the task..."
                value={newTaskForm.content}
                onChange={handleInputChange}
              />
            </div>
            <Button
              data-testid="create-task-button"
              onClick={handleCreateTask}
              className={ui.primaryButton}
              disabled={!newTaskForm.title.trim()}
            >
              <Plus className="mr-2 h-4 w-4" /> Add Task
            </Button>
          </CardContent>
        </Card>

        <section>
          <h2 className="text-2xl font-semibold mb-4">All Tasks</h2>
          <div data-testid="task-list" className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tasks.length === 0 ? (
              <p className={ui.mutedText}>No tasks yet. Start by adding a new one!</p>
            ) : (
              tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onComplete={handleCompleteTask}
                  onDelete={handleDeleteTask}
                />
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
