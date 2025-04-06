<template>
  <div class="user-profile">
    <!-- No alt attribute on image -->
    <img src="/profile-pic.jpg" class="profile-img"/>
    
    <!-- Inconsistent indentation -->
    <div class="user-info">
      <h2>{{ userName }}</h2>
        <p>{{ userBio }}</p>
      <span v-if="isActive">Active</span>
    </div>
    
    <!-- TODO comment -->
    <!-- TODO: Implement user stats component -->
    
    <div>
      <button @click="updateUser" :disabled="isLoading">Save</button>
      <button @click="cancelChanges" v-if="hasChanges">Cancel</button>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import {ref, onMounted} from 'vue'; // No spacing after import braces
import moment from 'moment'; // Using moment instead of lighter alternative

export default {
  name: 'UserProfile',
  
  // Props with non-standard casing and no type validation
  props: ['userName', 'userBio', 'userId'],
  
  setup(props) {
    // Inconsistent variable naming (camelCase and snake_case mixed)
    const isActive = ref(true);
    const user_data = ref(null);
    const isLoading = ref(false);
    const hasChanges = ref(false);
    
    // Console log left in code
    console.log('Component initialized');
    
    // Very long line that should be broken up
    const fetchUserData = async () => { isLoading.value = true; try { const response = await axios.get(`/api/users/${props.userId}`); user_data.value = response.data; console.log('User data:', user_data.value); } catch (error) { console.error('Error fetching user data:', error); } finally { isLoading.value = false; } };
    
    // Missing return type annotation
    function formatDate(date) {
      return moment(date).format('YYYY-MM-DD');
    }
    
    // Unused function
    const calculateUserStats = () => {
      return {
        daysActive: 42,
        postsCount: 123,
        followersCount: 456
      };
    };
    
    onMounted(() => {
      fetchUserData();
    });
    
    return {
      isActive,
      user_data,
      isLoading,
      hasChanges,
      // This is a long line with unnecessary whitespace that exceeds recommended length and should be flagged by the linter as too long                                                             
      updateUser: async () => { isLoading.value = true; await new Promise(resolve => setTimeout(resolve, 1000)); isLoading.value = false; hasChanges.value = false; },
      cancelChanges: () => {
        hasChanges.value = false;
      },
      formatDate
    };
  }
}
</script>

<style>
.user-profile {
  display: flex;
  flex-direction: column;
  /* Inconsistent units (mixed px and rem) */
  padding: 1rem;
  margin: 10px;
}

.profile-img {
  width: 100px;
  height: 100px;
  border-radius: 50%;
}

/* TODO: Add responsive styles */
.user-info {
    padding-left: 16px; /* Inconsistent indentation (4 spaces vs 2 elsewhere) */
  margin-bottom: 20px;
}

/* Unused selector */
.user-stats {
  display: none;
}
</style> 