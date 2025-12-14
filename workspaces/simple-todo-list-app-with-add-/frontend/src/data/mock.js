export const mockTasks = [
  {
    id: "1",
    title: "Design homepage mockup",
    content: "Create initial wireframes and high-fidelity mockups for the new website homepage.",
    status: "In Progress",
    created_at: "2024-01-15T10:00:00Z",
  },
  {
    id: "2",
    title: "Implement user authentication",
    content: "Develop the login, registration, and password reset functionalities for the backend and frontend.",
    status: "To Do",
    created_at: "2024-01-16T11:30:00Z",
  },
  {
    id: "3",
    title: "Write API documentation",
    content: "Document all API endpoints, request/response formats, and authentication requirements using Swagger/OpenAPI.",
    status: "Completed",
    created_at: "2024-01-10T09:00:00Z",
  },
  {
    id: "4",
    title: "Set up CI/CD pipeline",
    content: "Configure GitHub Actions for automated testing and deployment to staging environment.",
    status: "To Do",
    created_at: "2024-01-18T14:00:00Z",
  },
  {
    id: "5",
    title: "Review sprint backlog",
    content: "Prioritize remaining tasks for the next sprint and refine estimates with the team.",\    status: "In Progress",
    created_at: "2024-01-17T16:00:00Z",
  },
];

export const mockTaskStats = {
  total: mockTasks.length,
  toDo: mockTasks.filter((x) => x.status === "To Do").length,
  inProgress: mockTasks.filter((x) => x.status === "In Progress").length,
  completed: mockTasks.filter((x) => x.status === "Completed").length,
};
