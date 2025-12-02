<template>
  <div id="app">
    <router-view />
    <!-- Toast notifications globales -->
    <ToastContainer />
  </div>
</template>

<script setup>
import ToastContainer from '@/components/common/ToastContainer.vue'
</script>

<style scoped>
#app {
  min-height: 100vh;
}
</style>
