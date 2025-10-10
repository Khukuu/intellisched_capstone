const downloadBtn = document.getElementById('downloadBtn');
const submitBtn = document.getElementById('submitBtn');
downloadBtn.disabled = true;

const scheduleSection = document.getElementById('schedule-section');
const dataManagementSection = document.getElementById('data-management-section');
const scheduleNavLink = document.getElementById('scheduleNavLink');
const dataNavLink = document.getElementById('dataNavLink');

// Navigation functions
function showSection(sectionId) {
  if (scheduleSection) scheduleSection.style.display = 'none';
  if (dataManagementSection) dataManagementSection.style.display = 'none';
  
  const targetSection = document.getElementById(sectionId);
  if (targetSection) targetSection.style.display = 'block';
}

// Navigation event listeners
if (scheduleNavLink) {
  scheduleNavLink.addEventListener('click', (e) => {
    e.preventDefault();
    showSection('schedule-section');
  });
}

if (dataNavLink) {
  dataNavLink.addEventListener('click', (e) => {
    e.preventDefault();
    showSection('data-management-section');
  });
}

// Simple generate button test
const generateBtn = document.getElementById('generateBtn');
if (generateBtn) {
  generateBtn.onclick = function() {
    alert('Generate button clicked!');
    document.getElementById('result').innerHTML = '<div class="alert alert-success">SUCCESS: Generate button is working!</div>';
    return false;
  };
}

// Basic utility functions
function elValue(el) {
  return el ? el.value : '';
}

function getAuthHeaders() {
  // Try different possible token keys
  const token = localStorage.getItem('auth_token') || 
                localStorage.getItem('authToken') || 
                localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : ''
  };
}

// Basic table loading functions (simplified)
async function loadRoomsTable() {
  try {
    const response = await fetch('/data/rooms', { headers: getAuthHeaders() });
    if (response.ok) {
      const data = await response.json();
      console.log('Rooms loaded:', data.length);
    }
  } catch (e) {
    console.warn('Could not load rooms:', e);
  }
}

async function loadTeachersTable() {
  try {
    const response = await fetch('/data/teachers', { headers: getAuthHeaders() });
    if (response.ok) {
      const data = await response.json();
      console.log('Teachers loaded:', data.length);
    }
  } catch (e) {
    console.warn('Could not load teachers:', e);
  }
}

async function loadSubjectsTable() {
  try {
    const response = await fetch('/data/cs_curriculum', { headers: getAuthHeaders() });
    if (response.ok) {
      const data = await response.json();
      console.log('CS subjects loaded:', data.length);
    }
  } catch (e) {
    console.warn('Could not load CS subjects:', e);
  }
  
  try {
    const response = await fetch('/data/it_curriculum', { headers: getAuthHeaders() });
    if (response.ok) {
      const data = await response.json();
      console.log('IT subjects loaded:', data.length);
    }
  } catch (e) {
    console.warn('Could not load IT subjects:', e);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  console.log('Script loaded successfully');
  
  // Debug authentication
  const token = localStorage.getItem('auth_token') || 
                localStorage.getItem('authToken') || 
                localStorage.getItem('token');
  console.log('Auth token found:', token ? 'Yes' : 'No');
  console.log('Available localStorage keys:', Object.keys(localStorage));
  
  loadRoomsTable();
  loadTeachersTable();
  loadSubjectsTable();
});
