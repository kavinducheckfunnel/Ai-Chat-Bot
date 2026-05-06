<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" @click="$emit('update:open', false)" />
        <div :class="cn('relative z-50 grid w-full max-w-lg gap-4 border bg-background p-6 shadow-lg duration-200 sm:rounded-lg', props.class)">
          <slot />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
<script setup>
import { cn } from '@/lib/utils'
const props = defineProps({
  open: { type: Boolean, default: false },
  class: { type: String, default: '' },
})
defineEmits(['update:open'])
</script>
