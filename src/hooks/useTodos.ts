import { useEffect, useRef, useState } from 'react'
import type { Todo } from '../types'

const STORAGE_KEY = 'tdl.todos.v1'
const DELETE_COOLDOWN_MS = 450

function loadTodos(): Todo[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Todo[]
    if (!Array.isArray(parsed)) return []
    return parsed
  } catch {
    return []
  }
}

export function useTodos() {
  const [todos, setTodos] = useState<Todo[]>(() => loadTodos())
  const deleteLockUntil = useRef(0)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos))
  }, [todos])

  function addTodo(text: string) {
    const trimmed = text.trim()
    if (!trimmed) return
    setTodos((prev) => [
      {
        id: crypto.randomUUID(),
        text: trimmed,
        done: false,
        createdAt: Date.now(),
      },
      ...prev,
    ])
  }

  function toggleTodo(id: string) {
    setTodos((prev) =>
      prev.map((todo) =>
        todo.id === id ? { ...todo, done: !todo.done } : todo,
      ),
    )
  }

  function editTodo(id: string, text: string) {
    const trimmed = text.trim()
    if (!trimmed) {
      removeTodo(id)
      return
    }
    setTodos((prev) =>
      prev.map((todo) => (todo.id === id ? { ...todo, text: trimmed } : todo)),
    )
  }

  function removeTodo(id: string) {
    // Prevent accidental second deletes when the list shifts under the cursor.
    const now = Date.now()
    if (now < deleteLockUntil.current) return
    deleteLockUntil.current = now + DELETE_COOLDOWN_MS
    setTodos((prev) => prev.filter((todo) => todo.id !== id))
  }

  function clearDone() {
    setTodos((prev) => prev.filter((todo) => !todo.done))
  }

  return { todos, addTodo, toggleTodo, editTodo, removeTodo, clearDone }
}
