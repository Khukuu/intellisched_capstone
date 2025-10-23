const downloadBtn = document.getElementById('downloadBtn');
const submitBtn = document.getElementById('submitBtn');
downloadBtn.disabled = true;

const scheduleSection = document.getElementById('schedule-section');
const dataManagementSection = document.getElementById('data-management-section');
const scheduleNavLink = document.getElementById('scheduleNavLink');
const dataNavLink = document.getElementById('dataNavLink');

const uploadSubjectsForm = document.getElementById('uploadSubjectsForm');
const uploadTeachersForm = document.getElementById('uploadTeachersForm');
const uploadRoomsForm = document.getElementById('uploadRoomsForm');
const uploadSectionsForm = document.getElementById('uploadSectionsForm');

const semesterSelect = document.getElementById('semesterSelect'); // New: Get semester select element
const yearFilter = document.getElementById('yearFilter');
const sectionFilter = document.getElementById('sectionFilter');
const roomFilter = document.getElementById('roomFilter');
const teacherFilter = document.getElementById('teacherFilter');
const saveBtn = document.getElementById('saveBtn');
const saveNameInput = document.getElementById('saveNameInput');
// Saved schedule controls removed - now handled in separate page

// Keep last generated schedule in memory for filtering
let lastGeneratedSchedule = [];
let lastAnalytics = null;
let lastSavedId = '';
let currentRoomFilter = 'all';
let availableRooms = [];

// Cached data for tabs so searches/filtering work reliably
let subjectsCache = []; // Legacy - kept for compatibility
let csSubjectsCache = [];
let itSubjectsCache = [];
let teachersCache = [];
let roomsCache = [];

// Room ID to room name mapping
let roomIdToNameMap = {};

// Function to get room name from room ID
function getRoomName(roomId) {
  if (!roomId) return '';
  return roomIdToNameMap[String(roomId)] || String(roomId);
}

// Authentication helper function
function getAuthHeaders() {
  const token = localStorage.getItem('authToken');
  if (!token) {
    window.location.href = '/login';
    return {};
  }
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

// Enhanced UI feedback functions
function showLoadingState(buttonId, text = 'Processing...') {
  const button = document.getElementById(buttonId);
  if (button) {
    button.disabled = true;
    button.classList.add('loading');
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = text;
  }
}

function hideLoadingState(buttonId, originalText = null) {
  const button = document.getElementById(buttonId);
  if (button) {
    button.disabled = false;
    button.classList.remove('loading');
    button.innerHTML = originalText || button.dataset.originalText || button.innerHTML;
  }
}

function showNotification(message, type = 'info', duration = 5000) {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 500px;';
  
  notification.innerHTML = `
    <i class="bi bi-${getIconForType(type)} me-2"></i>
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  
  document.body.appendChild(notification);
  
  // Auto-remove after duration
  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove();
    }
  }, duration);
}

function getIconForType(type) {
  const icons = {
    'success': 'check-circle',
    'danger': 'exclamation-triangle',
    'warning': 'exclamation-circle',
    'info': 'info-circle'
  };
  return icons[type] || 'info-circle';
}

// Fix notification dropdown responsive positioning
function fixNotificationDropdownResponsive() {
  const dropdown = document.getElementById('notificationDropdownMenu');
  const dropdownToggle = document.getElementById('notificationDropdown');
  
  if (dropdown && dropdownToggle) {
    // Handle dropdown show event
    dropdown.addEventListener('show.bs.dropdown', function() {
      const width = window.innerWidth;
      
      if (width <= 575.98) {
        // Extra small devices (phones)
        this.style.position = 'fixed';
        this.style.top = '70px';
        this.style.right = '10px';
        this.style.left = '10px';
        this.style.minWidth = 'auto';
        this.style.maxWidth = 'none';
        this.style.width = 'auto';
        this.style.zIndex = '1050';
        this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        this.style.maxHeight = '70vh';
        this.style.overflowY = 'auto';
        this.style.fontSize = '0.9rem';
      } else if (width <= 767.98) {
        // Small devices (landscape phones)
        this.style.position = 'fixed';
        this.style.top = '80px';
        this.style.right = '15px';
        this.style.left = '15px';
        this.style.minWidth = 'auto';
        this.style.maxWidth = 'none';
        this.style.width = 'auto';
        this.style.zIndex = '1050';
        this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        this.style.maxHeight = '65vh';
        this.style.overflowY = 'auto';
        this.style.fontSize = '';
      } else if (width <= 991.98) {
        // Medium devices (tablets)
        this.style.position = '';
        this.style.top = '';
        this.style.right = '';
        this.style.left = '';
        this.style.minWidth = '350px';
        this.style.maxWidth = '450px';
        this.style.width = '';
        this.style.zIndex = '';
        this.style.boxShadow = '';
        this.style.maxHeight = '50vh';
        this.style.overflowY = 'auto';
        this.style.fontSize = '';
      } else if (width < 1200) {
        // Large devices (desktops)
        this.style.position = '';
        this.style.top = '';
        this.style.right = '';
        this.style.left = '';
        this.style.minWidth = '450px';
        this.style.maxWidth = '600px';
        this.style.width = '';
        this.style.zIndex = '';
        this.style.boxShadow = '';
        this.style.maxHeight = '500px';
        this.style.overflowY = 'auto';
        this.style.fontSize = '';
      } else {
        // Extra large devices (large desktops)
        this.style.position = '';
        this.style.top = '';
        this.style.right = '';
        this.style.left = '';
        this.style.minWidth = '500px';
        this.style.maxWidth = '700px';
        this.style.width = '';
        this.style.zIndex = '';
        this.style.boxShadow = '';
        this.style.maxHeight = '600px';
        this.style.overflowY = 'auto';
        this.style.fontSize = '';
      }
    });
  }
}

// Initialize responsive dropdown fix
document.addEventListener('DOMContentLoaded', function() {
  fixNotificationDropdownResponsive();
});

function addTooltip(elementId, text) {
  const element = document.getElementById(elementId);
  if (element) {
    element.setAttribute('data-bs-toggle', 'tooltip');
    element.setAttribute('data-bs-placement', 'top');
    element.setAttribute('title', text);
  }
}

// Enhanced error handling
function handleApiError(error, context = 'operation') {
  console.error(`Error in ${context}:`, error);
  
  let message = 'An unexpected error occurred. Please try again.';
  
  if (error.response) {
    // Server responded with error status
    if (error.response.status === 401) {
      message = 'Session expired. Please log in again.';
      setTimeout(() => {
        localStorage.clear();
        window.location.href = '/login';
      }, 2000);
    } else if (error.response.status === 403) {
      message = 'Access denied. You do not have permission for this action.';
    } else if (error.response.status === 500) {
      message = 'Server error. Please try again later.';
    } else if (error.response.data && error.response.data.detail) {
      message = error.response.data.detail;
    }
  } else if (error.request) {
    // Network error
    message = 'Network error. Please check your connection and try again.';
  }
  
  showNotification(message, 'danger');
  return message;
}

// Safe value getter for possibly-null elements
function elValue(el) {
  try { return el ? el.value : null; } catch (e) { return null; }
}

function showSection(sectionId) {
  scheduleSection.style.display = 'none';
  dataManagementSection.style.display = 'none';

  scheduleNavLink.classList.remove('active');
  dataNavLink.classList.remove('active');

  const resultsCard = document.getElementById('results-card');

  if (sectionId === 'schedule-section') {
    scheduleSection.style.display = 'block';
    scheduleNavLink.classList.add('active');
    if (resultsCard) resultsCard.style.display = 'block';
  } else if (sectionId === 'data-management-section') {
    dataManagementSection.style.display = 'block';
    dataNavLink.classList.add('active');
    if (resultsCard) resultsCard.style.display = 'none';
    // Load all data and update cards immediately
    setTimeout(() => {
      loadDataManagementTables();
    }, 100);
  }
}

// Initial display
showSection('schedule-section');

// Load notifications on page load
loadNotifications();

scheduleNavLink.addEventListener('click', (e) => {
  e.preventDefault();
  showSection('schedule-section');
});

dataNavLink.addEventListener('click', (e) => {
  e.preventDefault();
  showSection('data-management-section');
});

// Handle CSV file uploads (each reloads only its active table)
if (uploadSubjectsForm) uploadSubjectsForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('csCurriculumFile');
  await uploadFile(fileInput.files[0], 'cs_curriculum');
  await loadCSSubjectsTable(); // Reload CS subjects after upload
});

const uploadITSubjectsForm = document.getElementById('uploadITSubjectsForm');
if (uploadITSubjectsForm) uploadITSubjectsForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('itCurriculumFile');
  await uploadFile(fileInput.files[0], 'it_curriculum');
  await loadITSubjectsTable(); // Reload IT subjects after upload
});

// Handle program selection to show/hide section controls
function toggleSectionControls() {
  try {
    const csChecked = document.getElementById('programCS')?.checked || false;
    const itChecked = document.getElementById('programIT')?.checked || false;
    const csSectionControls = document.getElementById('csSectionControls');
    const itSectionControls = document.getElementById('itSectionControls');
    
    // Always show section controls container
    const sectionControls = document.getElementById('sectionControls');
    if (sectionControls) {
      sectionControls.style.display = 'block';
    }
    
    // Show/hide program-specific controls based on checkboxes
    if (csSectionControls) {
      csSectionControls.style.display = csChecked ? 'block' : 'none';
    }
    if (itSectionControls) {
      itSectionControls.style.display = itChecked ? 'block' : 'none';
    }
  } catch (error) {
    console.error('Error in toggleSectionControls:', error);
  }
}

// Add event listeners for program checkboxes
document.addEventListener('DOMContentLoaded', function() {
  const csCheckbox = document.getElementById('programCS');
  const itCheckbox = document.getElementById('programIT');
  
  if (csCheckbox) {
    csCheckbox.addEventListener('change', toggleSectionControls);
  }
  if (itCheckbox) {
    itCheckbox.addEventListener('change', toggleSectionControls);
  }
  
  // Initialize section controls visibility
  toggleSectionControls();
});

if (uploadTeachersForm) uploadTeachersForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('teachersFile');
  await uploadFile(fileInput.files[0], 'teachers');
  await loadTeachersTable(); // Reload teachers after upload
});

if (uploadRoomsForm) uploadRoomsForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('roomsFile');
  await uploadFile(fileInput.files[0], 'rooms');
  await loadRoomsTable(); // Reload rooms after upload
});


async function uploadFile(file, filename) {
  if (!file) {
    alert('Please select a file to upload.');
    return;
  }
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`/upload/${filename}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
      },
      body: formData,
    });
    const result = await response.json();
    if (response.ok) {
      alert(result.message);
    } else {
      alert(`Error uploading ${filename}: ${result.error || response.statusText}`);
    }
  } catch (error) {
    console.error('Upload error:', error);
    alert('An error occurred during upload.');
  }
}

