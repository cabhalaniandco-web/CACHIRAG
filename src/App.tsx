import { FormEvent, useState } from "react";
import {
  FILTERS,
  PRIORITIES,
  type Filter,
  type Priority,
  type Todo,
  formatDueLabel,
  isDueToday,
  isOverdue,
} from "./todos";
import { useTodos } from "./useTodos";
import "./App.css";

const PRIORITY_LABEL: Record<Priority, string> = {
  none: "No priority",
  low: "Low",
  medium: "Medium",
  high: "High",
};

export default function App() {
  const {
    visible,
    stats,
    filter,
    setFilter,
    query,
    setQuery,
    today,
    add,
    toggle,
    update,
    remove,
    clearDone,
  } = useTodos();
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [priority, setPriority] = useState<Priority>("none");
  const [error, setError] = useState("");

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      add({
        title,
        dueDate: dueDate || null,
        priority,
      });
      setTitle("");
      setDueDate("");
      setPriority("none");
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not add that task.");
    }
  }

  return (
    <main className="shell">
      <header className="letterhead">
        <div>
          <h1 className="mark">TDL</h1>
          <p className="tagline">To-do list. Write it down, then cross it off.</p>
        </div>
        <p className="remaining">
          <strong>{stats.active}</strong>
          {stats.active === 1 ? "open task" : "open tasks"}
        </p>
      </header>

      <form className="composer" onSubmit={onSubmit} aria-label="Add a task">
        <div className="composer-row">
          <input
            className="title-input"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="What needs doing?"
            aria-label="Task title"
            autoComplete="off"
          />
          <button className="add-btn" type="submit">
            Add
          </button>
        </div>
        <div className="composer-meta">
          <label className="field">
            Due
            <input
              type="date"
              value={dueDate}
              onChange={(event) => setDueDate(event.target.value)}
            />
          </label>
          <label className="field">
            Priority
            <select
              value={priority}
              onChange={(event) => setPriority(event.target.value as Priority)}
            >
              {PRIORITIES.map((value) => (
                <option key={value} value={value}>
                  {PRIORITY_LABEL[value]}
                </option>
              ))}
            </select>
          </label>
        </div>
        {error ? <p className="error">{error}</p> : null}
      </form>

      <div className="toolbar">
        <div className="filters" role="group" aria-label="Filter tasks">
          {FILTERS.map((value) => (
            <button
              key={value}
              type="button"
              className="filter"
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
            >
              {filterLabel(value)}
            </button>
          ))}
        </div>
        <input
          className="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search"
          aria-label="Search tasks"
        />
      </div>

      {visible.length === 0 ? (
        <div className="empty">
          <strong>{emptyTitle(filter, query, stats.total)}</strong>
          {emptyCopy(filter, query, stats.total)}
        </div>
      ) : (
        <ul className="list">
          {visible.map((todo) => (
            <TodoRow
              key={todo.id}
              todo={todo}
              today={today}
              onToggle={() => toggle(todo.id)}
              onUpdate={(patch) => update(todo.id, patch)}
              onRemove={() => remove(todo.id)}
            />
          ))}
        </ul>
      )}

      <footer className="footer">
        <span>
          {stats.completed} done
          {stats.overdue ? ` · ${stats.overdue} overdue` : ""}
        </span>
        {stats.completed > 0 ? (
          <button type="button" className="linkish" onClick={clearDone}>
            Clear completed
          </button>
        ) : null}
      </footer>
    </main>
  );
}

function TodoRow({
  todo,
  today,
  onToggle,
  onUpdate,
  onRemove,
}: {
  todo: Todo;
  today: string;
  onToggle: () => void;
  onUpdate: (patch: Partial<Pick<Todo, "title" | "dueDate" | "priority">>) => void;
  onRemove: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(todo.title);
  const overdue = isOverdue(todo, today);
  const dueToday = isDueToday(todo, today);

  function saveTitle() {
    const next = draft.trim();
    if (!next) {
      setDraft(todo.title);
      setEditing(false);
      return;
    }
    if (next !== todo.title) onUpdate({ title: next });
    setEditing(false);
  }

  return (
    <li className={todo.done ? "item done" : "item"}>
      <input
        className="check"
        type="checkbox"
        checked={todo.done}
        onChange={onToggle}
        aria-label={`Mark “${todo.title}” ${todo.done ? "active" : "done"}`}
      />
      <div className="task-main">
        {editing ? (
          <input
            className="edit-title"
            value={draft}
            autoFocus
            aria-label="Edit task title"
            onChange={(event) => setDraft(event.target.value)}
            onBlur={saveTitle}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                saveTitle();
              }
              if (event.key === "Escape") {
                setDraft(todo.title);
                setEditing(false);
              }
            }}
          />
        ) : (
          <button
            type="button"
            className="task-title"
            onClick={() => {
              setDraft(todo.title);
              setEditing(true);
            }}
          >
            {todo.title}
          </button>
        )}
        <div className="meta">
          {todo.dueDate ? (
            <span
              className={
                overdue ? "chip overdue" : dueToday ? "chip today" : "chip"
              }
            >
              {overdue ? "Overdue · " : ""}
              {formatDueLabel(todo.dueDate, today)}
            </span>
          ) : null}
          <label className="field">
            Due
            <input
              type="date"
              aria-label={`Due date for ${todo.title}`}
              value={todo.dueDate ?? ""}
              onChange={(event) =>
                onUpdate({ dueDate: event.target.value || null })
              }
            />
          </label>
          <label className="field">
            Priority
            <select
              aria-label={`Priority for ${todo.title}`}
              value={todo.priority}
              onChange={(event) =>
                onUpdate({ priority: event.target.value as Priority })
              }
            >
              {PRIORITIES.map((value) => (
                <option key={value} value={value}>
                  {PRIORITY_LABEL[value]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <div className="actions">
        <button
          type="button"
          className="icon-btn danger"
          onClick={onRemove}
          aria-label={`Delete ${todo.title}`}
        >
          Delete
        </button>
      </div>
    </li>
  );
}

function filterLabel(filter: Filter): string {
  if (filter === "all") return "All";
  if (filter === "active") return "Open";
  return "Done";
}

function emptyTitle(filter: Filter, query: string, total: number): string {
  if (query.trim()) return "Nothing matches that search.";
  if (total === 0) return "The list is empty.";
  if (filter === "active") return "Everything is done.";
  if (filter === "completed") return "Nothing completed yet.";
  return "No tasks to show.";
}

function emptyCopy(filter: Filter, query: string, total: number): string {
  if (query.trim()) return "Try a different word, or clear the search box.";
  if (total === 0) return "Add the first thing that needs doing.";
  if (filter === "active") return "Clear completed tasks, or add a new one.";
  if (filter === "completed") return "Open tasks stay here until you check them off.";
  return "";
}
