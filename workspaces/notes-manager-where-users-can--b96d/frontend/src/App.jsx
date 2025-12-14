import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import NotesPage from './pages/NotesPage';
import { Button } from '@/components/ui/button';
import { NotebookPen, Home as HomeIcon } from 'lucide-react';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background text-foreground">
        <header className="border-b border-border p-4 flex justify-between items-center bg-card shadow-sm">
          <Link to="/" className="flex items-center gap-4 text-2xl font-bold text-primary hover:text-primary/80 transition-colors">
            <NotebookPen className="h-7 w-7" />
            Notes Manager
          </Link>
          <nav className="flex gap-4">
            <Link to="/">
              <Button variant="ghost" className="text-muted-foreground hover:text-foreground">
                <HomeIcon className="mr-2 h-4 w-4" /> Home
              </Button>
            </Link>
            <Link to="/notes">
              <Button variant="ghost" className="text-muted-foreground hover:text-foreground">
                <NotebookPen className="mr-2 h-4 w-4" /> Notes
              </Button>
            </Link>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/notes" element={<NotesPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
