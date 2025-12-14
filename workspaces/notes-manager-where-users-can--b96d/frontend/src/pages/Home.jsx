import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, ArrowRight, NotebookPen, ListTodo, Clock } from 'lucide-react';
import { mockNotes, mockNoteStats } from '@/data/mock';
import { Link } from 'react-router-dom';

export default function Home() {
  const recentNotes = mockNotes.slice(0, 3); // Get top 3 recent notes

  return (
    <main data-testid="page-root" className="min-h-screen bg-background p-6 text-foreground">
      <div className="max-w-7xl mx-auto space-y-8">
        <h1 data-testid="page-title" className="text-4xl font-bold tracking-tight">Your Notes Dashboard</h1>
        <p className="text-muted-foreground text-lg">
          Quick overview of your notes and recent activity.
        </p>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-card border-border shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Notes</CardTitle>
              <NotebookPen className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockNoteStats.total}</div>
              <p className="text-xs text-muted-foreground">All your recorded thoughts</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Notes</CardTitle>
              <ListTodo className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockNoteStats.active}</div>
              <p className="text-xs text-muted-foreground">Currently in progress or relevant</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Draft Notes</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockNoteStats.draft}</div>
              <p className="text-xs text-muted-foreground">Unfinished or pending review</p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card className="bg-card border-border shadow-lg">
          <CardHeader>
            <CardTitle className="text-xl">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4">
            <Link to="/notes">
              <Button data-testid="view-all-notes-button">
                <ArrowRight className="mr-2 h-4 w-4" /> View All Notes
              </Button>
            </Link>
            <Link to="/notes">
              <Button data-testid="create-note-button">
                <Plus className="mr-2 h-4 w-4" /> Create New Note
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Recent Notes */}
        <Card className="bg-card border-border shadow-lg">
          <CardHeader>
            <CardTitle className="text-xl">Recent Notes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {recentNotes.length > 0 ? (
              recentNotes.map(note => (
                <div key={note.id} className="flex items-center justify-between p-3 bg-accent/20 rounded-md border border-border">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg">{note.title}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-1">{note.content}</p>
                  </div>
                  <Badge
                    className={`ml-4 ${note.status === 'Active' ? 'bg-green-600/20 text-green-400' : 'bg-yellow-600/20 text-yellow-400'}`}
                  >
                    {note.status}
                  </Badge>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground">No recent notes to display.</p>
            )}
            <Link to="/notes" className="block text-right text-primary hover:underline">
              View all notes <ArrowRight className="inline-block h-4 w-4 ml-1" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
