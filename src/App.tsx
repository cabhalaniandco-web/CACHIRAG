import { useMemo, useState, type FormEvent } from 'react'
import { TodoItem } from './components/TodoItem'
import { useTodos } from './hooks/useTodos'
import type { Filter } from './types'

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'active', label: 'Active' },
  { id: 'done', label: 'Done' },
]

export default function App() {
  const { todos, addTodo, toggleTodo, editTodo, removeTodo, clearDone } =
    useTodos()
  const [filter, setFilter] = useState<Filter>('all')
  const [draft, setDraft] = useState('')

  const visible = useMemo(() => {
    if (filter === 'active') return todos.filter((t) => !t.done)
    if (filter === 'done') return todos.filter((t) => t.done)
    return todos
  }, [todos, filter])

  const activeCount = todos.filter((t) => !t.done).length
  const doneCount = todos.length - activeCount

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    addTodo(draft)
    setDraft('')
  }

  return (
    <div className="shell">
      <div className="atmosphere" aria-hidden="true" />
      <div className="grain" aria-hidden="true" />

      <main className="stage">
        <header className="brand-block">
          <p className="brand">TDL</p>
          <h1 className="headline">What needs doing?</h1>
          <p className="lede">Capture it, check it off, keep moving.</p>
        </header>

        <form className="composer" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="new-todo">
            New to-do
          </label>
          <input
            id="new-todo"
            className="composer-input"
            placeholder="Add a task…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoComplete="off"
          />
          <button type="submit" className="composer-btn" disabled={!draft.trim()}>
            Add
          </button>
        </form>

        <section className="board" aria-label="To-do list">
          <div className="toolbar">
            <div className="filters" role="tablist" aria-label="Filter tasks">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  role="tab"
                  aria-selected={filter === f.id}
                  className={`filter${filter === f.id ? ' is-active' : ''}`}
                  onClick={() => setFilter(f.id)}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <p className="count">
              {activeCount === 0
                ? todos.length === 0
                  ? 'No tasks yet'
                  : 'All clear'
                : `${activeCount} left`}
            </p>
          </div>

          {visible.length === 0 ? (
            <p className="empty">
              {todos.length === 0
                ? 'Your list is empty — add something above.'
                : filter === 'done'
                  ? 'Nothing finished yet.'
                  : 'No active tasks.'}
            </p>
          ) : (
            <ul className="todo-list">
              {visible.map((todo, index) => (
                <TodoItem
                  key={todo.id}
                  todo={todo}
                  index={index}
                  onToggle={toggleTodo}
                  onEdit={editTodo}
                  onRemove={removeTodo}
                />
              ))}
            </ul>
          )}

          {doneCount > 0 && (
            <div className="footer-actions">
              <button type="button" className="ghost" onClick={clearDone}>
                Clear {doneCount} done
              </button>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
