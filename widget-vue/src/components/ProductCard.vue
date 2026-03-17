<template>
  <div class="cf-product-card">
    <div v-if="loading" class="cf-product-loading">
      <span class="cf-spinner"></span>
    </div>
    <template v-else-if="product">
      <img v-if="product.image_url" :src="product.image_url" :alt="product.title" class="cf-product-img" />
      <div v-else class="cf-product-img-placeholder">🛍️</div>
      <div class="cf-product-body">
        <h4 class="cf-product-title">{{ product.title }}</h4>
        <p v-if="product.description" class="cf-product-desc">{{ product.description }}</p>
        <div class="cf-product-footer">
          <span v-if="product.price" class="cf-product-price">{{ product.price }}</span>
          <a
            v-if="product.url"
            :href="product.url"
            target="_blank"
            rel="noopener noreferrer"
            class="cf-product-btn"
          >
            View Product →
          </a>
        </div>
      </div>
    </template>
    <div v-else class="cf-product-error">Could not load product.</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const props = defineProps({
  productId: { type: [Number, String], required: true },
  clientId:  { type: String, default: null },
});

const loading = ref(true);
const product = ref(null);

function getApiBase() {
  const h = window.location.hostname;
  return (h === 'localhost' || h === '127.0.0.1') ? 'http://127.0.0.1:8000' : '';
}

onMounted(async () => {
  try {
    const res = await fetch(`${getApiBase()}/api/chat/product/${props.productId}/`);
    if (res.ok) {
      product.value = await res.json();
    }
  } catch { /* leave product null → shows error state */ }
  loading.value = false;
});
</script>

<style scoped>
.cf-product-card {
  border: 1px solid #e8ecef;
  border-radius: 14px;
  overflow: hidden;
  background: white;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
  max-width: 280px;
  font-family: inherit;
}
.cf-product-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
}
.cf-spinner {
  width: 22px; height: 22px;
  border: 3px solid #e1e5ea;
  border-top-color: #3B82F6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
.cf-product-img {
  width: 100%;
  height: 150px;
  object-fit: cover;
  display: block;
}
.cf-product-img-placeholder {
  width: 100%;
  height: 100px;
  background: linear-gradient(135deg, #f0f4ff, #e8ecff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
}
.cf-product-body { padding: 14px; }
.cf-product-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.3;
}
.cf-product-desc {
  margin: 0 0 12px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.cf-product-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.cf-product-price {
  font-size: 15px;
  font-weight: 700;
  color: #16a34a;
}
.cf-product-btn {
  background: #3B82F6;
  color: white;
  border: none;
  padding: 7px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.2s;
  white-space: nowrap;
}
.cf-product-btn:hover { opacity: 0.88; }
.cf-product-error { padding: 16px; font-size: 13px; color: #94a3b8; text-align: center; }
</style>
