<template>
  <div class="layout">
    <Sidebar />
    <div class="main">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import Sidebar from './Sidebar.vue'
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--cf-bg);
}

.main {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
  background: var(--cf-bg);
}
</style>
