export type Priority = "none" | "low" | "medium" | "high";
export type Filter = "all" | "active" | "completed";

export interface Todo {
  id: string;
  title: string;
  done: boolean;
  createdAt: number;
  updatedAt: number;
  dueDate: string | null;
  priority: Priority;
}

export interface TodoDraft {
  title: string;
  dueDate?: string | null;
  priority?: Priority;
}

export interface TodoStats {
  total: number;
  active: number;
  completed: number;
  overdue: number;
}

export const STORAGE_KEY = "tdl.todos.v1";
export const PRIORITIES: Priority[] = ["none", "low", "medium", "high"];
export const FILTERS: Filter[] = ["all", "active", "completed"];

export function todayISO(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `tdl-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createTodo(draft: TodoDraft, now = Date.now()): Todo {
  const title = draft.title.trim();
  if (!title) {
    throw new Error("A task needs a title.");
  }
  return {
    id: createId(),
    title,
    done: false,
    createdAt: now,
    updatedAt: now,
    dueDate: normalizeDueDate(draft.dueDate ?? null),
    priority: draft.priority ?? "none",
  };
}

export function toggleTodo(todos: Todo[], id: string, now = Date.now()): Todo[] {
  return todos.map((todo) =>
    todo.id === id ? { ...todo, done: !todo.done, updatedAt: now } : todo,
  );
}

export function updateTodo(
  todos: Todo[],
  id: string,
  patch: Partial<Pick<Todo, "title" | "dueDate" | "priority">>,
  now = Date.now(),
): Todo[] {
  return todos.map((todo) => {
    if (todo.id !== id) return todo;
    const title = patch.title !== undefined ? patch.title.trim() : todo.title;
    if (!title) {
      throw new Error("A task needs a title.");
    }
    return {
      ...todo,
      title,
      dueDate:
        patch.dueDate !== undefined
          ? normalizeDueDate(patch.dueDate)
          : todo.dueDate,
      priority: patch.priority ?? todo.priority,
      updatedAt: now,
    };
  });
}

export function deleteTodo(todos: Todo[], id: string): Todo[] {
  return todos.filter((todo) => todo.id !== id);
}

export function clearCompleted(todos: Todo[]): Todo[] {
  return todos.filter((todo) => !todo.done);
}

export function isOverdue(todo: Todo, today = todayISO()): boolean {
  return !todo.done && todo.dueDate !== null && todo.dueDate < today;
}

export function isDueToday(todo: Todo, today = todayISO()): boolean {
  return !todo.done && todo.dueDate === today;
}

export function filterTodos(
  todos: Todo[],
  filter: Filter,
  query = "",
): Todo[] {
  const needle = query.trim().toLowerCase();
  return todos.filter((todo) => {
    if (filter === "active" && todo.done) return false;
    if (filter === "completed" && !todo.done) return false;
    if (needle && !todo.title.toLowerCase().includes(needle)) return false;
    return true;
  });
}

export function sortTodos(todos: Todo[], today = todayISO()): Todo[] {
  const rank: Record<Priority, number> = {
    high: 0,
    medium: 1,
    low: 2,
    none: 3,
  };
  return [...todos].sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1;
    const aOverdue = isOverdue(a, today) ? 0 : 1;
    const bOverdue = isOverdue(b, today) ? 0 : 1;
    if (aOverdue !== bOverdue) return aOverdue - bOverdue;
    if (rank[a.priority] !== rank[b.priority]) {
      return rank[a.priority] - rank[b.priority];
    }
    if (a.dueDate !== b.dueDate) {
      if (a.dueDate === null) return 1;
      if (b.dueDate === null) return -1;
      return a.dueDate.localeCompare(b.dueDate);
    }
    return b.createdAt - a.createdAt;
  });
}

export function statsFor(todos: Todo[], today = todayISO()): TodoStats {
  return {
    total: todos.length,
    active: todos.filter((todo) => !todo.done).length,
    completed: todos.filter((todo) => todo.done).length,
    overdue: todos.filter((todo) => isOverdue(todo, today)).length,
  };
}

export function parseStoredTodos(raw: string | null): Todo[] {
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  return parsed.filter(isTodo);
}

function isTodo(value: unknown): value is Todo {
  if (typeof value !== "object" || value === null) return false;
  const todo = value as Record<string, unknown>;
  return (
    typeof todo.id === "string" &&
    typeof todo.title === "string" &&
    typeof todo.done === "boolean" &&
    typeof todo.createdAt === "number" &&
    typeof todo.updatedAt === "number" &&
    (todo.dueDate === null || typeof todo.dueDate === "string") &&
    (todo.priority === "none" ||
      todo.priority === "low" ||
      todo.priority === "medium" ||
      todo.priority === "high")
  );
}

function normalizeDueDate(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(trimmed) ? trimmed : null;
}

export function formatDueLabel(dueDate: string, today = todayISO()): string {
  if (dueDate === today) return "Today";
  const tomorrow = shiftISO(today, 1);
  if (dueDate === tomorrow) return "Tomorrow";
  const yesterday = shiftISO(today, -1);
  if (dueDate === yesterday) return "Yesterday";
  const [year, month, day] = dueDate.split("-").map(Number);
  if (!year || !month || !day) return dueDate;
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: year === new Date().getFullYear() ? undefined : "numeric",
  });
}

function shiftISO(iso: string, days: number): string {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(year ?? 0, (month ?? 1) - 1, (day ?? 1) + days);
  return todayISO(date);
}
