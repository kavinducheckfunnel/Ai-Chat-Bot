import { reactive } from 'vue'

const state = reactive({ toasts: [] })
let nextId = 1

function add(message, type = 'info', duration = 4000) {
  const id = nextId++
  state.toasts.push({ id, message, type })
  if (duration > 0) {
    setTimeout(() => remove(id), duration)
  }
  return id
}

function remove(id) {
  const idx = state.toasts.findIndex(t => t.id === id)
  if (idx !== -1) state.toasts.splice(idx, 1)
}

export function useToast() {
  return {
    toasts: state.toasts,
    success: (msg) => add(msg, 'success'),
    error:   (msg) => add(msg, 'error', 5000),
    info:    (msg) => add(msg, 'info'),
    warning: (msg) => add(msg, 'warning'),
    remove,
  }
}
