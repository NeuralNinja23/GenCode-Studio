import React, { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Search, Plus, Loader2 } from 'lucide-react';
import { mockNotes } from '../data/mock';
import NoteCard from '../components/NoteCard';

function NotesPage() {
  const [notes, setNotes] = useState(mockNotes);
  const [searchTerm, setSearchTerm] = useState('');
  const [newNoteForm, setNewNoteForm] = useState({ title: '', content: '' });
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [editForm, setEditForm] = useState({ title: '', content: '' });
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(false); // For future API calls
  const [error, setError] = useState(null); // For future API calls

  const filteredNotes = useMemo(() => {
    return notes.filter(note =>
      note.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [notes, searchTerm]);

  const handleCreateNote = () => {
    if (!newNoteForm.title || !newNoteForm.content) return;

    setLoading(true);
    setError(null);
    setTimeout(() => { // Simulate API call
      const newNote = {
        id: Date.now().toString(),
        ...newNoteForm,
        status: "Draft", // Default status for new notes
        created_at: new Date().toISOString(),
      };
      setNotes(prevNotes => [...prevNotes, newNote]);
      setNewNoteForm({ title: '', content: '' });
      setShowAddForm(false);
      setLoading(false);
    }, 500);
  };

  const handleDeleteNote = (id) => {
    setLoading(true);
    setError(null);
    setTimeout(() => { // Simulate API call
      setNotes(prevNotes => prevNotes.filter(note => note.id !== id));
      setLoading(false);
    }, 300);
  };

  const handleEditClick = (note) => {
    setEditingNoteId(note.id);
    setEditForm({ title: note.title, content: note.content });
  };

  const handleUpdateNote = (id) => {
    if (!editForm.title || !editForm.content) return;

    setLoading(true);
    setError(null);
    setTimeout(() => { // Simulate API call
      setNotes(prevNotes =>
        prevNotes.map(note =>
          note.id === id ? { ...note, title: editForm.title, content: editForm.content } : note
        )
      );
      setEditingNoteId(null);
      setEditForm({ title: '', content: '' });
      setLoading(false);
    }, 500);
  };

  const handleCancelEdit = () => {
    setEditingNoteId(null);
    setEditForm({ title: '', content: '' });
  };

  return (
    <main data-testid="page-root" className="flex-1 p-6 bg-background text-foreground">
      <div className="max-w-7xl mx-auto space-y-8">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="space-y-4">
            <h1 data-testid="page-title" className="text-3xl font-bold">Manage Your Notes</h1>
            <p className="text-muted-foreground">Create, edit, delete, and search your productivity notes.</p>
          </div>
          <div className="flex items-center gap-4 w-full md:w-auto">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                data-testid="search-input"
                type="text"
                placeholder="Search notes by title..."
                className="pl-9 pr-4 py-2 w-full"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Button data-testid="create-note-button" onClick={() => setShowAddForm(!showAddForm)} className="flex-shrink-0">
              <Plus className="mr-2 h-4 w-4" />
              Add Note
            </Button>
          </div>
        </header>

        {showAddForm && (
          <Card className="bg-card border border-border shadow-lg">
            <CardHeader>
              <CardTitle>Create New Note</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="new-note-title">Title</Label>
                <Input
                  data-testid="new-note-title-input"
                  id="new-note-title"
                  value={newNoteForm.title}
                  onChange={(e) => setNewNoteForm({ ...newNoteForm, title: e.target.value })}
                  placeholder="Enter note title"
                />
              </div>
              <div>
                <Label htmlFor="new-note-content">Content</Label>
                <Textarea
                  data-testid="new-note-content-input"
                  id="new-note-content"
                  value={newNoteForm.content}
                  onChange={(e) => setNewNoteForm({ ...newNoteForm, content: e.target.value })}
                  placeholder="Write your note content here..."
                  rows={5}
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-end gap-4">
              <Button variant="outline" onClick={() => setShowAddForm(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateNote} disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Create Note
              </Button>
            </CardFooter>
          </Card>
        )}

        {loading && (
          <div data-testid="loading-indicator" className="flex items-center justify-center p-8 text-muted-foreground">
            <Loader2 className="mr-2 h-6 w-6 animate-spin" /> Loading notes...
          </div>
        )}

        {error && (
          <div data-testid="error-message" className="p-4 bg-red-900/20 text-red-400 border border-red-700 rounded-md">
            Error: {error}
          </div>
        )}

        <div data-testid="note-list" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredNotes.length === 0 && !loading && !error ? (
            <p className="col-span-full text-center text-muted-foreground">No notes found. Try creating one!</p>
          ) : (
            filteredNotes.map(note => (
              editingNoteId === note.id ? (
                <Card key={note.id} className="bg-card border border-border shadow-lg">
                  <CardHeader>
                    <CardTitle>Edit Note</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label htmlFor={`edit-note-title-${note.id}`}>Title</Label>
                      <Input
                        data-testid={`edit-note-title-input-${note.id}`}
                        id={`edit-note-title-${note.id}`}
                        value={editForm.title}
                        onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                        placeholder="Enter note title"
                      />
                    </div>
                    <div>
                      <Label htmlFor={`edit-note-content-${note.id}`}>Content</Label>
                      <Textarea
                        data-testid={`edit-note-content-input-${note.id}`}
                        id={`edit-note-content-${note.id}`}
                        value={editForm.content}
                        onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                        placeholder="Write your note content here..."
                        rows={5}
                      />
                    </div>
                  </CardContent>
                  <CardFooter className="flex justify-end gap-4">
                    <Button variant="outline" onClick={handleCancelEdit}>
                      Cancel
                    </Button>
                    <Button onClick={() => handleUpdateNote(note.id)} disabled={loading}>
                      {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Save Changes
                    </Button>
                  </CardFooter>
                </Card>
              ) : (
                <NoteCard
                  key={note.id}
                  note={note}
                  onDelete={handleDeleteNote}
                  onEdit={handleEditClick}
                  loading={loading}
                />
              )
            ))
          )}
        </div>
      </div>
    </main>
  );
}

export default NotesPage;
