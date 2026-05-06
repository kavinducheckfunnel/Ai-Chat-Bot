<template>
  <div :class="cn('', props.class)" v-bind="$attrs">
    <slot />
  </div>
</template>
<script setup>
import { cn } from '@/lib/utils'
import { provide, ref } from 'vue'
defineOptions({ inheritAttrs: false })
const props = defineProps({
  modelValue: { type: String, default: '' },
  class: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
const active = ref(props.modelValue)
provide('tabs', {
  active,
  setActive: (val) => { active.value = val; emit('update:modelValue', val) },
})
</script>
