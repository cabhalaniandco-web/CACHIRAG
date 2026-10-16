# TDL

**TDL** is a focused to-do list. Add a task, set a due date and priority if you need them, then check it off.

Tasks stay in this browser (`localStorage`). There is no account and no server.

## Run it

```bash
npm install
npm run dev
```

Open http://localhost:5173.

| Command | What it does |
| --- | --- |
| `npm run dev` | Start the app |
| `npm test` | Run the task-logic tests |
| `npm run typecheck` | Typecheck |
| `npm run build` | Production build |

## What you can do

- Add a task with **Enter** or the **Add** button
- Click a title to rename it (**Enter** saves, **Escape** cancels)
- Check a box to complete it, **Delete** to remove it
- Filter **All / Open / Done**, and search by title
- **Clear completed** when you are done reviewing them
- Overdue and due-today labels use your local date, not UTC