// Day and Time Slot labels must match scheduler.py exactly
const dayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];  // No Sunday classes
const timeSlotLabels = [
  "07:00-07:30", "07:30-08:00", "08:00-08:30", "08:30-09:00",
  "09:00-09:30", "09:30-10:00", "10:00-10:30", "10:30-11:00",
  "11:00-11:30", "11:30-12:00", "12:00-12:30", "12:30-13:00",
  "13:00-13:30", "13:30-14:00", "14:00-14:30", "14:30-15:00",
  "15:00-15:30", "15:30-16:00", "16:00-16:30", "16:30-17:00",
  "17:00-17:30", "17:30-18:00"
];

// Timetable subject color mapping helpers
const SUBJECT_COLOR_PALETTE = [
  '#AEC6CF', /* pastel blue */
  '#FFB3BA', /* pastel pink */
  '#FFDFBA', /* pastel peach */
  '#FFFFBA', /* pastel yellow */
  '#BFFCC6', /* pastel green */
  '#CDE7FF', /* baby blue */
  '#E4C1F9', /* pastel lavender */
  '#F1CBFF', /* light mauve */
  '#FDE2E4', /* rose */
  '#E2F0CB', /* light green */
  '#FBE7C6', /* apricot */
  '#D7E3FC', /* periwinkle */
  '#D4F0F0', /* powder */
  '#F6EAC2', /* light sand */
  '#FFD6E0', /* light pink */
  '#C1F9E4', /* mint */
  '#C9C0FF', /* light purple */
  '#BFD1FF'  /* soft blue */
];

// Special colors for laboratory subjects - more vibrant and prominent
const LAB_COLOR_PALETTE = [
  '#FF6B6B', /* vibrant red */
  '#4ECDC4', /* teal */
  '#45B7D1', /* bright blue */
  '#96CEB4', /* mint green */
  '#FFEAA7', /* golden yellow */
  '#DDA0DD', /* medium orchid */
  '#98D8C8', /* turquoise */
  '#F7DC6F', /* bright yellow */
  '#BB8FCE', /* light purple */
  '#85C1E9', /* light blue */
  '#F8C471', /* orange */
  '#82E0AA', /* light green */
  '#F1948A', /* salmon */
  '#85C1E9', /* sky blue */
  '#D7BDE2'  /* light purple */
];

const subjectColorCache = {};
function hashStringToInt(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}
function getSubjectColor(subjectCode, subjectType = null) {
  const key = String(subjectCode || '');
  const cacheKey = `${key}_${subjectType || 'default'}`;
  if (subjectColorCache[cacheKey]) return subjectColorCache[cacheKey];
  
  // Use lab colors for laboratory subjects, regular colors for others
  const palette = (subjectType === 'lab') ? LAB_COLOR_PALETTE : SUBJECT_COLOR_PALETTE;
  const idx = hashStringToInt(key) % palette.length;
  const color = palette[idx];
  subjectColorCache[cacheKey] = color;
  return color;
}
function getTextColorForBackground(hex) {
  // Expect #RRGGBB
  const c = hex.replace('#', '');
  if (c.length !== 6) return '#fff';
  const r = parseInt(c.substr(0,2), 16);
  const g = parseInt(c.substr(2,2), 16);
  const b = parseInt(c.substr(4,2), 16);
  // Relative luminance (sRGB)
  const lum = 0.2126*(r/255) + 0.7152*(g/255) + 0.0722*(b/255);
  return lum > 0.6 ? '#000' : '#fff';
}


// Generate schedule directly using inline inputs
document.getElementById('generateBtn').onclick = async function() {
  try {
    // Show loading state
    showLoadingState('generateBtn', '<i class="bi bi-arrow-clockwise me-2"></i>Generating...');
    
    // Clear previous results
    document.getElementById('result').innerHTML = `
      <div class="placeholder p-4 text-center text-muted" style="display: flex; align-items: center; justify-content: center; min-height: 300px;">
        <div>
          <i class="bi bi-arrow-clockwise" style="font-size: 3rem; opacity: 0.3; animation: spin 1s linear infinite;"></i>
          <p class="mt-3 mb-0">Generating your schedule...</p>
          <p class="small">This may take a few moments</p>
        </div>
      </div>
    `;
    document.getElementById('timetable').innerHTML = `
      <div class="placeholder p-4 text-center text-muted" style="display: flex; align-items: center; justify-content: center; min-height: 300px;">
        <div>
          <i class="bi bi-arrow-clockwise" style="font-size: 3rem; opacity: 0.3; animation: spin 1s linear infinite;"></i>
          <p class="mt-3 mb-0">Processing timetable...</p>
        </div>
      </div>
    `;

    // Get selected programs from checkboxes
    const selectedPrograms = [];
    if (document.getElementById('programCS').checked) selectedPrograms.push('CS');
    if (document.getElementById('programIT').checked) selectedPrograms.push('IT');
    
    const selectedSemester = elValue(document.getElementById('semesterSelect')) || null;
    const requestBody = { 
      programs: selectedPrograms,
      semester: selectedSemester 
    };

    // Collect program-specific section counts
    const programSections = {};
    
    if (selectedPrograms.includes('CS')) {
      programSections['CS'] = {
        1: parseInt(elValue(document.getElementById('csSectionsYear1')) || 0, 10),
        2: parseInt(elValue(document.getElementById('csSectionsYear2')) || 0, 10),
        3: parseInt(elValue(document.getElementById('csSectionsYear3')) || 0, 10),
        4: parseInt(elValue(document.getElementById('csSectionsYear4')) || 0, 10)
      };
    }
    
    if (selectedPrograms.includes('IT')) {
      programSections['IT'] = {
        1: parseInt(elValue(document.getElementById('itSectionsYear1')) || 0, 10),
        2: parseInt(elValue(document.getElementById('itSectionsYear2')) || 0, 10),
        3: parseInt(elValue(document.getElementById('itSectionsYear3')) || 0, 10),
        4: parseInt(elValue(document.getElementById('itSectionsYear4')) || 0, 10)
      };
    }
    
    requestBody.programSections = programSections;

    // Validate that at least one program is selected
    if (selectedPrograms.length === 0) {
      hideLoadingState('generateBtn');
      document.getElementById('result').innerHTML = `
        <div class="card border-0 shadow-sm rounded-3 h-100">
          <div class="card-header bg-light border-0">
            <h5 class="mb-0 fw-semibold">
              <i class="bi bi-exclamation-triangle text-warning me-2"></i>Configuration Required
            </h5>
          </div>
          <div class="card-body p-4">
            <div class="alert alert-warning">
              <i class="bi bi-exclamation-triangle me-2"></i>
              Please select at least one program (CS or IT) to generate a schedule.
            </div>
          </div>
        </div>
      `;
      showNotification('Please select at least one program before generating a schedule.', 'warning');
      return;
    }

  // Pre-validate against curriculum: zero-out years that have no subjects in selected semester
  try {
    // Load subjects from all selected programs
    const allSubjects = [];
    for (const program of selectedPrograms) {
      const curriculumEndpoint = program.toUpperCase() === 'IT' ? '/data/it_curriculum' : '/data/cs_curriculum';
      const subjectsResponse = await fetch(curriculumEndpoint, {
        headers: getAuthHeaders()
      });
    
      if (!subjectsResponse.ok) {
        console.error(`Failed to load subjects for ${program}:`, subjectsResponse.status);
        throw new Error(`Failed to load subjects for ${program}: ${subjectsResponse.status}`);
      }
      
      const subjectsData = await subjectsResponse.json();
      
      if (!Array.isArray(subjectsData)) {
        throw new Error(`Subjects data for ${program} is not an array`);
      }
      
      allSubjects.push(...subjectsData);
    }
    
    const yearsList = allSubjects
      .filter(s => String(s.semester) === String(selectedSemester))
      .map(s => parseInt(s.year_level))
      .filter(n => !isNaN(n));
    const allowedYears = new Set(yearsList);

    const changedYears = [];
    [1, 2, 3, 4].forEach(y => {
      const key = `numSectionsYear${y}`;
      if ((requestBody[key] || 0) > 0 && !allowedYears.has(y)) {
        requestBody[key] = 0;
        const inputEl = document.getElementById(key);
        if (inputEl) inputEl.value = 0;
        changedYears.push(y);
      }
    });

    if (changedYears.length === 4) {
      document.getElementById('result').innerHTML = '<div class="alert alert-warning">No subjects exist for the selected semester across all year levels. Please change the semester or upload curriculum data.</div>';
      if (downloadBtn) downloadBtn.disabled = true;
      return;
    }

    if (changedYears.length > 0) {
      const msg = `Adjusted sections for Year(s) ${changedYears.join(', ')} because no subjects exist for Semester ${selectedSemester}.`;
      document.getElementById('result').innerHTML = `<div class="alert alert-warning">${msg}</div>`;
    }
  } catch (err) {
    console.warn('Pre-validation skipped due to error:', err);
  }

  // Check if any program has any sections selected
  const hasAnySections = Object.values(programSections).some(programSections =>
    Object.values(programSections).some(count => count > 0)
  );
  
  if (!hasAnySections) {
    document.getElementById('result').innerHTML = '<div class="alert alert-info">No sections selected to schedule. Please set at least one section count for any year level.</div>';
    if (downloadBtn) downloadBtn.disabled = true;
    return;
  }

  try {
    // Load rooms data first to populate room mapping
    await loadRoomsTable();
    
    const response = await fetch('/schedule', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(requestBody)
    });
    const data = await response.json();
    const scheduleArray = Array.isArray(data) ? data : Array.isArray(data.schedule) ? data.schedule : [];
    const analytics = data.analytics || null;
    lastGeneratedSchedule = scheduleArray;
    lastAnalytics = analytics;
    lastSavedId = '';

    if (!Array.isArray(scheduleArray) || scheduleArray.length === 0) {
      const noScheduleMsg = "<b>No schedule generated.</b>";
      document.getElementById('result').innerHTML = noScheduleMsg;
      document.getElementById('timetable').innerHTML = "";
      document.getElementById('hybridResult').innerHTML = noScheduleMsg;
      document.getElementById('hybridTimetable').innerHTML = "";
      if (downloadBtn) downloadBtn.disabled = true;
      hideAnalytics();
      return;
    }

    populateFilters(lastGeneratedSchedule);
    populateTeacherFilter(lastGeneratedSchedule);
    renderScheduleAndTimetable(lastGeneratedSchedule, analytics);
      // Saved schedule list refresh moved to separate page
  } catch (e) {
    console.error('Error generating schedule', e);
    document.getElementById('result').innerHTML = '<div class="alert alert-danger">Error generating schedule. See console.</div>';
  } finally {
    hideLoadingState('generateBtn');
  }
  } catch (error) {
    console.error('Error in generate schedule function:', error);
    handleApiError(error, 'schedule generation');
    hideLoadingState('generateBtn');
  }
};

