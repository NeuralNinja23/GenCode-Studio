import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, ArrowRight, CheckCircle, Clock, XCircle } from 'lucide-react';
import { mockTaskStats, mockTasks } from '../data/mock';
import { Link } from 'react-router-dom';

export default function Home() {
  const recentTasks = mockTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Done':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'In Progress':
      case 'Review':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'Backlog':
      default:
        return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };

  return (
    <main data-testid="page-root" className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 data-testid="page-title" className="text-4xl font-extrabold tracking-tight lg:text-5xl">
              Kanban Dashboard
            </h1>
            <p className="text-muted-foreground text-lg">
              Manage your tasks efficiently across columns
            </p>
          </div>
          <Link to="/tasks">
            <Button data-testid="create-task-button" className="flex items-center gap-4">
              <Plus className="h-4 w-4" /> Go to Board
            </Button>
          </Link>
        </div>

        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.total}</div>
              <p className="text-xs text-muted-foreground">All tasks in your project</p>
            </CardContent>
          </Card>
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">In Progress</CardTitle>
              <Clock className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.inProgress}</div>
              <p className="text-xs text-muted-foreground">Currently being worked on</p>
            </CardContent>
          </Card>
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.done}</div>
              <p className="text-xs text-muted-foreground">Tasks successfully finished</p>
            </CardContent>
          </Card>
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Backlog</CardTitle>
              <XCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.backlog}</div>
              <p className="text-xs text-muted-foreground">Tasks awaiting start</p>
            </CardContent>
          </Card>
        </section>

        <section>
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Recent Tasks</CardTitle>
              <Link to="/tasks">
                <Button variant="link" className="flex items-center gap-4 p-0 h-auto">
                  View All <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              <div data-testid="task-list" className="space-y-4">
                {recentTasks.length === 0 ? (
                  <p className="text-muted-foreground">No recent tasks.</p>
                ) : (
                  recentTasks.map(task => (
                    <div key={task.id} className="flex items-center justify-between p-3 border rounded-md">
                      <div className="flex items-center gap-4">
                        {getStatusIcon(task.status)}
                        <span className="font-medium">{task.title}</span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {task.status} - {new Date(task.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
