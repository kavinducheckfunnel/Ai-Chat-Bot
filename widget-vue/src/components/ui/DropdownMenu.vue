<template>
  <div class="relative inline-block text-left" ref="container">
    <div @click="toggle">
      <slot name="trigger" />
    </div>
    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <div
        v-if="open"
        :class="cn('absolute z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md', alignClass, props.class)"
      >
        <slot />
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  align: { type: String, default: 'end' },
  class: { type: String, default: '' },
})

const open = ref(false)
const container = ref(null)

const alignClass = computed(() =>
  props.align === 'start' ? 'left-0 top-full mt-1' : 'right-0 top-full mt-1'
)

function toggle() { open.value = !open.value }

function handleClickOutside(e) {
  if (container.value && !container.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>
