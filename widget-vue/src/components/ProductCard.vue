<template>
  <div class="cf-product-card">
    <img src="https://via.placeholder.com/300x150?text=Product+Image" alt="Product Image">
    <h4>Recommended Product Special</h4>
    <p>Based on your intent, we think you'll love this offer. Limited time pricing applies.</p>
    <button @click="addToCart">Add to Cart - $199</button>
  </div>
</template>

<script setup>
import { defineProps } from 'vue';

const props = defineProps({
  productId: {
    type: [Number, String],
    required: true
  }
});

const addToCart = () => {
  alert(`Proceeding to checkout for product ID: ${props.productId}`);
};
</script>

<style scoped>
.cf-product-card {
  border: 1px solid #eaeaea;
  border-radius: 12px;
  padding: 15px;
  margin-top: 5px;
  background: white;
  text-align: center;
  box-shadow: 0 4px 15px rgba(0,0,0,0.05);
}
.cf-product-card img {
  max-width: 100%;
  border-radius: 8px;
  margin-bottom: 10px;
}
.cf-product-card h4 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 16px;
}
.cf-product-card p {
  margin: 0 0 15px 0;
  color: #666;
  font-size: 13px;
  line-height: 1.4;
}
.cf-product-card button {
  background: #28a745;
  color: white;
  border: none;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  width: 100%;
  font-weight: 600;
  font-size: 14px;
  transition: background 0.2s;
}
.cf-product-card button:hover {
  background: #218838;
}
</style>
