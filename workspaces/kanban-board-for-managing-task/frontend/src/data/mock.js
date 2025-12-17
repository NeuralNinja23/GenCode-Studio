import { format, isPast } from 'date-fns';

export const mockAssignees = [
  { id: "a1", name: "Alice Johnson", avatar: "https://api.dicebear.com/7.x/lorelei/svg?seed=Alice" },
  { id: "a2", name: "Bob Smith", avatar: "https://api.dicebear.com/7.x/lorelei/svg?seed=Bob" },
  { id: "a3", name: "Charlie Brown", avatar: "https://api.dicebear.com/7.x/lorelei/svg?seed=Charlie" },
  { id: "a4", name: "Diana Prince", avatar: "https://api.dicebear.com/7.x/lorelei/svg?seed=Diana" },
];

export const mockTags = [
  "design", "frontend", "backend", "security", "marketing", "strategy", "database", "management", "planning", "urgent", "bug", "feature"
];

export const mockKanbanColumns = [
  { id: "backlog", title: "Backlog" },
  { id: "in-progress", title: "In Progress" },
  { id: "review", title: "Review" },
  { id: "done", title: "Done" },
];

export const mockTasks = [
  {
    id: "task-1",
    title: "Design homepage mockup",
    description: "Create initial wireframes and high-fidelity mockups for the new website homepage, focusing on user experience and modern aesthetics.",
    status: "in-progress", // backlog, in-progress, review, done
    priority: "high", // high, medium, low
    assignee: mockAssignees[0],
    dueDate: "2024-07-25",
    labels: [mockTags[0], mockTags[1], mockTags[9]],
    subtasks: { completed: 2, total: 5 },
    created_at: new Date('2024-07-10T10:00:00Z').toISOString(),
  },
  {
    id: "task-2",
    title: "Develop user authentication API",
    description: "Implement secure user registration, login, and session management endpoints using FastAPI and MongoDB.", status: "backlog",
    priority: "high",
    assignee: mockAssignees[1],
    dueDate: "2024-08-01",
    labels: [mockTags[2], mockTags[3]],
    subtasks: { completed: 0, total: 3 },
    created_at: new Date('2024-07-12T11:30:00Z').toISOString(),
  },
  {
    id: "task-3",
    title: "Review Q2 marketing strategy",
    description: "Analyze performance of Q2 campaigns and propose adjustments for Q3 based on analytics data.",
    status: "review",
    priority: "medium",
    assignee: mockAssignees[2],
    dueDate: "2024-07-20", // Overdue
    labels: [mockTags[4], mockTags[5]],
    subtasks: { completed: 1, total: 1 },
    created_at: new Date('2024-07-05T09:00:00Z').toISOString(),
  },
  {
    id: "task-4",
    title: "Refactor database schema for performance",
    description: "Optimize existing MongoDB schema for better query performance and scalability, including indexing strategies.",
    status: "done",
    priority: "low",
    assignee: mockAssignees[1],
    dueDate: "2024-07-10",
    labels: [mockTags[2], mockTags[6]],
    subtasks: { completed: 4, total: 4 },
    created_at: new Date('2024-07-01T14:00:00Z').toISOString(),
  },
  {
    id: "task-5",
    title: "Prepare sprint planning meeting agenda",
    description: "Gather all pending tasks, estimate efforts, and prepare a detailed agenda for the next sprint planning session.",
    status: "backlog",
    priority: "medium",
    assignee: mockAssignees[0],
    dueDate: "2024-07-28",
    labels: [mockTags[7], mockTags[8]],
    subtasks: { completed: 0, total: 2 },
    created_at: new Date('2024-07-15T16:00:00Z').toISOString(),
  },
  {
    id: "task-6",
    title: "Fix critical login bug",
    description: "Investigate and resolve the reported issue where users are unable to log in intermittently.",
    status: "in-progress",
    priority: "high",
    assignee: mockAssignees[3],
    dueDate: "2024-07-26",
    labels: [mockTags[2], mockTags[10], mockTags[9]],
    subtasks: { completed: 1, total: 1 },
    created_at: new Date('2024-07-20T09:00:00Z').toISOString(),
  }
];

export const mockTaskStats = {
  total: mockTasks.length,
  backlog: mockTasks.filter(x => x.status === "backlog").length,
  inProgress: mockTasks.filter(x => x.status === "in-progress").length,
  review: mockTasks.filter(x => x.status === "review").length,
  done: mockTasks.filter(x => x.status === "done").length,
  overdue: mockTasks.filter(x => x.dueDate && isPast(new Date(x.dueDate)) && x.status !== 'done').length,
};
