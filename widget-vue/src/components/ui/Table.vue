<template>
  <div class="relative w-full overflow-auto">
    <table :class="cn('w-full caption-bottom text-sm', props.class)" v-bind="$attrs">
      <slot />
    </table>
  </div>
</template>
<script setup>
import { cn } from '@/lib/utils'
defineOptions({ inheritAttrs: false })
const props = defineProps({ class: { type: String, default: '' } })
</script>