downloadBtn.onclick = async function() {
  if (!downloadBtn.disabled) {
    try {
      const selectedSemester = semesterSelect.value;
      let downloadUrl = '/download_schedule';
      if (lastSavedId) {
        downloadUrl += `?id=${encodeURIComponent(lastSavedId)}`;
      } else if (selectedSemester) {
        downloadUrl += `?semester=${selectedSemester}`;
      }
      
      // Use fetch with authentication headers
      const response = await fetch(downloadUrl, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          showNotification('Authentication required. Please log in again.', 'danger');
        } else {
          showNotification('Failed to download CSV. Please try again.', 'danger');
        }
        return;
      }
      
      // Get the CSV content
      const csvContent = await response.text();
      
      // Create and trigger download
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = 'schedule.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showNotification('CSV file downloaded successfully!', 'success');
    } catch (error) {
      console.error('Error downloading CSV:', error);
      showNotification('Error downloading CSV. Please check your connection.', 'danger');
    }
  }
};

// Save current generated schedule
if (saveBtn) {
  // Repurpose Save button to submit for approval
  saveBtn.addEventListener('click', async () => {
    await submitForApproval();
  });
}

// (modal removed) no delegated handlers needed

// Saved schedule load/delete functionality moved to separate page

// Submit generated schedule for approval (Chair)
async function submitForApproval() {
    if (!Array.isArray(lastGeneratedSchedule) || lastGeneratedSchedule.length === 0) {
      alert('No schedule to submit. Generate a schedule first.');
      return;
    }
    const name = (saveNameInput && saveNameInput.value.trim()) || 'Generated Schedule';
    try {
      const body = {
        name,
        semester: semesterSelect ? semesterSelect.value : undefined,
        schedule: lastGeneratedSchedule,
        numSectionsYear1: parseInt(elValue(document.getElementById('numSectionsYear1')) || 0, 10),
        numSectionsYear2: parseInt(elValue(document.getElementById('numSectionsYear2')) || 0, 10),
        numSectionsYear3: parseInt(elValue(document.getElementById('numSectionsYear3')) || 0, 10),
        numSectionsYear4: parseInt(elValue(document.getElementById('numSectionsYear4')) || 0, 10)
      };
      const resp = await fetch('/schedules/generate', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Failed to submit schedule');
      }
      lastSavedId = data.id || '';
      alert('Schedule submitted for approval.');
      // Saved schedule list refresh moved to separate page
    } catch (e) {
      console.error(e);
      alert('Error submitting schedule.');
    }
}

// Saved schedule list functionality moved to separate page


function populateFilters(data) {
  // Extract available years from section IDs (format CS{year}{letter} or IT{year}{letter})
  const years = new Set();
  const sectionsByYear = new Map();
  data.forEach(e => {
    const match = /^(CS|IT)(\d)/.exec(e.section_id || '');
    if (match) {
      const y = match[2];
      years.add(y);
      if (!sectionsByYear.has(y)) sectionsByYear.set(y, new Set());
      sectionsByYear.get(y).add(e.section_id);
    }
  });

  // Enable/disable year filter options based on presence
  Array.from(yearFilter.options).forEach(opt => {
    if (opt.value === 'all') return;
    opt.disabled = !years.has(opt.value);
  });

  // If current selection is disabled, reset to 'all'
  if (yearFilter.selectedOptions[0] && yearFilter.selectedOptions[0].disabled) {
    yearFilter.value = 'all';
  }

  // Rebuild sectionFilter based on selected year
  rebuildSectionFilter(sectionsByYear);
  
  // Rebuild roomFilter based on available rooms
  rebuildRoomFilter();
}

function rebuildSectionFilter(sectionsByYear) {
  const selectedYear = yearFilter.value;
  sectionFilter.innerHTML = '';
  const defaultOpt = document.createElement('option');
  defaultOpt.value = 'all';
  defaultOpt.textContent = 'All Sections';
  sectionFilter.appendChild(defaultOpt);

  let sectionSet = new Set();
  if (selectedYear === 'all') {
    // union of all
    sectionsByYear.forEach(set => set.forEach(s => sectionSet.add(s)));
  } else if (sectionsByYear.has(selectedYear)) {
    sectionSet = sectionsByYear.get(selectedYear);
  }

  Array.from(sectionSet).sort().forEach(sec => {
    const opt = document.createElement('option');
    opt.value = sec;
    opt.textContent = sec;
    sectionFilter.appendChild(opt);
  });

  sectionFilter.disabled = sectionFilter.options.length <= 1;
  sectionFilter.value = 'all';
}

function rebuildRoomFilter() {
  if (!roomFilter) {
    console.error('Room filter element not found');
    return;
  }
  
  // Build display list using schedule rooms (names) if present, else all rooms from DB
  const roomsFromSchedule = new Set();
  lastGeneratedSchedule.forEach(e => {
    if (e.room_id) {
      roomsFromSchedule.add(getRoomName(e.room_id));
    }
  });
  if (roomsFromSchedule.size > 0) {
    availableRooms = Array.from(roomsFromSchedule).sort();
  } else {
    const names = new Set();
    (roomsCache || []).forEach(r => {
      const name = (r && (r.room_name || r.room_id)) || '';
      if (name) names.add(name);
    });
    availableRooms = Array.from(names).sort();
  }
  
  // Clear existing options except "All Rooms"
  roomFilter.innerHTML = '<option value="all" selected>All Rooms</option>';
  
  // Add room options
  availableRooms.forEach(room => {
    const option = document.createElement('option');
    option.value = room;
    option.textContent = room;
    roomFilter.appendChild(option);
  });
  
  // Enable/disable the filter
  roomFilter.disabled = availableRooms.length === 0;
}



yearFilter.addEventListener('change', () => {
  // Rebuild section list based on year
  const sectionsByYear = new Map();
  lastGeneratedSchedule.forEach(e => {
    const match = /^(CS|IT)(\d)/.exec(e.section_id || '');
    if (match) {
      const y = match[2];
      if (!sectionsByYear.has(y)) sectionsByYear.set(y, new Set());
      sectionsByYear.get(y).add(e.section_id);
    }
  });
  rebuildSectionFilter(sectionsByYear);
  rebuildRoomFilter();
  renderScheduleAndTimetable(lastGeneratedSchedule, lastAnalytics);
});

sectionFilter.addEventListener('change', () => {
  renderScheduleAndTimetable(lastGeneratedSchedule, lastAnalytics);
});

// Room filter event listeners
roomFilter.addEventListener('change', () => {
  renderScheduleAndTimetable(lastGeneratedSchedule, lastAnalytics);
});



function applyFilters(data) {
  const y = yearFilter.value;
  const s = sectionFilter.value;
  const r = roomFilter.value;
  const t = teacherFilter ? teacherFilter.value : 'all';
  return data.filter(e => {
    let ok = true;
    if (y !== 'all') {
      const m = /^(CS|IT)(\d)/.exec(e.section_id || '');
      ok = ok && m && m[2] === y;
    }
    if (s !== 'all') ok = ok && e.section_id === s;
    if (r !== 'all') {
      const evName = getRoomName(e.room_id);
      ok = ok && (String(e.room_id) === String(r) || String(evName) === String(r));
    }
    if (t !== 'all') ok = ok && e.teacher_name === t;
    return ok;
  });
}

