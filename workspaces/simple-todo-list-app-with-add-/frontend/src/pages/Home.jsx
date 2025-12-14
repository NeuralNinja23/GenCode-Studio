import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';
import { mockTasks, mockTaskStats } from '../data/mock';
import { TaskCard } from '../components/TaskCard';
import { ui } from '../design/theme'; // Assuming this file exists as per instructions

export default function Home() {
  const recentTasks = mockTasks.slice(0, 3);

  return (
    <main data-testid="page-root" className={ui.pageRoot}>
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-10">
        <header className="text-center space-y-4">
          <h1 data-testid="page-title" className="text-4xl font-extrabold tracking-tight lg:text-5xl">
            Create a simple todo list app with add, complete,
          </h1>
          <p className={`text-xl ${ui.mutedText}`}>
            Manage your tasks efficiently and stay productive.
          </p>
          <Button className={ui.primaryButton} size="lg">
            Manage All Tasks <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </header>

        <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Card className={ui.card}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
              <span className="text-muted-foreground">ð</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.total}</div>
              <p className={ui.mutedText}>All tasks in your list</p>
            </CardContent>
          </Card>
          <Card className={ui.card}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">To Do</CardTitle>
              <span className="text-blue-500">â³</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.toDo}</div>
              <p className={ui.mutedText}>Tasks awaiting action</p>
            </CardContent>
          </Card>
          <Card className={ui.card}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">In Progress</CardTitle>
              <span className="text-yellow-500">ð§</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.inProgress}</div>
              <p className={ui.mutedText}>Tasks currently being worked on</p>
            </CardContent>
          </Card>
          <Card className={ui.card}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <span className="text-green-500">â</span>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockTaskStats.completed}</div>
              <p className={ui.mutedText}>Tasks successfully finished</p>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Recent Tasks</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {recentTasks.length === 0 ? (
              <p className={ui.mutedText}>No recent tasks to display.</p>
            ) : (
              recentTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  // No onComplete/onDelete functionality on dashboard view
                  onComplete={() => console.log(`Complete task ${task.id}`)}
                  onDelete={() => console.log(`Delete task ${task.id}`)}
                />
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
