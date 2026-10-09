<script setup lang="ts">
import { useHealth } from '~/composables/useHealth'

const { data: health, status } = await useHealth()
</script>

<template>
  <p v-if="status === 'pending'" class="text-gray-500">
    Connexion au backend…
  </p>
  <p v-else-if="status === 'error'" class="text-red-700">
    Le backend ne répond pas : lancez-le avec <code>uv run python manage.py runserver</code>.
  </p>
  <p v-else class="text-green-700">
    Backend joignable (statut : {{ health?.status }}).
  </p>
</template>
