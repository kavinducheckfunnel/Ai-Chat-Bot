import { reactive } from 'vue'

const state = reactive({
  visible: false,
  message: '',
  resolve: null,
})

export function useConfirm() {
  function confirm(message) {
    state.message = message
    state.visible = true
    return new Promise((resolve) => {
      state.resolve = resolve
    })
  }

  function respond(value) {
    state.visible = false
    if (state.resolve) {
      state.resolve(value)
      state.resolve = null
    }
  }

  return { state, confirm, respond }
}
