export const mockNotes = [
  {
    id: "1",
    title: "Project Kick-off Meeting Notes",
    content: "Discussed initial project scope, team roles, and preliminary timeline. Key action items include setting up Jira and scheduling daily stand-ups. Remember to follow up with Sarah on the design assets.",
    status: "Active",
    created_at: "2024-03-10T10:00:00Z",
  },
  {
    id: "2",
    title: "Ideas for New Feature X",
    content: "Brainstormed several concepts for Feature X. Focus areas: user authentication, real-time updates, and offline capabilities. Need to research existing solutions and conduct a feasibility study.",
    status: "Draft",
    created_at: "2024-03-08T14:30:00Z",
  },
  {
    id: "3",
    title: "Weekly Sync with Marketing Team",
    content: "Reviewed Q1 marketing performance. Discussed upcoming campaigns for Q2. Action: Prepare a summary of website traffic analytics for next week's meeting. Don't forget the social media strategy.",
    status: "Active",
    created_at: "2024-03-05T09:00:00Z",
  },
  {
    id: "4",
    title: "Personal To-Do List",
    content: "Buy groceries, call dentist, finish reading 'Clean Code', plan weekend trip. Important: Renew subscription for cloud storage by end of month.",
    status: "Active",
    created_at: "2024-03-11T18:00:00Z",
  },
  {
    id: "5",
    title: "Bug Report: Login Page Issue",
    content: "Users are reporting issues logging in with special characters in their passwords. Need to investigate backend validation and frontend encoding. Priority: High.",
    status: "Pending",
    created_at: "2024-03-09T11:15:00Z",
  },
];

export const mockNoteStats = {
  total: mockNotes.length,
  active: mockNotes.filter(x => x.status === "Active").length,
  draft: mockNotes.filter(x => x.status === "Draft").length,
  pending: mockNotes.filter(x => x.status === "Pending").length,
};
