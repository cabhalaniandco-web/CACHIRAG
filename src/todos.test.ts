import { describe, expect, it } from "vitest";
import {
  clearCompleted,
  createTodo,
  deleteTodo,
  filterTodos,
  formatDueLabel,
  isOverdue,
  parseStoredTodos,
  sortTodos,
  statsFor,
  todayISO,
  toggleTodo,
  updateTodo,
} from "./todos";

const TODAY = "2026-10-16";

function task(
  title: string,
  extras: Partial<{
    done: boolean;
    dueDate: string | null;
    priority: "none" | "low" | "medium" | "high";
    createdAt: number;
  }> = {},
) {
  const todo = createTodo(
    {
      title,
      dueDate: extras.dueDate ?? null,
      priority: extras.priority ?? "none",
    },
    extras.createdAt ?? 1,
  );
  return extras.done ? { ...todo, done: true } : todo;
}

describe("createTodo", () => {
  it("trims the title and defaults optional fields", () => {
    const todo = createTodo({ title: "  File GSTR-3B  " }, 42);
    expect(todo.title).toBe("File GSTR-3B");
    expect(todo.done).toBe(false);
    expect(todo.dueDate).toBeNull();
    expect(todo.priority).toBe("none");
    expect(todo.createdAt).toBe(42);
    expect(todo.id).toBeTruthy();
  });

  it("rejects a blank title", () => {
    expect(() => createTodo({ title: "   " })).toThrow(/title/i);
  });
});

describe("mutations", () => {
  it("toggles completion", () => {
    const todos = [task("A")];
    const toggled = toggleTodo(todos, todos[0]!.id, 99);
    expect(toggled[0]!.done).toBe(true);
    expect(toggled[0]!.updatedAt).toBe(99);
    expect(toggleTodo(toggled, todos[0]!.id)[0]!.done).toBe(false);
  });

  it("updates title, due date, and priority", () => {
    const todos = [task("Draft")];
    const updated = updateTodo(todos, todos[0]!.id, {
      title: "  File return  ",
      dueDate: "2026-10-20",
      priority: "high",
    });
    expect(updated[0]).toMatchObject({
      title: "File return",
      dueDate: "2026-10-20",
      priority: "high",
    });
  });

  it("deletes a task and clears completed ones", () => {
    const a = task("Keep");
    const b = task("Done", { done: true });
    expect(deleteTodo([a, b], a.id)).toEqual([b]);
    expect(clearCompleted([a, b])).toEqual([a]);
  });
});

describe("filter, sort, and stats", () => {
  const active = task("Call client", { priority: "high", createdAt: 1 });
  const overdue = task("Bank rec", {
    dueDate: "2026-10-10",
    priority: "medium",
    createdAt: 2,
  });
  const done = task("Invoice", { done: true, createdAt: 3 });

  it("filters by status and search query", () => {
    const todos = [active, overdue, done];
    expect(filterTodos(todos, "active").map((t) => t.title)).toEqual([
      "Call client",
      "Bank rec",
    ]);
    expect(filterTodos(todos, "completed").map((t) => t.title)).toEqual([
      "Invoice",
    ]);
    expect(filterTodos(todos, "all", "bank").map((t) => t.title)).toEqual([
      "Bank rec",
    ]);
  });

  it("sorts open tasks before done, overdue first, then priority", () => {
    const later = task("Later", { priority: "high", createdAt: 0 });
    const ordered = sortTodos([done, later, overdue, active], TODAY);
    expect(ordered.map((t) => t.title)).toEqual([
      "Bank rec",
      "Call client",
      "Later",
      "Invoice",
    ]);
    // Same priority, no due date: newer createdAt comes first.
  });

  it("counts active, completed, and overdue tasks", () => {
    expect(statsFor([active, overdue, done], TODAY)).toEqual({
      total: 3,
      active: 2,
      completed: 1,
      overdue: 1,
    });
  });
});

describe("dates and storage", () => {
  it("treats past due dates on open tasks as overdue", () => {
    expect(isOverdue(task("Late", { dueDate: "2026-10-15" }), TODAY)).toBe(
      true,
    );
    expect(isOverdue(task("Today", { dueDate: TODAY }), TODAY)).toBe(false);
    expect(
      isOverdue(task("Done late", { dueDate: "2026-10-01", done: true }), TODAY),
    ).toBe(false);
  });

  it("labels nearby due dates in plain language", () => {
    expect(formatDueLabel(TODAY, TODAY)).toBe("Today");
    expect(formatDueLabel("2026-10-17", TODAY)).toBe("Tomorrow");
    expect(formatDueLabel("2026-10-15", TODAY)).toBe("Yesterday");
  });

  it("round-trips valid stored todos and ignores junk", () => {
    const todo = createTodo({ title: "Keep me", dueDate: TODAY }, 7);
    const done = { ...todo, id: "done-1", done: true, title: "Already done" };
    expect(parseStoredTodos(JSON.stringify([todo, done]))).toEqual([todo, done]);
    expect(parseStoredTodos("not-json")).toEqual([]);
    expect(parseStoredTodos(JSON.stringify([{ title: "nope" }]))).toEqual([]);
  });

  it("formats today as a local ISO date", () => {
    expect(todayISO(new Date(2026, 9, 16))).toBe("2026-10-16");
  });
});
