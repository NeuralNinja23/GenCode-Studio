import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowRight, Plus, FileText, CheckCircle, Clock } from 'lucide-react';
import { mockNotes, mockNoteStats } from '../data/mock';

function Home() {
  const recentNotes = mockNotes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 3);

  return (
    <main data-testid="page-root" className="flex-1 p-6 bg-background text-foreground">
      <div className="max-w-7xl mx-auto space-y-8">
        <header className="space-y-4">
          <h1 data-testid="page-title" className="text-3xl font-bold">Create a notes manager where users can create, edi</h1>
          <p className="text-muted-foreground">
            Manage your notes efficiently and stay organized.
          </p>
        </header>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-card border border-border shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Notes</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockNoteStats.total}</div>
              <p className="text-xs text-muted-foreground">All your recorded thoughts</p>
            </CardContent>
          </Card>

          <Card className="bg-card border border-border shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Notes</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockNoteStats.active}</div>
              <p className="text-xs text-muted-foreground">Currently in progress</p>
            </CardContent>
          </Card>

          <Card className="bg-card border border-border shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Draft Notes</CardTitle>
              <Clock className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockNoteStats.draft}</div>
              <p className="text-xs text-muted-foreground">Waiting for completion</p>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-semibold">Recent Notes</h2>
            <Button variant="link" className="px-0">
              View All <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentNotes.map(note => (
              <Card key={note.id} className="bg-card border border-border shadow-lg">
                <CardHeader>
                  <CardTitle className="text-lg line-clamp-1">{note.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2">{note.content}</p>
                  <div className="text-xs text-gray-500 mt-2">Created: {new Date(note.created_at).toLocaleDateString()}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Quick Actions</h2>
          <div className="flex gap-4">
            <Button data-testid="create-note-button" className="bg-primary text-primary-foreground hover:bg-primary/90">
              <Plus className="mr-2 h-4 w-4" /> Create New Note
            </Button>
            <Button variant="outline">
              <FileText className="mr-2 h-4 w-4" /> View All Notes
            </Button>
          </div>
        </section>
      </div>
    </main>
  );
}

export default Home;
