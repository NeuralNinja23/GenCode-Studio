export const mockTasks = [
  {
    id: "1",
    title: "Design homepage mockup",
    content: "Create initial wireframes and high-fidelity mockups for the new website homepage.",
    status: "Active",
    priority: "High",
    dueDate: "2024-07-25",
    created_at: "2024-07-18T10:00:00Z",
  },
  {
    id: "2",
    title: "Implement user authentication",
    content: "Set up user registration, login, and session management using JWT.",
    status: "Active",
    priority: "High",
    dueDate: "2024-07-30",
    created_at: "2024-07-19T11:30:00Z",
  },
  {
    id: "3",
    title: "Write API documentation",
    content: "Document all API endpoints, request/response schemas, and authentication methods.",
    status: "Completed",
    priority: "Medium",
    dueDate: "2024-07-15",
    created_at: "2024-07-10T09:00:00Z",
  },
  {
    id: "4",
    title: "Refactor database schema",
    content: "Optimize existing database tables and relationships for better performance.",
    status: "Active",
    priority: "Medium",
    dueDate: "2024-08-05",
    created_at: "2024-07-20T14:00:00Z",
  },
  {
    id: "5",
    title: "Prepare sprint review presentation",
    content: "Compile progress, demos, and next steps for the upcoming sprint review meeting.",
    status: "Active",
    priority: "Low",
    dueDate: "2024-07-28",
    created_at: "2024-07-22T16:00:00Z",
  },
];

export const mockTaskStats = {
  total: mockTasks.length,
  active: mockTasks.filter(x => x.status === "Active").length,
  completed: mockTasks.filter(x => x.status === "Completed").length,
};
