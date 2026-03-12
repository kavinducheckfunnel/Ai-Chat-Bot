<template>
  <ChatWidget />
</template>

<script setup>
import ChatWidget from './components/ChatWidget.vue'
</script>

<style>
/* Reset base vue defaults to not interfere with host website */
#app {
  font-family: inherit;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
