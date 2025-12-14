import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Plus, Trash2, Edit, Search, CheckCircle, Clock } from 'lucide-react';
import { NoteCard } from '@/components/NoteCard';
import { mockNotes } from '@/data/mock';

export default function NotesPage() {
  const [notes, setNotes] = useState(mockNotes);
  const [searchTerm, setSearchTerm] = useState('');
  const [newNoteForm, setNewNoteForm] = useState({ title: '', content: '' });
  const [editingNote, setEditingNote] = useState(null); // null or the note object being edited

  const filteredNotes = notes.filter(note =>
    note.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCreateNote = () => {
    if (!newNoteForm.title || !newNoteForm.content) return;
    const newNote = {
      id: Date.now().toString(),
      title: newNoteForm.title,
      content: newNoteForm.content,
      status: "Draft", // Default status for new notes
      created_at: new Date().toISOString(),
    };
    setNotes(prevNotes => [...prevNotes, newNote]);
    setNewNoteForm({ title: '', content: '' });
  };

  const handleUpdateNote = (updatedNote) => {
    setNotes(prevNotes =>
      prevNotes.map(note => (note.id === updatedNote.id ? updatedNote : note))
    );
    setEditingNote(null); // Close edit mode
  };

  const handleDeleteNote = (id) => {
    setNotes(prevNotes => prevNotes.filter(note => note.id !== id));
  };

  const handleEditClick = (note) => {
    setEditingNote({ ...note }); // Set the note to be edited
  };

  const handleEditFormChange = (e) => {
    const { name, value } = e.target;
    setEditingNote(prev => ({ ...prev, [name]: value }));
  };

  const handleSaveEdit = () => {
    if (editingNote) {
      handleUpdateNote(editingNote);
    }
  };

  return (
    <main data-testid="page-root" className="min-h-screen bg-background p-6 text-foreground">
      <div className="max-w-7xl mx-auto space-y-8">
        <h1 data-testid="page-title" className="text-4xl font-bold tracking-tight">Manage Your Notes</h1>
        <p className="text-muted-foreground text-lg">Create, edit, delete, and search your productivity notes.</p>

        {/* Search Bar */}
        <div className="flex items-center space-x-4">
          <Search className="h-5 w-5 text-muted-foreground" />
          <Input
            data-testid="search-input"
            type="text"
            placeholder="Search notes by title..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 bg-card border-border focus:ring-primary focus:border-primary"
          />
        </div>

        {/* Add New Note Form */}
        <Card className="bg-card border-border shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-4 text-xl">
              <Plus className="h-5 w-5" /> Add New Note
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4">
              <Label htmlFor="new-note-title">Title</Label>
              <Input
                data-testid="new-note-title-input"
                id="new-note-title"
                name="title"
                placeholder="Note title"
                value={newNoteForm.title}
                onChange={(e) => setNewNoteForm({ ...newNoteForm, title: e.target.value })}
                className="bg-input border-border"
              />
            </div>
            <div className="grid gap-4">
              <Label htmlFor="new-note-content">Content</Label>
              <Textarea
                data-testid="new-note-content-input"
                id="new-note-content"
                name="content"
                placeholder="Write your note content here..."
                value={newNoteForm.content}
                onChange={(e) => setNewNoteForm({ ...newNoteForm, content: e.target.value })}
                className="bg-input border-border min-h-[100px]"
              />
            </div>
            <Button data-testid="create-note-button" onClick={handleCreateNote} className="w-full">
              <Plus className="mr-2 h-4 w-4" /> Create Note
            </Button>
          </CardContent>
        </Card>

        {/* Notes Grid */}
        <div data-testid="note-list" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredNotes.length > 0 ? (
            filteredNotes.map(note => (
              <NoteCard
                key={note.id}
                note={note}
                onEdit={handleEditClick}
                onDelete={handleDeleteNote}
              />
            ))
          ) : (
            <p className="col-span-full text-center text-muted-foreground">No notes found. Start by creating one!</p>
          )}
        </div>

        {/* Edit Note Modal/Inline (simplified for this example, could be a modal) */}
        {editingNote && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <Card className="w-full max-w-md bg-card border-border shadow-2xl">
              <CardHeader>
                <CardTitle className="text-xl">Edit Note</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4">
                  <Label htmlFor="edit-note-title">Title</Label>
                  <Input
                    data-testid="edit-note-title-input"
                    id="edit-note-title"
                    name="title"
                    value={editingNote.title}
                    onChange={handleEditFormChange}
                    className="bg-input border-border"
                  />
                </div>
                <div className="grid gap-4">
                  <Label htmlFor="edit-note-content">Content</Label>
                  <Textarea
                    data-testid="edit-note-content-input"
                    id="edit-note-content"
                    name="content"
                    value={editingNote.content}
                    onChange={handleEditFormChange}
                    className="bg-input border-border min-h-[100px]"
                  />
                </div>
                <div className="flex justify-end gap-4">
                  <Button variant="outline" onClick={() => setEditingNote(null)}>
                    Cancel
                  </Button>
                  <Button data-testid="save-edit-note-button" onClick={handleSaveEdit}>
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </main>
  );
}
