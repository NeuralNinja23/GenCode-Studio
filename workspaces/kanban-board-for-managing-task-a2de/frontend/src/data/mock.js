export const mockAssignees = [
  { id: "a1", name: "Alice", avatar: "https://api.dicebear.com/7.x/initials/svg?seed=Alice" },
  { id: "a2", name: "Bob", avatar: "https://api.dicebear.com/7.x/initials/svg?seed=Bob" },
  { id: "a3", name: "Charlie", avatar: "https://api.dicebear.com/7.x/initials/svg?seed=Charlie" },
];

export const mockTags = [
  { id: "t1", name: "Design", color: "bg-blue-500" },
  { id: "t2", name: "Frontend", color: "bg-green-500" },
  { id: "t3", name: "Backend", color: "bg-purple-500" },
  { id: "t4", name: "Urgent", color: "bg-red-500" },
  { id: "t5", name: "Bug", color: "bg-orange-500" },
];

export const mockTasks = [
  {
    id: "task-1",
    title: "Design homepage mockup",
    description: "Create initial wireframes and high-fidelity mockups for the new homepage layout.",
    status: "backlog",
    priority: "high",
    assignee: mockAssignees[0],
    dueDate: "2024-07-25",
    labels: [mockTags[0], mockTags[3]],
    subtasks: { completed: 2, total: 5 },
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(), // 5 days ago
  },
  {
    id: "task-2",
    title: "Implement user authentication",
    description: "Develop the login, registration, and password reset functionalities.",
    status: "in-progress",
    priority: "high",
    assignee: mockAssignees[1],
    dueDate: "2024-07-20", // Overdue
    labels: [mockTags[1], mockTags[2]],
    subtasks: { completed: 1, total: 3 },
    created_at: new Date(Date.now() - 86400000 * 7).toISOString(), // 7 days ago
  },
  {
    id: "task-3",
    title: "Review API documentation",
    description: "Go through the existing API endpoints and ensure they are well-documented.",
    status: "review",
    priority: "medium",
    assignee: mockAssignees[2],
    dueDate: "2024-07-30",
    labels: [mockTags[2]],
    subtasks: { completed: 0, total: 1 },
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(), // 2 days ago
  },
  {
    id: "task-4",
    title: "Fix responsive layout issues",
    description: "Address reported bugs related to the website's responsiveness on mobile devices.",
    status: "done",
    priority: "medium",
    assignee: mockAssignees[0],
    dueDate: "2024-07-15",
    labels: [mockTags[1], mockTags[4]],
    subtasks: { completed: 3, total: 3 },
    created_at: new Date(Date.now() - 86400000 * 10).toISOString(), // 10 days ago
  },
  {
    id: "task-5",
    title: "Write unit tests for backend",
    description: "Create comprehensive unit tests for the core backend services and models.",
    status: "backlog",
    priority: "low",
    assignee: mockAssignees[1],
    dueDate: "2024-08-01",
    labels: [mockTags[2]],
    subtasks: { completed: 0, total: 4 },
    created_at: new Date(Date.now() - 86400000 * 1).toISOString(), // 1 day ago
  },
  {
    id: "task-6",
    title: "Prepare sprint planning meeting",
    description: "Organize agenda and materials for the upcoming sprint planning session.",
    status: "backlog",
    priority: "medium",
    assignee: mockAssignees[2],
    dueDate: "2024-07-28",
    labels: [],
    subtasks: { completed: 0, total: 2 },
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(), // 3 days ago
  },
  {
    id: "task-7",
    title: "Deploy staging environment",
    description: "Set up and configure the new staging server for testing.",
    status: "in-progress",
    priority: "high",
    assignee: mockAssignees[0],
    dueDate: "2024-07-26",
    labels: [mockTags[2]],
    subtasks: { completed: 0, total: 1 },
    created_at: new Date(Date.now() - 86400000 * 4).toISOString(), // 4 days ago
  }
];

export const mockColumns = [
  { id: "backlog", title: "Backlog", tasks: mockTasks.filter(t => t.status === "backlog") },
  { id: "in-progress", title: "In Progress", tasks: mockTasks.filter(t => t.status === "in-progress") },
  { id: "review", title: "Review", tasks: mockTasks.filter(t => t.status === "review") },
  { id: "done", title: "Done", tasks: mockTasks.filter(t => t.status === "done") },
];

export const mockTaskStats = {
  total: mockTasks.length,
  backlog: mockTasks.filter(x => x.status === "backlog").length,
  inProgress: mockTasks.filter(x => x.status === "in-progress").length,
  review: mockTasks.filter(x => x.status === "review").length,
  done: mockTasks.filter(x => x.status === "done").length,
};

export const mockProjects = [
  { id: "p1", name: "Website Redesign", color: "#3B82F6", taskCount: 24 },
  { id: "p2", name: "Mobile App", color: "#10B981", taskCount: 18 },
  { id: "p3", name: "API Integration", color: "#F59E0B", taskCount: 12 }
];