import { useEffect, useRef, useState } from 'react'
import type { Todo } from '../types'

type Props = {
  todo: Todo
  onToggle: (id: string) => void
  onEdit: (id: string, text: string) => void
  onRemove: (id: string) => void
  index: number
}

export function TodoItem({ todo, onToggle, onEdit, onRemove, index }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(todo.text)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  function commit() {
    setEditing(false)
    if (draft.trim() !== todo.text) onEdit(todo.id, draft)
    else setDraft(todo.text)
  }

  return (
    <li
      className={`todo-item${todo.done ? ' is-done' : ''}${editing ? ' is-editing' : ''}`}
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <button
        type="button"
        className="check"
        aria-label={todo.done ? 'Mark as active' : 'Mark as done'}
        aria-pressed={todo.done}
        onClick={() => onToggle(todo.id)}
      >
        <span className="check-mark" aria-hidden="true" />
      </button>

      {editing ? (
        <input
          ref={inputRef}
          className="todo-edit"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit()
            if (e.key === 'Escape') {
              setDraft(todo.text)
              setEditing(false)
            }
          }}
        />
      ) : (
        <button
          type="button"
          className="todo-text"
          onDoubleClick={() => {
            setDraft(todo.text)
            setEditing(true)
          }}
        >
          {todo.text}
        </button>
      )}

      <button
        type="button"
        className="remove"
        aria-label={`Remove “${todo.text}”`}
        onClick={() => onRemove(todo.id)}
      >
        <span aria-hidden="true">×</span>
      </button>
    </li>
  )
}