function renderScheduleAndTimetable(data, analytics = null) {
  const filtered = applyFilters(Array.isArray(data) ? data : []);

  // Schedule Table (side-by-side column)
  let html = '<div class="table-responsive"><table class="table table-striped"><thead><tr><th>Section ID</th><th>Subject</th><th>Type</th><th>Teacher</th><th>Room</th><th>Day</th><th>Time</th></tr></thead><tbody>';
  for (const row of filtered) {
    const subj = row.subject_name || row.subject_code || '';
    const timeRange = computeEventTimeRange(row);
    html += `<tr>
      <td>${row.section_id}</td>
      <td>${subj}</td>
      <td>${row.type}</td>
      <td>${row.teacher_name}</td>
      <td>${getRoomName(row.room_id)}</td>
      <td>${row.day}</td>
      <td>${timeRange}</td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  // Update both individual tabs and hybrid view
  const resultDiv = document.getElementById('result');
  const hybridResultDiv = document.getElementById('hybridResult');
  if (resultDiv) {
    resultDiv.innerHTML = html;
  }
  if (hybridResultDiv) {
    hybridResultDiv.innerHTML = html;
  }
  downloadBtn.disabled = filtered.length === 0;

  // Timetable (right) - Advanced rendering with proper rowspan and overlapping events
  const timetable = Array.from({length: timeSlotLabels.length}, () => Array.from({length: dayLabels.length}, () => []));
  
  // Populate the timetable with all events
  filtered.forEach(event => {
    const dayIdx = dayLabels.indexOf(event.day);
    const startSlotIdx = timeSlotLabels.indexOf(event.start_time_slot);
    const duration = parseInt(event.duration_slots, 10) || 1;
    
    if (dayIdx !== -1 && startSlotIdx !== -1) {
      // Add event to all time slots it occupies
      for (let i = 0; i < duration && startSlotIdx + i < timeSlotLabels.length; i++) {
        timetable[startSlotIdx + i][dayIdx].push(event);
      }
    }
  });
  
  // Create a map to track which cells should be skipped (due to rowspan)
  const skipCells = new Set();
  
  let tthtml = '<div class="table-responsive"><table class="table table-bordered"><thead><tr><th>Time Slot</th>';
  for (const day of dayLabels) tthtml += `<th>${day}</th>`;
  tthtml += '</tr></thead><tbody>';
  
  for (let t = 0; t < timeSlotLabels.length; t++) {
    tthtml += `<tr><th>${timeSlotLabels[t]}</th>`;
    for (let d = 0; d < dayLabels.length; d++) {
      const cellKey = `${t}-${d}`;
      
      // Skip this cell if it's already occupied by a rowspan from above
      if (skipCells.has(cellKey)) {
        continue;
      }
      
      // Find ALL events that START at this time slot and day (including overlapping ones)
      const eventsStartingHere = filtered.filter(event => {
        const dayIdx = dayLabels.indexOf(event.day);
        const startSlotIdx = timeSlotLabels.indexOf(event.start_time_slot);
        return dayIdx === d && startSlotIdx === t;
      });
      
      if (eventsStartingHere.length > 0) {
        // Remove duplicates based on section + subject + day
        const uniqueEvents = [];
        const seenEvents = new Set();
        eventsStartingHere.forEach(event => {
          const key = `${event.section_id}-${event.subject_code}-${event.day}-${event.start_time_slot}`;
          if (!seenEvents.has(key)) {
            uniqueEvents.push(event);
            seenEvents.add(key);
          }
        });
        
        if (uniqueEvents.length > 0) {
          // Calculate the maximum duration among all events in this slot
          const maxDuration = Math.max(...uniqueEvents.map(e => parseInt(e.duration_slots, 10) || 1));
          
          // Handle different numbers of overlapping events differently
          if (uniqueEvents.length === 1) {
            // Single event - apply background directly to td like dean interface
            const event = uniqueEvents[0];
            const eventDuration = parseInt(event.duration_slots, 10) || 1;
            const subj = event.subject_name || event.subject_code || '';
            const range = computeEventTimeRange(event);
            const bg = getSubjectColor(event.subject_code, event.type);
            const fg = getTextColorForBackground(bg);
            
            // Mark cells below as occupied by this specific event's rowspan
            for (let i = 1; i < eventDuration && t + i < timeSlotLabels.length; i++) {
              skipCells.add(`${t + i}-${d}`);
            }
            
            tthtml += `<td rowspan="${eventDuration}" style="background:${bg}; color:${fg}; padding:6px 8px; vertical-align: top;">
              <b>${subj}</b><br>
              <small style="opacity:.85;">(${range})</small><br>
              <small>${event.section_id}</small><br>
              <small>${event.teacher_name}</small><br>
              <small>${getRoomName(event.room_id)}</small>
            </td>`;
          } else {
            // 2+ events - use expandable summary for better readability
            // Mark cells below as occupied by this rowspan
            for (let i = 1; i < maxDuration && t + i < timeSlotLabels.length; i++) {
              skipCells.add(`${t + i}-${d}`);
            }
            
            tthtml += `<td rowspan="${maxDuration}" style="vertical-align: top; padding: 1px;">`;
            
            uniqueEvents.forEach((event, index) => {
              const subj = event.subject_name || event.subject_code || '';
              const range = computeEventTimeRange(event);
              const eventBg = getSubjectColor(event.subject_code, event.type);
              const eventFg = getTextColorForBackground(eventBg);
              
              tthtml += `<div style="background:${eventBg}; color:${eventFg}; padding:3px 5px; border-radius:3px; margin:2px 0; font-size:9px; line-height:1.2; border-left: 3px solid ${eventBg};">
                <b>${subj}</b><br>
                <small style="opacity:.85;">(${range})</small><br>
                <small>${event.section_id} • ${event.teacher_name}</small><br>
                <small>${getRoomName(event.room_id)}</small>
              </div>`;
            });
            
            tthtml += `</td>`;
          }
        } else {
          tthtml += '<td></td>';
        }
      } else {
        tthtml += '<td></td>';
      }
    }
    tthtml += '</tr>';
  }
  tthtml += '</tbody></table></div>';
  // Update both individual tabs and hybrid view
  const timetableDiv = document.getElementById('timetable');
  const hybridTimetableDiv = document.getElementById('hybridTimetable');
  if (timetableDiv) {
    timetableDiv.innerHTML = tthtml;
  }
  if (hybridTimetableDiv) {
    hybridTimetableDiv.innerHTML = tthtml;
  }
  // View toggle handling removed - now using tabs
  
  // Display analytics if available
  if (analytics) {
    displayAnalytics(analytics, false); // Don't switch tabs when filtering
  } else {
    hideAnalytics();
  }
}

// Build a readable time range from start slot and duration (e.g., 08:00-10:00)
function computeEventTimeRange(event) {
  const startIdx = timeSlotLabels.indexOf(event.start_time_slot);
  const dur = parseInt(event.duration_slots, 10) || 0;
  if (startIdx < 0 || dur <= 0) return event.start_time_slot || '';
  const startStart = (event.start_time_slot || '').split('-')[0];
  const endIdx = Math.min(timeSlotLabels.length - 1, startIdx + dur - 1);
  const endEnd = (timeSlotLabels[endIdx] || '').split('-')[1] || '';
  return `${startStart}-${endEnd}`;
}

// Apply current view mode to show only one view and expand its column
function applyViewMode() {
  const resultCol = document.getElementById('result');
  const timetableCol = document.getElementById('timetable');
  if (!resultCol || !timetableCol) return;

  // Reset classes
  resultCol.classList.remove('col-md-12');
  timetableCol.classList.remove('col-md-12');
  resultCol.classList.add('col-md-6');
  timetableCol.classList.add('col-md-6');

  if (viewMode && viewMode.value === 'timetable') {
    resultCol.style.display = 'none';
    timetableCol.style.display = 'block';
    timetableCol.classList.remove('col-md-6');
    timetableCol.classList.add('col-md-12');
  } else if (viewMode && viewMode.value === 'list') {
    resultCol.style.display = 'block';
    timetableCol.style.display = 'none';
    resultCol.classList.remove('col-md-6');
    resultCol.classList.add('col-md-12');
  } else { // both
    resultCol.style.display = 'block';
    timetableCol.style.display = 'block';
    resultCol.classList.remove('col-md-12');
    timetableCol.classList.remove('col-md-12');
    resultCol.classList.add('col-md-6');
    timetableCol.classList.add('col-md-6');
  }
}

// Teacher filter functionality
function populateTeacherFilter(scheduleData) {
  if (!teacherFilter || !scheduleData) return;
  
  // Get unique teachers from schedule data
  const teachers = [...new Set(scheduleData.map(item => item.teacher_name).filter(name => name))];
  
  // Clear existing options except "All Teachers"
  teacherFilter.innerHTML = '<option value="all" selected>All Teachers</option>';
  
  // Add teacher options
  teachers.sort().forEach(teacher => {
    const option = document.createElement('option');
    option.value = teacher;
    option.textContent = teacher;
    teacherFilter.appendChild(option);
  });
  
  // Enable the filter
  teacherFilter.disabled = false;
}

// Teacher filter change handler
if (teacherFilter) {
  teacherFilter.addEventListener('change', () => {
    if (lastGeneratedSchedule) {
      renderScheduleAndTimetable(lastGeneratedSchedule, lastAnalytics);
    }
  });
}


// Lazy-load per-tab data loaders
async function loadSubjectsTable() {
  // Check if the subject elements exist before loading
  const csElement = document.getElementById('csSubjectsData');
  const itElement = document.getElementById('itSubjectsData');
  
  if (csElement) {
    await loadCSSubjectsTable();
  }
  if (itElement) {
    await loadITSubjectsTable();
  }
}

async function loadCSSubjectsTable() {
  try {
    const subjectsResponse = await fetch('/data/cs_curriculum', {
      headers: getAuthHeaders()
    });
    if (!subjectsResponse.ok) throw new Error('Failed to load CS subjects');
    csSubjectsCache = await subjectsResponse.json();
    renderTable(csSubjectsCache, 'csSubjectsData', ['subject_code', 'subject_name', 'lecture_hours_per_week', 'lab_hours_per_week', 'units', 'semester', 'program_specialization', 'year_level']);
  } catch (e) {
    console.warn('Could not load CS subjects:', e);
    const element = document.getElementById('csSubjectsData');
    if (element) {
      element.innerHTML = '<p>No CS data available.</p>';
    }
  }
  // Attach client-side search handler
  const sInput = document.getElementById('csSubjectsSearch');
  if (sInput) {
    sInput.oninput = () => filterTable('csSubjectsData', csSubjectsCache, ['subject_code', 'subject_name']);
  }
}

async function loadITSubjectsTable() {
  try {
    const subjectsResponse = await fetch('/data/it_curriculum', {
      headers: getAuthHeaders()
    });
    if (!subjectsResponse.ok) throw new Error('Failed to load IT subjects');
    itSubjectsCache = await subjectsResponse.json();
    renderTable(itSubjectsCache, 'itSubjectsData', ['subject_code', 'subject_name', 'lecture_hours_per_week', 'lab_hours_per_week', 'units', 'semester', 'program_specialization', 'year_level']);
  } catch (e) {
    console.warn('Could not load IT subjects:', e);
    const element = document.getElementById('itSubjectsData');
    if (element) {
      element.innerHTML = '<p>No IT data available.</p>';
    }
  }
  // Attach client-side search handler
  const sInput = document.getElementById('itSubjectsSearch');
  if (sInput) {
    sInput.oninput = () => filterTable('itSubjectsData', itSubjectsCache, ['subject_code', 'subject_name']);
  }
}

async function loadTeachersTable() {
  try {
    const teachersResponse = await fetch('/data/teachers', {
      headers: getAuthHeaders()
    });
    if (!teachersResponse.ok) throw new Error('Failed to load teachers');
    teachersCache = await teachersResponse.json();
    renderTable(teachersCache, 'teachersData', ['teacher_id', 'teacher_name', 'can_teach', 'availability_days']);
  } catch (e) {
    console.warn('Could not load teachers:', e);
    document.getElementById('teachersData').innerHTML = '<p>No data available.</p>';
  }
  const tInput = document.getElementById('teachersSearch');
  if (tInput) {
    tInput.oninput = () => filterTable('teachersData', teachersCache, ['teacher_id', 'teacher_name', 'can_teach', 'availability_days']);
  }
}

async function loadRoomsTable() {
  try {
    const roomsResponse = await fetch('/data/rooms', {
      headers: getAuthHeaders()
    });
    if (!roomsResponse.ok) throw new Error('Failed to load rooms');
    roomsCache = await roomsResponse.json();
    // Build mapping id -> name
    roomIdToNameMap = {};
    if (Array.isArray(roomsCache)) {
      roomsCache.forEach(r => {
        if (r && r.room_id) {
          roomIdToNameMap[String(r.room_id)] = r.room_name || r.room_id;
        }
      });
    }
    renderTable(roomsCache, 'roomsData', ['room_id', 'room_name', 'is_laboratory']);
  } catch (e) {
    console.warn('Could not load rooms:', e);
    document.getElementById('roomsData').innerHTML = '<p>No data available.</p>';
  }
  const rInput = document.getElementById('roomsSearch');
  if (rInput) {
    rInput.oninput = () => filterTable('roomsData', roomsCache, ['room_id', 'room_name']);
  }
}


function filterTable(elementId, data, searchableFields) {
  const input = document.getElementById(elementId.replace('Data','Search')) || document.querySelector(`#${elementId.split('Data')[0]}Search`);
  const q = (input && input.value || '').trim().toLowerCase();
  if (!q) {
  // show full
  if (elementId === 'subjectsData' || elementId === 'csSubjectsData' || elementId === 'itSubjectsData') renderTable(data, elementId, ['subject_code', 'subject_name', 'lecture_hours_per_week', 'lab_hours_per_week', 'units', 'semester', 'program_specialization', 'year_level']);
  else if (elementId === 'teachersData') renderTable(data, elementId, ['teacher_id', 'teacher_name', 'can_teach']);
  else if (elementId === 'roomsData') renderTable(data, elementId, ['room_id', 'room_name', 'is_laboratory']);
  return;
}
const filtered = data.filter(row => searchableFields.some(field => String(row[field] || '').toLowerCase().includes(q)));
// reuse renderTable but with filtered data
if (elementId === 'subjectsData' || elementId === 'csSubjectsData' || elementId === 'itSubjectsData') renderTable(filtered, elementId, ['subject_code', 'subject_name', 'lecture_hours_per_week', 'lab_hours_per_week', 'units', 'semester', 'program_specialization', 'year_level']);
else if (elementId === 'teachersData') renderTable(filtered, elementId, ['teacher_id', 'teacher_name', 'can_teach']);
  else if (elementId === 'roomsData') renderTable(filtered, elementId, ['room_id', 'room_name', 'is_laboratory']);
}

async function updateDataManagementCards() {
  try {
    // Try to get data from API first
    let subjectsCount = 0;
    let teachersCount = 0;
    let roomsCount = 0;

    // Update subjects count
    try {
      const subjectsResponse = await fetch('/api/subjects', {
        headers: getAuthHeaders()
      });
      if (subjectsResponse.ok) {
        const subjectsData = await subjectsResponse.json();
        console.log('Subjects data:', subjectsData);
        const subjects = Array.isArray(subjectsData) ? subjectsData : (subjectsData.subjects || []);
        subjectsCount = subjects.length;
      }
    } catch (error) {
      console.error('Error fetching subjects:', error);
    }

    // Update teachers count
    try {
      const teachersResponse = await fetch('/api/teachers', {
        headers: getAuthHeaders()
      });
      if (teachersResponse.ok) {
        const teachersData = await teachersResponse.json();
        console.log('Teachers data:', teachersData);
        const teachers = Array.isArray(teachersData) ? teachersData : (teachersData.teachers || []);
        teachersCount = teachers.length;
      }
    } catch (error) {
      console.error('Error fetching teachers:', error);
    }

    // Update rooms count
    try {
      const roomsResponse = await fetch('/api/rooms', {
        headers: getAuthHeaders()
      });
      if (roomsResponse.ok) {
        const roomsData = await roomsResponse.json();
        console.log('Rooms data:', roomsData);
        const rooms = Array.isArray(roomsData) ? roomsData : (roomsData.rooms || []);
        roomsCount = rooms.length;
      }
    } catch (error) {
      console.error('Error fetching rooms:', error);
    }

    // Fallback: try to count from cached data if API calls failed
    if (subjectsCount === 0 && (csSubjectsCache.length > 0 || itSubjectsCache.length > 0)) {
      subjectsCount = csSubjectsCache.length + itSubjectsCache.length;
      console.log('Using cached subjects data:', subjectsCount);
    }

    if (teachersCount === 0 && teachersCache.length > 0) {
      teachersCount = teachersCache.length;
      console.log('Using cached teachers data:', teachersCount);
    }

    if (roomsCount === 0 && roomsCache.length > 0) {
      roomsCount = roomsCache.length;
      console.log('Using cached rooms data:', roomsCount);
    }

    // Final fallback: count from table rows if all else fails
    if (teachersCount === 0) {
      const teachersTable = document.querySelector('#teachersData table tbody');
      if (teachersTable) {
        const teacherRows = teachersTable.querySelectorAll('tr');
        teachersCount = teacherRows.length;
        console.log('Using table row count for teachers:', teachersCount);
      }
    }

    if (subjectsCount === 0) {
      const csSubjectsTable = document.querySelector('#csSubjectsData table tbody');
      const itSubjectsTable = document.querySelector('#itSubjectsData table tbody');
      let csCount = 0;
      let itCount = 0;
      
      if (csSubjectsTable) {
        csCount = csSubjectsTable.querySelectorAll('tr').length;
      }
      if (itSubjectsTable) {
        itCount = itSubjectsTable.querySelectorAll('tr').length;
      }
      
      subjectsCount = csCount + itCount;
      if (subjectsCount > 0) {
        console.log('Using table row count for subjects:', subjectsCount);
      }
    }

    if (roomsCount === 0) {
      const roomsTable = document.querySelector('#roomsData table tbody');
      if (roomsTable) {
        const roomRows = roomsTable.querySelectorAll('tr');
        roomsCount = roomRows.length;
        console.log('Using table row count for rooms:', roomsCount);
      }
    }

    // Update the display
    document.getElementById('totalSubjects').textContent = subjectsCount;
    document.getElementById('totalTeachers').textContent = teachersCount;
    document.getElementById('totalRooms').textContent = roomsCount;

  } catch (error) {
    console.error('Error updating data management cards:', error);
    // Set to 0 if there's an error
    document.getElementById('totalSubjects').textContent = '0';
    document.getElementById('totalTeachers').textContent = '0';
    document.getElementById('totalRooms').textContent = '0';
  }
}

async function loadDataManagementTables() {
  // Load all data to populate cards immediately
  await Promise.all([
    loadSubjectsTable(),
    loadTeachersTable(),
    loadRoomsTable()
  ]);
  
  // Update cards after loading all data
  await updateDataManagementCards();
}

// Wire tab buttons to load content when activated (use Bootstrap event)
document.querySelectorAll('#dataTabs button[data-bs-toggle="tab"]').forEach(btn => {
  btn.addEventListener('shown.bs.tab', (e) => {
    const tab = e.target.dataset.tab;
    if (tab === 'subjects') {
      // Small delay to ensure DOM is rendered
      setTimeout(async () => {
        await loadSubjectsTable();
        await updateDataManagementCards();
      }, 100);
    }
    else if (tab === 'teachers') {
      loadTeachersTable().then(() => updateDataManagementCards());
    }
    else if (tab === 'rooms') {
      loadRoomsTable().then(() => updateDataManagementCards());
    }
  });
});

// Wire refresh buttons
['subjects','teachers','rooms'].forEach(key => {
  const btn = document.getElementById(`${key}Refresh`);
  if (btn) btn.addEventListener('click', async () => {
    if (key === 'subjects') {
      await loadSubjectsTable();
      await updateDataManagementCards();
    }
    if (key === 'teachers') {
      await loadTeachersTable();
      await updateDataManagementCards();
    }
    if (key === 'rooms') {
      await loadRoomsTable();
      await updateDataManagementCards();
    }
  });
});

function renderTable(data, elementId, headers) {
  const hasData = Array.isArray(data) && data.length > 0;
  let tableHtml = '<table class="table table-striped table-bordered selectable-table"><thead><tr>';
  // selection checkbox column
  tableHtml += '<th style="width:36px;"><input type="checkbox" class="form-check-input" data-role="select-all"></th>';
  headers.forEach(header => { tableHtml += `<th>${header}</th>`; });
  tableHtml += '</tr></thead><tbody>';
  if (hasData) {
    data.forEach(row => {
      tableHtml += '<tr>';
      tableHtml += '<td><input type="checkbox" class="form-check-input" data-role="row-select"></td>';
      headers.forEach(header => { 
        let value = row[header];
        if (Array.isArray(value)) {
          value = value.join(', ');
        }
        tableHtml += `<td>${value}</td>`; 
      });
      tableHtml += '</tr>';
    });
  } else {
    tableHtml += `<tr><td colspan="${headers.length + 1}" class="text-center text-muted">No data available.</td></tr>`;
  }
  tableHtml += '</tbody></table>';
  const element = document.getElementById(elementId);
  if (!element) {
    console.error(`Element with ID '${elementId}' not found`);
    return;
  }
  element.innerHTML = tableHtml;
  // enable row selection
  const container = document.getElementById(elementId);
  const rows = container.querySelectorAll('tbody tr');
  rows.forEach(tr => {
    tr.addEventListener('click', () => {
      rows.forEach(r => r.classList.remove('table-active'));
      tr.classList.add('table-active');
    });
  });
  // select-all checkbox
  const selectAll = container.querySelector('thead input[data-role="select-all"]');
  if (selectAll) {
    selectAll.addEventListener('change', (e) => {
      const checks = container.querySelectorAll('tbody input[data-role="row-select"]');
      checks.forEach(c => c.checked = selectAll.checked);
    });
  }
}

document.addEventListener('DOMContentLoaded', function() {
  const token = localStorage.getItem('authToken');
  if (!token) {
    window.location.href = '/login';
    return;
  }

  // Check user role - only chair users should access this page
  const userRole = localStorage.getItem('role');
  if (userRole !== 'chair') {
    alert('Access denied. This area is only accessible to Chair users.');
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    window.location.href = '/login';
    return;
  }

  // Update navbar with user info
  const username = localStorage.getItem('username');
  if (username) {
    const logoutBtn = document.getElementById('logoutBtn');
    logoutBtn.innerHTML = `<i class="bi bi-person"></i> ${username} (Chair) <i class="bi bi-box-arrow-right ms-1"></i> Logout`;
  }

  // Update profile section
  const profileUsername = document.getElementById('profile-username');
  const profileRole = document.getElementById('profile-role');
  if (profileUsername) profileUsername.textContent = username || 'User';
  if (profileRole) {
    profileRole.textContent = 'Chair';
    profileRole.className = 'badge bg-success'; // Green badge for chair role
  }
  
  // Load rooms data to populate room mapping
  loadRoomsTable();
  // Hook up CRUD action buttons
  setupCrudButtons();
  
  // Initialize tooltips
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
  
  // Initial view mode removed - now using tabs
});

function getSelectedRowData(elementId, headers) {
  const container = document.getElementById(elementId);
  if (!container) return null;
  const trs = Array.from(container.querySelectorAll('tbody tr')).filter(tr => tr.querySelector('input[data-role="row-select"]')?.checked);
  if (trs.length === 0) return [];
  return trs.map(tr => {
    const tds = Array.from(tr.querySelectorAll('td'));
    const data = {};
    // offset by 1 due to checkbox column
    headers.forEach((h, idx) => { data[h] = (tds[idx + 1] && tds[idx + 1].textContent) || ''; });
    return data;
  });
}

function promptForData(fields, initial = {}) {
  const result = {};
  
  // Field labels for better user experience
  const fieldLabels = {
    'teacher_name': 'Teacher Name',
    'can_teach': 'Subjects (comma-separated)',
    'availability_days': 'Available Days (comma-separated: Mon,Tue,Wed,Thu,Fri,Sat)',
    'room_name': 'Room Name',
    'is_laboratory': 'Is Laboratory? (yes/no)',
    'subject_code': 'Subject Code',
    'subject_name': 'Subject Name',
    'lecture_hours_per_week': 'Lecture Hours per Week',
    'lab_hours_per_week': 'Lab Hours per Week',
    'units': 'Units',
    'semester': 'Semester',
    'program_specialization': 'Program Specialization',
    'year_level': 'Year Level'
  };
  
  for (const f of fields) {
    const label = fieldLabels[f] || f;
    let initialValue = '';
    if (initial[f] != null) {
      if (Array.isArray(initial[f])) {
        initialValue = initial[f].join(',');
      } else {
        initialValue = String(initial[f]);
      }
    }
    const val = prompt(`Enter ${label}:`, initialValue);
    if (val === null) return null;
    result[f] = val;
  }
  return result;
}

function setupCrudButtons() {

  // CS Subjects
  const csSubAdd = document.getElementById('csSubjectsAdd');
  const csSubEdit = document.getElementById('csSubjectsEdit');
  const csSubDel = document.getElementById('csSubjectsDelete');
  if (csSubAdd) csSubAdd.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const data = promptForData(fields);
    if (!data) return;
    data.lecture_hours_per_week = data.lecture_hours_per_week ? parseInt(data.lecture_hours_per_week, 10) : 0;
    data.lab_hours_per_week = data.lab_hours_per_week ? parseInt(data.lab_hours_per_week, 10) : 0;
    data.units = data.units ? parseInt(data.units, 10) : 0;
    data.semester = data.semester ? parseInt(data.semester, 10) : null;
    data.year_level = data.year_level ? parseInt(data.year_level, 10) : null;
    await fetch('/api/subjects', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    loadCSSubjectsTable();
  };
  if (csSubEdit) csSubEdit.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const selected = getSelectedRowData('csSubjectsData', fields);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('subjects', fields, selected);
  };
  if (csSubDel) csSubDel.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const selected = getSelectedRowData('csSubjectsData', fields);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    if (!confirm(`Delete ${selected.length} CS subject(s)?`)) return;
    for (const item of selected) {
      await fetch(`/api/subjects/${encodeURIComponent(item.subject_code)}`, { method: 'DELETE', headers: getAuthHeaders() });
    }
    loadCSSubjectsTable();
  };

  // IT Subjects
  const itSubAdd = document.getElementById('itSubjectsAdd');
  const itSubEdit = document.getElementById('itSubjectsEdit');
  const itSubDel = document.getElementById('itSubjectsDelete');
  if (itSubAdd) itSubAdd.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const data = promptForData(fields);
    if (!data) return;
    data.lecture_hours_per_week = data.lecture_hours_per_week ? parseInt(data.lecture_hours_per_week, 10) : 0;
    data.lab_hours_per_week = data.lab_hours_per_week ? parseInt(data.lab_hours_per_week, 10) : 0;
    data.units = data.units ? parseInt(data.units, 10) : 0;
    data.semester = data.semester ? parseInt(data.semester, 10) : null;
    data.year_level = data.year_level ? parseInt(data.year_level, 10) : null;
    await fetch('/api/it-subjects', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    loadITSubjectsTable();
  };
  if (itSubEdit) itSubEdit.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const selected = getSelectedRowData('itSubjectsData', fields);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('it-subjects', fields, selected);
  };
  if (itSubDel) itSubDel.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const selected = getSelectedRowData('itSubjectsData', fields);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    if (!confirm(`Delete ${selected.length} IT subject(s)?`)) return;
    for (const item of selected) {
      await fetch(`/api/it-subjects/${encodeURIComponent(item.subject_code)}`, { method: 'DELETE', headers: getAuthHeaders() });
    }
    loadITSubjectsTable();
  };

  // Teachers
  const tAdd = document.getElementById('teachersAdd');
  const tEdit = document.getElementById('teachersEdit');
  const tDel = document.getElementById('teachersDelete');
  if (tAdd) tAdd.onclick = async () => {
    const data = promptForData(['teacher_name','can_teach','availability_days']);
    if (!data) return;
    // Convert availability_days string to array if provided
    if (data.availability_days && typeof data.availability_days === 'string') {
      data.availability_days = data.availability_days.split(',').map(day => day.trim()).filter(day => day);
    }
    const response = await fetch('/api/teachers', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    if (response.ok) {
      const result = await response.json();
      alert(`Teacher added successfully with ID: ${result.teacher_id}`);
    }
    loadTeachersTable();
  };
  if (tEdit) tEdit.onclick = async () => {
    const selected = getSelectedRowData('teachersData', ['teacher_id','teacher_name','can_teach','availability_days']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('teachers', ['teacher_name','can_teach','availability_days'], selected);
  };
  if (tDel) tDel.onclick = async () => {
    const selected = getSelectedRowData('teachersData', ['teacher_id','teacher_name','can_teach']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    if (!confirm(`Delete ${selected.length} teacher(s)?`)) return;
    for (const item of selected) {
      await fetch(`/api/teachers/${encodeURIComponent(item.teacher_id)}`, { method: 'DELETE', headers: getAuthHeaders() });
    }
    loadTeachersTable();
  };

  // Rooms
  const rAdd = document.getElementById('roomsAdd');
  const rEdit = document.getElementById('roomsEdit');
  const rDel = document.getElementById('roomsDelete');
  if (rAdd) rAdd.onclick = async () => {
    const data = promptForData(['room_name','is_laboratory']);
    if (!data) return;
    data.is_laboratory = ['1','true','yes','y'].includes(String(data.is_laboratory).trim().toLowerCase());
    const response = await fetch('/api/rooms', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    if (response.ok) {
      const result = await response.json();
      alert(`Room added successfully with ID: ${result.room_id}`);
    }
    loadRoomsTable();
  };
  if (rEdit) rEdit.onclick = async () => {
    const selected = getSelectedRowData('roomsData', ['room_id','room_name','is_laboratory']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('rooms', ['room_name','is_laboratory'], selected);
  };
  if (rDel) rDel.onclick = async () => {
    const selected = getSelectedRowData('roomsData', ['room_id','room_name','is_laboratory']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    if (!confirm(`Delete ${selected.length} room(s)?`)) return;
    for (const item of selected) {
      await fetch(`/api/rooms/${encodeURIComponent(item.room_id)}`, { method: 'DELETE', headers: getAuthHeaders() });
    }
    loadRoomsTable();
  };

}

function openBulkEditModal(kind, fields, selectedRows) {
  const modalEl = document.getElementById('bulkEditModal');
  const content = document.getElementById('bulkEditContent');
  const saveBtn = document.getElementById('bulkEditSaveBtn');
  if (!modalEl || !content || !saveBtn) return;

  // Field labels for better user experience
  const fieldLabels = {
    'teacher_name': 'Teacher Name',
    'can_teach': 'Subjects (comma-separated)',
    'availability_days': 'Available Days (comma-separated: Mon,Tue,Wed,Thu,Fri,Sat)',
    'room_name': 'Room Name',
    'is_laboratory': 'Is Laboratory? (yes/no)',
    'subject_code': 'Subject Code',
    'subject_name': 'Subject Name',
    'lecture_hours_per_week': 'Lecture Hours per Week',
    'lab_hours_per_week': 'Lab Hours per Week',
    'units': 'Units',
    'semester': 'Semester',
    'program_specialization': 'Program Specialization',
    'year_level': 'Year Level'
  };

  // Get the first selected row to pre-populate values (for single selection)
  const firstRow = selectedRows.length === 1 ? selectedRows[0] : null;

  // Build form: simple inputs for current values
  let html = '';
  html += `<p>${selectedRows.length} row(s) selected.</p>`;
  html += '<div class="table-responsive"><table class="table"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>';
  fields.forEach(f => {
    const disabled = (f.endsWith('_id') || f === 'teacher_id' || f === 'room_id' || f === 'section_id') ? 'disabled' : '';
    const label = fieldLabels[f] || f;
    
    // Get current value for pre-population
    let currentValue = '';
    if (firstRow && firstRow[f] !== undefined) {
      currentValue = firstRow[f];
      // Handle array fields (like availability_days)
      if (Array.isArray(currentValue)) {
        currentValue = currentValue.join(', ');
      }
      // Handle boolean fields
      if (typeof currentValue === 'boolean') {
        currentValue = currentValue ? 'yes' : 'no';
      }
    }
    
    html += `<tr>
      <td>${label}</td>
      <td><input type="text" class="form-control form-control-sm" data-role="field-input" data-field="${f}" data-original="${currentValue}" value="${currentValue}" ${disabled && 'disabled'}></td>
    </tr>`;
  });
  html += '</tbody></table></div>';
  content.innerHTML = html;

  // Attach handler
  saveBtn.onclick = async () => {
    const inputs = Array.from(content.querySelectorAll('input[data-role="field-input"]'));
    const toApply = {};
    
    // Auto-detect changed fields by comparing current value with original
    inputs.forEach(input => {
      if (!input.disabled) {
        const field = input.getAttribute('data-field');
        const originalValue = input.getAttribute('data-original');
        const currentValue = input.value;
        
        // Only include fields that have actually changed
        if (currentValue !== originalValue) {
          toApply[field] = currentValue;
        }
      }
    });
    
    if (Object.keys(toApply).length === 0) {
      alert('No changes detected. Please modify at least one field before saving.');
      return;
    }
    // Cast booleans/ints where needed
    if (kind === 'rooms' && toApply.hasOwnProperty('is_laboratory')) {
      toApply.is_laboratory = ['1','true','yes','y'].includes(String(toApply.is_laboratory).trim().toLowerCase());
    }
    if (kind === 'subjects') {
      ['lecture_hours_per_week','lab_hours_per_week','units','semester','year_level'].forEach(k => {
        if (toApply.hasOwnProperty(k)) {
          const v = toApply[k];
          toApply[k] = v === '' || v == null ? (k === 'semester' || k === 'year_level' ? null : 0) : parseInt(v, 10);
        }
      });
    }
    // Convert availability_days string to array for teachers
    if (kind === 'teachers' && toApply.hasOwnProperty('availability_days')) {
      if (toApply.availability_days && typeof toApply.availability_days === 'string') {
        toApply.availability_days = toApply.availability_days.split(',').map(day => day.trim()).filter(day => day);
      }
    }

    // Perform PUT per selected row
    for (const row of selectedRows) {
      let idField = (kind === 'teachers') ? 'teacher_id' : (kind === 'rooms') ? 'room_id' : 'subject_code';
      const idVal = row[idField];
      const body = { ...row, ...toApply };
      const url = `/api/${kind}/${encodeURIComponent(idVal)}`;
      await fetch(url, { method: 'PUT', headers: getAuthHeaders(), body: JSON.stringify(body) });
    }

    // Refresh table
    if (kind === 'teachers') await loadTeachersTable();
    if (kind === 'rooms') await loadRoomsTable();
    if (kind === 'subjects') await loadSubjectsTable();

    // Close modal
    const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    bsModal.hide();
  };

  // Show modal
  const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
  bsModal.show();
}

// Notification functions
async function loadNotifications() {
  try {
    const response = await fetch('/api/notifications', {
      headers: getAuthHeaders()
    });
    
    if (response.ok) {
      const notifications = await response.json();
      displayNotifications(notifications);
      updateNotificationBadge(notifications);
    }
  } catch (error) {
    console.error('Error loading notifications:', error);
  }
}

async function loadUnreadNotifications() {
  try {
    const response = await fetch('/api/notifications/unread', {
      headers: getAuthHeaders()
    });
    
    if (response.ok) {
      const notifications = await response.json();
      return notifications;
    }
  } catch (error) {
    console.error('Error loading unread notifications:', error);
  }
  return [];
}

function displayNotifications(notifications) {
  const dropdownMenu = document.getElementById('notificationDropdownMenu');
  const noNotifications = document.getElementById('noNotifications');
  
  if (!dropdownMenu) return;
  
  // Clear existing notifications (except header and divider)
  const existingItems = dropdownMenu.querySelectorAll('.notification-item');
  existingItems.forEach(item => item.remove());
  
  if (notifications.length === 0) {
    noNotifications.style.display = 'block';
    return;
  }
  
  noNotifications.style.display = 'none';
  
  notifications.forEach(notification => {
    const notificationItem = createNotificationItem(notification);
    dropdownMenu.appendChild(notificationItem);
  });
}

function createNotificationItem(notification) {
  const li = document.createElement('li');
  li.className = 'notification-item';
  
  const typeClass = getNotificationTypeClass(notification.type);
  const timeAgo = getTimeAgo(notification.created_at);
  
  li.innerHTML = `
    <div class="dropdown-item ${notification.is_read ? '' : 'bg-light'}">
      <div class="d-flex justify-content-between align-items-start">
        <div class="flex-grow-1">
          <div class="d-flex align-items-center mb-1">
            <i class="bi ${getNotificationIcon(notification.type)} ${typeClass} me-2"></i>
            <strong class="text-dark">${notification.title}</strong>
          </div>
          <p class="mb-1 text-muted small">${notification.message}</p>
          <small class="text-muted">${timeAgo}</small>
        </div>
        <div class="d-flex align-items-center gap-2">
          ${!notification.is_read ? '<span class="badge bg-primary rounded-pill">New</span>' : ''}
          <button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteNotification(${notification.id})" title="Delete notification">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    </div>
  `;
  
  // Add click handler to mark as read (only for the main content area, not buttons)
  li.addEventListener('click', async (e) => {
    if (!e.target.closest('button') && !notification.is_read) {
      await markNotificationAsRead(notification.id);
      notification.is_read = true;
      li.querySelector('.dropdown-item').classList.remove('bg-light');
      const badge = li.querySelector('.badge');
      if (badge) badge.remove();
      updateNotificationBadge(await loadUnreadNotifications());
    }
  });
  
  return li;
}

function getNotificationTypeClass(type) {
  switch (type) {
    case 'success': return 'text-success';
    case 'warning': return 'text-warning';
    case 'error': return 'text-danger';
    case 'info': 
    default: return 'text-info';
  }
}

function getNotificationIcon(type) {
  switch (type) {
    case 'success': return 'bi-check-circle-fill';
    case 'warning': return 'bi-exclamation-triangle-fill';
    case 'error': return 'bi-x-circle-fill';
    case 'info': 
    default: return 'bi-info-circle-fill';
  }
}

function getTimeAgo(dateString) {
  const now = new Date();
  const date = new Date(dateString);
  const diffInSeconds = Math.floor((now - date) / 1000);
  
  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

function updateNotificationBadge(notifications) {
  const badge = document.getElementById('notificationBadge');
  if (!badge) return;
  
  const unreadCount = notifications.filter(n => !n.is_read).length;
  
  if (unreadCount > 0) {
    badge.textContent = unreadCount;
    badge.style.display = 'inline-block';
  } else {
    badge.style.display = 'none';
  }
}

async function markNotificationAsRead(notificationId) {
  try {
    const response = await fetch(`/api/notifications/${notificationId}/read`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      console.error('Failed to mark notification as read');
    }
  } catch (error) {
    console.error('Error marking notification as read:', error);
  }
}

async function deleteNotification(notificationId) {
  try {
    showLoadingState('deleteBtn', 'Deleting...');
    
    const response = await fetch(`/api/notifications/${notificationId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        showNotification('Notification not found or already deleted.', 'warning');
      } else {
        showNotification('Failed to delete notification. Please try again.', 'danger');
      }
      console.error('Failed to delete notification:', response.status, response.statusText);
    } else {
      showNotification('Notification deleted successfully.', 'success');
      // Reload notifications after deletion
      await loadNotifications();
    }
  } catch (error) {
    console.error('Error deleting notification:', error);
    showNotification('Error deleting notification. Please check your connection.', 'danger');
  } finally {
    hideLoadingState('deleteBtn');
  }
}

async function clearAllNotifications() {
  if (!confirm('Are you sure you want to delete all notifications? This action cannot be undone.')) {
    return;
  }
  
  try {
    // Get all notifications first
    const response = await fetch('/api/notifications', {
      headers: getAuthHeaders()
    });
    
    if (!response.ok) {
      showNotification('Failed to load notifications.', 'danger');
      return;
    }
    
    const notifications = await response.json();
    
    if (notifications.length === 0) {
      showNotification('No notifications to delete.', 'info');
      return;
    }
    
    // Delete all notifications
    const deletePromises = notifications.map(notification => 
      fetch(`/api/notifications/${notification.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })
    );
    
    await Promise.all(deletePromises);
    showNotification(`Successfully deleted ${notifications.length} notifications.`, 'success');
    
    // Reload notifications
    await loadNotifications();
    
  } catch (error) {
    console.error('Error clearing all notifications:', error);
    showNotification('Error clearing notifications. Please try again.', 'danger');
  }
}

// Auto-refresh notifications every 30 seconds
setInterval(loadNotifications, 30000);

// Analytics Functions
function displayAnalytics(analytics, switchToTab = true) {
  const analyticsContent = document.getElementById('analyticsContent');
  
  if (!analyticsContent) return;
  
  // Switch to analytics tab only if requested
  if (switchToTab) {
    const analyticsTab = document.getElementById('analytics-tab');
    if (analyticsTab) {
      const tab = new bootstrap.Tab(analyticsTab);
      tab.show();
    }
  }
  
  // Generate analytics HTML
  let html = '';
  
  // Summary Cards
  if (analytics.summary) {
    html += `
      <div class="analytics-summary-grid">
        <div class="analytics-summary-card">
          <div class="analytics-summary-value">${analytics.summary.total_events || 0}</div>
          <div class="analytics-summary-label">Total Events</div>
        </div>
        <div class="analytics-summary-card">
          <div class="analytics-summary-value">${analytics.summary.rooms_used || 0}</div>
          <div class="analytics-summary-label">Rooms Used</div>
        </div>
        <div class="analytics-summary-card">
          <div class="analytics-summary-value">${analytics.summary.teachers_used || 0}</div>
          <div class="analytics-summary-label">Teachers Used</div>
        </div>
        <div class="analytics-summary-card">
          <div class="analytics-summary-value">${analytics.summary.total_contact_hours || 0}</div>
          <div class="analytics-summary-label">Contact Hours</div>
        </div>
      </div>
    `;
  }
  
  // Room Utilization Chart
  if (analytics.room_utilization && Object.keys(analytics.room_utilization).length > 0) {
    html += `
      <div class="analytics-chart-container">
        <div class="analytics-chart-title">🏢 Room Utilization</div>
        <div class="analytics-chart">
          <canvas id="roomUtilizationChart"></canvas>
        </div>
      </div>
    `;
  }
  
  // Faculty Workload Chart
  if (analytics.faculty_workload && Object.keys(analytics.faculty_workload).length > 0) {
    html += `
      <div class="analytics-chart-container">
        <div class="analytics-chart-title">👨‍🏫 Faculty Contact Hours</div>
        <div class="analytics-chart">
          <canvas id="facultyWorkloadChart"></canvas>
        </div>
      </div>
    `;
  }
  
  // Weekly Occupancy Chart
  if (analytics.weekly_occupancy && Object.keys(analytics.weekly_occupancy).length > 0) {
    html += `
      <div class="analytics-chart-container">
        <div class="analytics-chart-title">📅 Weekly Occupancy Rates</div>
        <div class="analytics-chart">
          <canvas id="weeklyOccupancyChart"></canvas>
        </div>
      </div>
    `;
  }
  analyticsContent.innerHTML = html;
  
  // Create charts after DOM is updated
  setTimeout(() => {
    createRoomUtilizationChart(analytics.room_utilization);
    createFacultyWorkloadChart(analytics.faculty_workload);
    createWeeklyOccupancyChart(analytics.weekly_occupancy);
  }, 100);
}

function hideAnalytics() {
  const analyticsContent = document.getElementById('analyticsContent');
  if (analyticsContent) {
    analyticsContent.innerHTML = `
      <div class="text-center py-5">
        <i class="bi bi-graph-up" style="font-size: 3rem; opacity: 0.3; color: #6c757d;"></i>
        <p class="mt-3 mb-0 text-muted">No analytics available yet.</p>
        <p class="small text-muted">Generate a schedule to see analytics.</p>
      </div>
    `;
  }
}

function createRoomUtilizationChart(roomData) {
  const canvas = document.getElementById('roomUtilizationChart');
  if (!canvas || !roomData) return;
  
  const rooms = Object.keys(roomData);
  const utilizationData = rooms.map(roomId => roomData[roomId].utilization_percentage);
  const roomNames = rooms.map(roomId => roomData[roomId].room_name);
  
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: roomNames,
      datasets: [{
        label: 'Utilization %',
        data: utilizationData,
        backgroundColor: utilizationData.map(val => 
          val > 80 ? 'rgba(255, 59, 48, 0.8)' : val > 60 ? 'rgba(255, 149, 0, 0.8)' : 'rgba(52, 199, 89, 0.8)'
        ),
        borderColor: utilizationData.map(val => 
          val > 80 ? '#FF3B30' : val > 60 ? '#FF9500' : '#34C759'
        ),
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: {
            display: false
          },
          ticks: {
            color: '#8E8E93',
            font: {
              size: 12,
              weight: '500'
            }
          }
        },
        y: {
          beginAtZero: true,
          max: 100,
          grid: {
            color: 'rgba(142, 142, 147, 0.2)',
            drawBorder: false
          },
          ticks: {
            color: '#8E8E93',
            font: {
              size: 12,
              weight: '500'
            },
            callback: function(value) {
              return value + '%';
            }
          }
        }
      },
      plugins: {
        legend: {
          display: false
        }
      }
    }
  });
}

function createFacultyWorkloadChart(facultyData) {
  const canvas = document.getElementById('facultyWorkloadChart');
  if (!canvas || !facultyData) return;
  
  const teachers = Object.keys(facultyData);
  const workloadData = teachers.map(teacher => facultyData[teacher].total_hours);
  const teacherNames = teachers.map(teacher => facultyData[teacher].teacher_name);
  
  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: teacherNames,
      datasets: [{
        data: workloadData,
        backgroundColor: [
          '#007AFF', '#34C759', '#FF9500', '#FF3B30', '#AF52DE',
          '#FF2D92', '#5AC8FA', '#FFCC00', '#FF6B6B', '#4ECDC4'
        ],
        borderWidth: 0,
        cutout: '60%'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            usePointStyle: true,
            padding: 20,
            color: '#1D1D1F',
            font: {
              size: 12,
              weight: '500'
            }
          }
        }
      }
    }
  });
}

