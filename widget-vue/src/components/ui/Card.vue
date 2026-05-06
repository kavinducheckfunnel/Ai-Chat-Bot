<template>
  <div :class="cn('rounded-xl border bg-card text-card-foreground shadow', props.class)" v-bind="$attrs">
    <slot />
  </div>
</template>
<script setup>
import { cn } from '@/lib/utils'
defineOptions({ inheritAttrs: false })
const props = defineProps({ class: { type: String, default: '' } })
</script>
