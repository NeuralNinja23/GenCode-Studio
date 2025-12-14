export const mockTasks = [
  {
    id: "1",
    title: "Plan sprint goals",
    content: "Define objectives and key results for the upcoming sprint.",
    status: "Active",
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(), // 2 days ago
  },
  {
    id: "2",
    title: "Develop user authentication module",
    content: "Implement login, registration, and password reset functionalities.",
    status: "Active",
    created_at: new Date(Date.now() - 86400000 * 1).toISOString(), // 1 day ago
  },
  {
    id: "3",
    title: "Review UI/UX designs for dashboard",
    content: "Provide feedback on the latest Figma mockups for the main dashboard.",
    status: "Pending",
    created_at: new Date(Date.now() - 86400000 * 0.5).toISOString(), // 12 hours ago
  },
  {
    id: "4",
    title: "Write API documentation for tasks endpoint",
    content: "Document all CRUD operations, request/response schemas, and error codes.",
    status: "Completed",
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(), // 3 days ago
  },
  {
    id: "5",
    title: "Set up CI/CD pipeline",
    content: "Configure GitHub Actions for automated testing and deployment.",
    status: "Active",
    created_at: new Date().toISOString(), // Just now
  },
];

export const mockTaskStats = {
  total: mockTasks.length,
  active: mockTasks.filter(x => x.status === "Active").length,
  completed: mockTasks.filter(x => x.status === "Completed").length,
  pending: mockTasks.filter(x => x.status === "Pending").length,
};
