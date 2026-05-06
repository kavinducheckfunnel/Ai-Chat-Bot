<template>
  <td :class="cn('p-4 align-middle [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]', props.class)" v-bind="$attrs"><slot /></td>
</template>
<script setup>
import { cn } from '@/lib/utils'
defineOptions({ inheritAttrs: false })
const props = defineProps({ class: { type: String, default: '' } })
</script>