function createWeeklyOccupancyChart(occupancyData) {
  const canvas = document.getElementById('weeklyOccupancyChart');
  if (!canvas || !occupancyData) return;
  
  const days = Object.keys(occupancyData);
  const occupancyRates = days.map(day => occupancyData[day].occupancy_rate);
  
  new Chart(canvas, {
    type: 'line',
    data: {
      labels: days,
      datasets: [{
        label: 'Occupancy Rate %',
        data: occupancyRates,
        borderColor: '#007AFF',
        backgroundColor: 'rgba(0, 122, 255, 0.1)',
        tension: 0.4,
        fill: true,
        borderWidth: 3,
        pointBackgroundColor: '#007AFF',
        pointBorderColor: '#FFFFFF',
        pointBorderWidth: 2,
        pointRadius: 6,
        pointHoverRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: {
            display: false
          },
          ticks: {
            color: '#8E8E93',
            font: {
              size: 12,
              weight: '500'
            }
          }
        },
        y: {
          beginAtZero: true,
          max: 100,
          grid: {
            color: 'rgba(142, 142, 147, 0.2)',
            drawBorder: false
          },
          ticks: {
            color: '#8E8E93',
            font: {
              size: 12,
              weight: '500'
            },
            callback: function(value) {
              return value + '%';
            }
          }
        }
      },
      plugins: {
        legend: {
          display: false
        }
      }
    }
  });
}
