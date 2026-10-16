export type Todo = {
  id: string
  text: string
  done: boolean
  createdAt: number
}

export type Filter = 'all' | 'active' | 'done'
