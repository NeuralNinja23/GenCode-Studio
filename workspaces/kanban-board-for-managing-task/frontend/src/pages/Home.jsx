import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { mockTaskStats, mockTasks } from '../data/mock';
import { format, isPast } from 'date-fns';
import { ArrowRight, Plus, CheckCircle, Clock, AlertCircle, ListTodo } from 'lucide-react';

function Home() {
  const recentTasks = mockTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'done':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'in-progress':
        return <Clock className="h-4 w-4 text-blue-500" />;
      case 'review':
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
      case 'backlog':
      default:
        return <ListTodo className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <main data-testid="page-root" className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 data-testid="page-title" className="text-4xl font-bold text-foreground">Build a kanban board for managing tasks across col</h1>
            <p className="text-muted-foreground mt-2">Manage your tasks efficiently and track project progress.</p>
          </div>
          <Button data-testid="create-task-button" size="lg">
            <Plus className="mr-2 h-5 w-5" /> Create New Task
          </Button>
        </div>

        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
              <ListTodo className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.total}</div>
              <p className="text-xs text-muted-foreground">All tasks in your board</p>
            </CardContent>
          </Card>
          <Card className="bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">In Progress</CardTitle>
              <Clock className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.inProgress}</div>
              <p className="text-xs text-muted-foreground">Currently being worked on</p>
            </CardContent>
          </Card>
          <Card className="bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.done}</div>
              <p className="text-xs text-muted-foreground">Tasks successfully finished</p>
            </CardContent>
          </Card>
          <Card className="bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Overdue</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.overdue}</div>
              <p className="text-xs text-muted-foreground">Tasks past their due date</p>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-foreground">Recent Tasks</h2>
          <Card className="bg-card shadow-sm">
            <CardContent className="p-0">
              <div data-testid="task-list" className="divide-y divide-border">
                {recentTasks.length > 0 ? (
                  recentTasks.map(task => (
                    <div key={task.id} className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors">
                      <div className="flex items-center gap-4">
                        {getStatusIcon(task.status)}
                        <div>
                          <p className="font-medium text-foreground">{task.title}</p>
                          <p className="text-sm text-muted-foreground">{task.description.substring(0, 70)}{task.description.length > 70 ? '...' : ''}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        {task.dueDate && (
                          <span className={`text-sm ${isPast(new Date(task.dueDate)) && task.status !== 'done' ? 'text-red-500' : 'text-muted-foreground'}`}>
                            Due: {format(new Date(task.dueDate), 'MMM dd')}
                          </span>
                        )}
                        {task.assignee && (
                          <div className="flex items-center gap-4">
                            <img src={task.assignee.avatar} alt={task.assignee.name} className="w-6 h-6 rounded-full" />
                            <span className="text-sm text-muted-foreground hidden sm:inline">{task.assignee.name}</span>
                          </div>
                        )}
                        <Button variant="ghost" size="sm" data-testid={`view-task-button-${task.id}`}>
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="p-4 text-muted-foreground text-center">No recent tasks found.</p>
                )}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}

export default Home;
