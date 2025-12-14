export const mockNotes = [
  {
    id: "1",
    title: "Project Kick-off Meeting Notes",
    content: "Discussed project scope, team roles, and initial timelines. Key action items include setting up Jira and scheduling daily stand-ups. Attendees: John, Jane, Mike.",
    status: "Active",
    created_at: "2024-03-10T10:00:00Z",
  },
  {
    id: "2",
    title: "Brainstorming Session for New Feature",
    content: "Ideas generated for user authentication flow: OAuth, JWT, session-based. Pros and cons of each were debated. Next step: technical deep-dive on JWT implementation.",
    status: "Draft",
    created_at: "2024-03-09T14:30:00Z",
  },
  {
    id: "3",
    title: "Weekly Sync - Frontend Progress",
    content: "Completed user profile page, started on dashboard layout. Encountered minor issue with responsive grid on mobile, will address tomorrow. PR for profile page is ready for review.",
    status: "Active",
    created_at: "2024-03-08T09:15:00Z",
  },
  {
    id: "4",
    title: "Backend API Design for Notes",
    content: "Defined endpoints for GET /notes, POST /notes, PUT /notes/{id}, DELETE /notes/{id}. Discussed data models for Note entity: title, content, status, created_at, updated_at.",
    status: "Active",
    created_at: "2024-03-07T11:00:00Z",
  },
  {
    id: "5",
    title: "Research on State Management Libraries",
    content: "Explored Zustand, Redux Toolkit, and React Context. Zustand seems promising for its simplicity and performance for this project. Need to create a small PoC.",
    status: "Draft",
    created_at: "2024-03-06T16:00:00Z",
  },
];

export const mockNoteStats = {
  total: mockNotes.length,
  active: mockNotes.filter(x => x.status === "Active").length,
  draft: mockNotes.filter(x => x.status === "Draft").length,
};
