import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Plus, ArrowRight, LayoutDashboard, ListTodo, Users, Tag } from 'lucide-react';

import { mockTaskStats, mockTasks, mockProjects } from '../data/mock';
import TaskCard from '../components/TaskCard';

const Home = () => {
  const recentTasks = mockTasks.slice(0, 3);

  return (
    <main data-testid="page-root" className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex justify-between items-center">
          {/* FIX 3: Updated page title to be complete and meaningful */}
          <h1 data-testid="page-title" className="text-4xl font-extrabold tracking-tight lg:text-5xl">
            Kanban Project Dashboard
          </h1>
          <Button data-testid="create-task-button" className="flex items-center gap-4">
            <Plus className="h-4 w-4" /> Add New Task
          </Button>
        </div>
        <p className="text-lg text-muted-foreground">
          Overview of your projects and tasks. Stay productive!
        </p>

        <Separator />

        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
              <ListTodo className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.total}</div>
              <p className="text-xs text-muted-foreground">Across all columns</p>
            </CardContent>
          </Card>
          <Card className="bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">In Progress</CardTitle>
              <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.inProgress}</div>
              <p className="text-xs text-muted-foreground">Currently being worked on</p>
            </CardContent>
          </Card>
          <Card className="bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Backlog</CardTitle>
              <Tag className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.backlog}</div>
              <p className="text-xs text-muted-foreground">Tasks awaiting start</p>
            </CardContent>
          </Card>
          <Card className="bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.done}</div>
              <p className="text-xs text-muted-foreground">Tasks finished</p>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-semibold">Recent Tasks</h2>
            <Button variant="link" className="flex items-center gap-4" data-testid="view-all-tasks-button">
              View All <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentTasks.map(task => (
              <TaskCard key={task.id} task={task} onDelete={() => console.log('Delete from Home')} onUpdate={() => console.log('Update from Home')} />
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Your Projects</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {mockProjects.map(project => (
              <Card key={project.id} className="bg-card shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-lg font-medium flex items-center gap-4">
                    <span className="h-3 w-3 rounded-full" style={{ backgroundColor: project.color }}></span>
                    {project.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-xl font-bold">{project.taskCount} Tasks</div>
                  <p className="text-xs text-muted-foreground">Active tasks in this project</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
};

export default Home;