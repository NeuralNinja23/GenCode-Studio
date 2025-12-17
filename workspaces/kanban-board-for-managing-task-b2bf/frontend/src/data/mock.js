export const mockAssignees = [
  { id: "1", name: "Alice", avatar: "https://api.dicebear.com/7.x/initials/svg?seed=Alice" },
  { id: "2", name: "Bob", avatar: "https://api.dicebear.com/7.x/initials/svg?seed=Bob" },
  { id: "3", name: "Charlie", avatar: "https://api.dicebear.com/7.x/initials/svg?seed=Charlie" }
];

export const mockTags = [
  { id: "1", name: "Design", color: "bg-blue-500" },
  { id: "2", name: "Frontend", color: "bg-green-500" },
  { id: "3", name: "Backend", color: "bg-purple-500" },
  { id: "4", name: "Urgent", color: "bg-red-500" }
];

export const mockTasks = [
  {
    id: "1",
    title: "Design homepage mockup",
    description: "Create initial wireframes and high-fidelity mockups for the new homepage layout.",
    status: "Backlog",
    priority: "High",
    assignee: mockAssignees[0],
    dueDate: "2024-07-20",
    tags: [mockTags[0], mockTags[3]],
    subtasks: { completed: 2, total: 5 },
    created_at: "2024-07-01T10:00:00Z"
  },
  {
    id: "2",
    title: "Implement user authentication",
    description: "Develop the login, registration, and password reset functionalities.",
    status: "In Progress",
    priority: "High",
    assignee: mockAssignees[1],
    dueDate: "2024-07-25",
    tags: [mockTags[1], mockTags[2]],
    subtasks: { completed: 3, total: 4 },
    created_at: "2024-07-03T11:30:00Z"
  },
  {
    id: "3",
    title: "Review API documentation",
    description: "Go through the existing API endpoints and ensure they are well-documented.",
    status: "Review",
    priority: "Medium",
    assignee: mockAssignees[2],
    dueDate: "2024-07-18",
    tags: [mockTags[2]],
    subtasks: { completed: 1, total: 1 },
    created_at: "2024-07-05T09:00:00Z"
  },
  {
    id: "4",
    title: "Deploy to staging environment",
    description: "Prepare and execute the deployment of the latest build to the staging server.",
    status: "Done",
    priority: "Low",
    assignee: mockAssignees[0],
    dueDate: "2024-07-15",
    tags: [],
    subtasks: { completed: 2, total: 2 },
    created_at: "2024-07-07T14:00:00Z"
  },
  {
    id: "5",
    title: "Refactor old components",
    description: "Improve code quality and maintainability of legacy frontend components.",
    status: "Backlog",
    priority: "Medium",
    assignee: mockAssignees[1],
    dueDate: "2024-08-01",
    tags: [mockTags[1]],
    subtasks: { completed: 0, total: 3 },
    created_at: "2024-07-10T16:00:00Z"
  }
];

export const mockTaskStats = {
  total: mockTasks.length,
  backlog: mockTasks.filter(x => x.status === "Backlog").length,
  inProgress: mockTasks.filter(x => x.status === "In Progress").length,
  review: mockTasks.filter(x => x.status === "Review").length,
  done: mockTasks.filter(x => x.status === "Done").length
};

export const mockColumns = [
  { id: "Backlog", title: "Backlog", tasks: mockTasks.filter(t => t.status === "Backlog") },
  { id: "In Progress", title: "In Progress", tasks: mockTasks.filter(t => t.status === "In Progress") },
  { id: "Review", title: "Review", tasks: mockTasks.filter(t => t.status === "Review") },
  { id: "Done", title: "Done", tasks: mockTasks.filter(t => t.status === "Done") }
];
