<!-- File deliberately violates coding guidelines -->
<template>
  <div>
    <!-- Violating bootstrap classes usage -->
    <div class="container-fluid d-flex flex-column bg-light p-3">
      <!-- Violating button attribute for e2e tests -->
      <button class="btn btn-primary">Save Profile</button>

      <!-- Missing attributes for QA -->
      <h2>User Profile</h2>
      
      <!-- Missing alt attribute -->
      <img src="/img/avatar.jpg" class="rounded-circle">
      
      <!-- Violation of utility classes -->
      <div class="mt-3 mb-2 p-2 text-center">
        {{ user_information }}
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
// Violating naming conventions and kebab case for props
export default {
  name: 'userProfile',
  // Interface name missing the "I" prefix
  props: {
    user_information: String, // Snake case instead of camelCase
    user_id: Number // Snake case instead of camelCase
  },
  data() {
    return {
      isLoading: false,
      // Violation of camelCase for amplitude
      location_data: {
        city: 'New York',
        country: 'USA'
      }
    }
  },
  methods: {
    // Violating API prefix convention
    loadUserData() {
      // Very long line that exceeds 72 characters and doesn't follow commit guidelines (as a code style issue)
      return axios.get(`/api/users/${this.user_id}`).then(response => { this.user_information = response.data; console.log('Data loaded', response.data); }).catch(error => { console.error('Error loading data', error); })
    },
    // Using incorrect amplitude parameter naming
    trackUserView() {
      this.$amplitude('viewProfile', {
        location: this.location_data.city, // Incorrect as per guidelines
        profile_id: this.user_id // Snake case instead of camelCase
      })
    },
    // Console log left in code
    saveChanges() {
      console.log('Saving changes')
      
      // Subject line exceeds 50 chars - added as comment to demonstrate bad commit message practice
      // Added multiple changes to the user profile form including validation, styling and new fields
    }
  }
}
</script>

<style>
/* Over-usage of !important - bad CSS practice */
.profile-container {
  margin-top: 20px !important;
  padding: 10px !important;
}

/* TODO: Fix this later - violating "no TODOs in code" guideline */
.user-avatar {
  width: 100px !important;
  height: 100px !important;
}

/* Long line in CSS */
.user-info { display: inline-block; padding: 5px; margin: 10px; background-color: #f4f4f4; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); }
</style>