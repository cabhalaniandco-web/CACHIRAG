import { useCallback, useMemo, useState } from "react";
import {
  STORAGE_KEY,
  type Filter,
  type Priority,
  type Todo,
  type TodoDraft,
  clearCompleted,
  createTodo,
  deleteTodo,
  filterTodos,
  parseStoredTodos,
  sortTodos,
  statsFor,
  todayISO,
  toggleTodo,
  updateTodo,
} from "./todos";

function loadTodos(): Todo[] {
  try {
    return parseStoredTodos(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return [];
  }
}

function persist(todos: Todo[]): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
}

export function useTodos() {
  const [todos, setTodos] = useState<Todo[]>(() => loadTodos());
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const today = todayISO();

  const commit = useCallback((next: Todo[]) => {
    setTodos(next);
    persist(next);
  }, []);

  const add = useCallback(
    (draft: TodoDraft) => {
      commit([createTodo(draft), ...todos]);
    },
    [commit, todos],
  );

  const toggle = useCallback(
    (id: string) => commit(toggleTodo(todos, id)),
    [commit, todos],
  );

  const update = useCallback(
    (
      id: string,
      patch: Partial<Pick<Todo, "title" | "dueDate" | "priority">>,
    ) => commit(updateTodo(todos, id, patch)),
    [commit, todos],
  );

  const remove = useCallback(
    (id: string) => commit(deleteTodo(todos, id)),
    [commit, todos],
  );

  const clearDone = useCallback(
    () => commit(clearCompleted(todos)),
    [commit, todos],
  );

  const visible = useMemo(
    () => sortTodos(filterTodos(todos, filter, query), today),
    [todos, filter, query, today],
  );

  const stats = useMemo(() => statsFor(todos, today), [todos, today]);

  return {
    todos,
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
  };
}

export type { Priority };
