import React from 'react';
import NotesPage from './pages/NotesPage';
// import Home from './pages/Home'; // Can be used for a dashboard view later

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* 
        In a full application, you'd likely have a layout component 
        that includes a sidebar and then renders different pages based on routing.
        For this task, NotesPage is the primary focus for managing notes.
      */}
      <NotesPage />
    </div>
  );
}

export default App;
