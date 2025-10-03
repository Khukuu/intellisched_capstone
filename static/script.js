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
const roomDropdown = document.getElementById('roomDropdown');
const viewMode = document.getElementById('viewMode');
const saveBtn = document.getElementById('saveBtn');
const saveNameInput = document.getElementById('saveNameInput');
const savedSchedulesSelect = document.getElementById('savedSchedulesSelect');
const loadBtn = document.getElementById('loadBtn');
const deleteBtn = document.getElementById('deleteBtn');

// Keep last generated schedule in memory for filtering
let lastGeneratedSchedule = [];
let lastSavedId = '';
let currentRoomFilter = 'all';
let availableRooms = [];

// Cached data for tabs so searches/filtering work reliably
let subjectsCache = [];
let teachersCache = [];
let roomsCache = [];
let sectionsCache = [];

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
    loadDataManagementTables(); // Load data when showing this section
  }
}

// Initial display
showSection('schedule-section');

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
  await loadSubjectsTable(); // Reload subjects after upload
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

if (uploadSectionsForm) uploadSectionsForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('sectionsFile');
  await uploadFile(fileInput.files[0], 'sections');
  await loadSectionsTable(); // Reload sections after upload
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
const dayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const timeSlotLabels = [
  "08:00-08:30", "08:30-09:00", "09:00-09:30", "09:30-10:00",
  "10:00-10:30", "10:30-11:00", "11:00-11:30", "11:30-12:00",
  "13:00-13:30", "13:30-14:00", "14:00-14:30", "14:30-15:00",
  "15:00-15:30", "15:30-16:00", "16:00-16:30", "16:30-17:00",
  "17:00-17:30", "17:30-18:00", "18:00-18:30", "18:30-19:00",
  "19:00-19:30", "19:30-20:00"
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
  document.getElementById('result').innerHTML = '<div class="p-4 text-center">Generating schedule...</div>';
  document.getElementById('timetable').innerHTML = "";

  const selectedSemester = elValue(document.getElementById('semesterSelect')) || null;
  const requestBody = { semester: selectedSemester };
  requestBody.numSectionsYear1 = parseInt(elValue(document.getElementById('numSectionsYear1')) || 0, 10);
  requestBody.numSectionsYear2 = parseInt(elValue(document.getElementById('numSectionsYear2')) || 0, 10);
  requestBody.numSectionsYear3 = parseInt(elValue(document.getElementById('numSectionsYear3')) || 0, 10);
  requestBody.numSectionsYear4 = parseInt(elValue(document.getElementById('numSectionsYear4')) || 0, 10);

  // Pre-validate against curriculum: zero-out years that have no subjects in selected semester
  try {
    const subjectsResponse = await fetch('/data/cs_curriculum', {
      headers: getAuthHeaders()
    });
    
    if (!subjectsResponse.ok) {
      console.error('Failed to load subjects:', subjectsResponse.status);
      throw new Error(`Failed to load subjects: ${subjectsResponse.status}`);
    }
    
    const subjectsData = await subjectsResponse.json();
    
    if (!Array.isArray(subjectsData)) {
      throw new Error('Subjects data is not an array');
    }
    
    const yearsList = subjectsData
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

  if (!requestBody.numSectionsYear1 && !requestBody.numSectionsYear2 && !requestBody.numSectionsYear3 && !requestBody.numSectionsYear4) {
    document.getElementById('result').innerHTML = '<div class="alert alert-info">No sections selected to schedule.</div>';
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
    lastGeneratedSchedule = scheduleArray;
    lastSavedId = '';

    if (!Array.isArray(scheduleArray) || scheduleArray.length === 0) {
      document.getElementById('result').innerHTML = "<b>No schedule generated.</b>";
      document.getElementById('timetable').innerHTML = "";
      if (downloadBtn) downloadBtn.disabled = true;
      return;
    }

    populateFilters(lastGeneratedSchedule);
    renderScheduleAndTimetable(lastGeneratedSchedule);
    refreshSavedSchedulesList();
  } catch (e) {
    console.error('Error generating schedule', e);
    document.getElementById('result').innerHTML = '<div class="alert alert-danger">Error generating schedule. See console.</div>';
  }
};

downloadBtn.onclick = function() {
  if (!downloadBtn.disabled) {
    const selectedSemester = semesterSelect.value;
    let downloadUrl = '/download_schedule';
    if (lastSavedId) {
      downloadUrl += `?id=${encodeURIComponent(lastSavedId)}`;
    } else if (selectedSemester) {
      downloadUrl += `?semester=${selectedSemester}`;
    }
    window.location.href = downloadUrl;
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

// Load selected saved schedule
if (loadBtn) {
  loadBtn.addEventListener('click', async () => {
    const id = savedSchedulesSelect ? savedSchedulesSelect.value : '';
    if (!id) {
      alert('Select a saved schedule first.');
      return;
    }
    try {
      // Load rooms data first to populate room mapping
      await loadRoomsTable();
      
      const resp = await fetch(`/load_schedule?id=${encodeURIComponent(id)}`, {
        headers: getAuthHeaders()
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Failed to load schedule');
      }
      const sched = Array.isArray(data.schedule) ? data.schedule : [];
      lastGeneratedSchedule = sched;
      lastSavedId = data.id || id;
      if (semesterSelect && data.semester) semesterSelect.value = String(data.semester);
      renderScheduleAndTimetable(lastGeneratedSchedule);
      populateFilters(lastGeneratedSchedule);
      applyViewMode();
      alert('Schedule loaded.');
    } catch (e) {
      console.error(e);
      alert('Error loading saved schedule.');
    }
  });
}

// Delete selected saved schedule
if (deleteBtn) {
  deleteBtn.addEventListener('click', async () => {
    const id = savedSchedulesSelect ? savedSchedulesSelect.value : '';
    if (!id) {
      alert('Select a saved schedule to delete.');
      return;
    }
    if (!confirm('Delete this saved schedule? This action cannot be undone.')) return;
    try {
      const resp = await fetch(`/saved_schedules/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.detail || 'Failed to delete');
      alert('Saved schedule deleted.');
      if (lastSavedId === id) lastSavedId = '';
      refreshSavedSchedulesList();
      // Clear rendered views if nothing loaded/generated
      if (!lastSavedId && (!lastGeneratedSchedule || lastGeneratedSchedule.length === 0)) {
        const resultDiv = document.getElementById('result');
        const timetableDiv = document.getElementById('timetable');
        if (resultDiv) resultDiv.innerHTML = '<div class="placeholder p-4 text-center text-muted" style="display: flex; align-items: center; justify-content: center; min-height: 200px;">No schedule generated yet. Click <strong>Generate</strong> to create one.</div>';
        if (timetableDiv) timetableDiv.innerHTML = '<div class="placeholder p-4 text-center text-muted" style="display: flex; align-items: center; justify-content: center; min-height: 200px;">Timetable will appear here after generation.</div>';
        if (downloadBtn) downloadBtn.disabled = true;
      }
    } catch (e) {
      console.error(e);
      alert('Error deleting saved schedule.');
    }
  });
}

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
      refreshSavedSchedulesList(lastSavedId);
    } catch (e) {
      console.error(e);
      alert('Error submitting schedule.');
    }
}

async function refreshSavedSchedulesList(selectId) {
  try {
          const resp = await fetch('/saved_schedules', {
        headers: getAuthHeaders()
      });
    const items = await resp.json();
    if (!savedSchedulesSelect) return;
    savedSchedulesSelect.innerHTML = '<option value="">Select saved schedule…</option>';
    items.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.id;
      const labelName = item.name ? `${item.name}` : `${item.id}`;
      const extra = item.semester ? `S${item.semester}` : '';
      const status = item.status ? ` [${String(item.status).toUpperCase()}]` : '';
      const count = typeof item.count === 'number' ? ` (${item.count})` : '';
      opt.textContent = `${labelName} ${extra} ${count}${status}`.trim();
      savedSchedulesSelect.appendChild(opt);
    });
    if (selectId) savedSchedulesSelect.value = selectId;
  } catch (e) {
    console.warn('Could not load saved schedules:', e);
  }
}

// Load saved list on page open
refreshSavedSchedulesList();


function populateFilters(data) {
  // Extract available years from section IDs (format CS{year}{letter})
  const years = new Set();
  const sectionsByYear = new Map();
  data.forEach(e => {
    const match = /^CS(\d)/.exec(e.section_id || '');
    if (match) {
      const y = match[1];
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
  if (!roomFilter || !roomDropdown) {
    console.error('Room filter elements not found');
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
  
  // Update dropdown with all rooms
  updateRoomDropdown(availableRooms);
  
  // Enable/disable the filter
  roomFilter.disabled = availableRooms.length === 0;
  
  // Reset to "All Rooms" if disabled or if current selection is not available
  if (roomFilter.disabled || (currentRoomFilter !== 'all' && !availableRooms.includes(currentRoomFilter))) {
    currentRoomFilter = 'all';
    roomFilter.value = '';
    roomFilter.placeholder = 'Search rooms...';
  }
}

function updateRoomDropdown(rooms) {
  roomDropdown.innerHTML = '';
  
  // Add "All Rooms" option
  const allOption = document.createElement('div');
  allOption.className = 'dropdown-item';
  allOption.setAttribute('data-value', 'all');
  allOption.textContent = 'All Rooms';
  allOption.style.cursor = 'pointer';
  roomDropdown.appendChild(allOption);
  
  // Add individual room options
  rooms.forEach(room => {
    const option = document.createElement('div');
    option.className = 'dropdown-item';
    option.setAttribute('data-value', room);
    option.textContent = room;
    option.style.cursor = 'pointer';
    roomDropdown.appendChild(option);
  });
}

function filterRoomDropdown(searchTerm) {
  const filteredRooms = availableRooms.filter(room => 
    room.toLowerCase().includes(searchTerm.toLowerCase())
  );
  updateRoomDropdown(filteredRooms);
}

yearFilter.addEventListener('change', () => {
  // Rebuild section list based on year
  const sectionsByYear = new Map();
  lastGeneratedSchedule.forEach(e => {
    const match = /^CS(\d)/.exec(e.section_id || '');
    if (match) {
      const y = match[1];
      if (!sectionsByYear.has(y)) sectionsByYear.set(y, new Set());
      sectionsByYear.get(y).add(e.section_id);
    }
  });
  rebuildSectionFilter(sectionsByYear);
  rebuildRoomFilter();
  renderScheduleAndTimetable(lastGeneratedSchedule);
});

sectionFilter.addEventListener('change', () => {
  renderScheduleAndTimetable(lastGeneratedSchedule);
});

// Room filter event listeners
roomFilter.addEventListener('input', (e) => {
  const searchTerm = e.target.value;
  filterRoomDropdown(searchTerm);
  roomDropdown.style.display = 'block';
});

roomFilter.addEventListener('focus', () => {
  if (!roomFilter.disabled) {
    roomDropdown.style.display = 'block';
  }
});

roomFilter.addEventListener('blur', (e) => {
  // Delay hiding to allow click on dropdown items
  setTimeout(() => {
    roomDropdown.style.display = 'none';
  }, 200);
});

// Handle dropdown item clicks
roomDropdown.addEventListener('click', (e) => {
  if (e.target.classList.contains('dropdown-item')) {
    const value = e.target.getAttribute('data-value');
    currentRoomFilter = value;
    
    if (value === 'all') {
      roomFilter.value = '';
      roomFilter.placeholder = 'Search rooms...';
    } else {
      roomFilter.value = value;
    }
    
    roomDropdown.style.display = 'none';
    renderScheduleAndTimetable(lastGeneratedSchedule);
  }
});

// Handle keyboard navigation
roomFilter.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    roomDropdown.style.display = 'none';
    roomFilter.blur();
  }
});


function applyFilters(data) {
  const y = yearFilter.value;
  const s = sectionFilter.value;
  const r = currentRoomFilter;
  return data.filter(e => {
    let ok = true;
    if (y !== 'all') {
      const m = /^CS(\d)/.exec(e.section_id || '');
      ok = ok && m && m[1] === y;
    }
    if (s !== 'all') ok = ok && e.section_id === s;
    if (r !== 'all') {
      const evName = getRoomName(e.room_id);
      ok = ok && (String(e.room_id) === String(r) || String(evName) === String(r));
    }
    return ok;
  });
}

function renderScheduleAndTimetable(data) {
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
  const resultDiv = document.getElementById('result');
  if (resultDiv) {
    resultDiv.innerHTML = html;
  }
  downloadBtn.disabled = filtered.length === 0;

  // Timetable (right)
  const timetable = Array.from({length: timeSlotLabels.length}, () => Array.from({length: dayLabels.length}, () => []));
  filtered.forEach(event => {
    const dayIdx = dayLabels.indexOf(event.day);
    const startSlotIdx = timeSlotLabels.indexOf(event.start_time_slot);
    const duration = event.duration_slots;
    if (dayIdx !== -1 && startSlotIdx !== -1) {
      for (let i = 0; i < duration; i++) {
        if (startSlotIdx + i < timeSlotLabels.length) {
          timetable[startSlotIdx + i][dayIdx].push(event);
        }
      }
    }
  });

  let tthtml = '<div class="table-responsive"><table class="table table-bordered"><thead><tr><th>Time Slot</th>';
  for (const day of dayLabels) tthtml += `<th>${day}</th>`;
  tthtml += '</tr></thead><tbody>';
  const singleSectionView = sectionFilter && sectionFilter.value !== 'all';
  if (singleSectionView) {
    // Rowspan rendering for a single section to reflect duration visually
    const skip = Array.from({ length: timeSlotLabels.length }, () => Array(dayLabels.length).fill(false));
    const startsMap = Array.from({ length: timeSlotLabels.length }, () => Array.from({ length: dayLabels.length }, () => []));
    filtered.forEach(event => {
      const dIdx = dayLabels.indexOf(event.day);
      const sIdx = timeSlotLabels.indexOf(event.start_time_slot);
      if (dIdx !== -1 && sIdx !== -1) startsMap[sIdx][dIdx].push(event);
    });
    for (let t = 0; t < timeSlotLabels.length; t++) {
      tthtml += `<tr><th>${timeSlotLabels[t]}</th>`;
      for (let d = 0; d < dayLabels.length; d++) {
        if (skip[t][d]) continue;
        const starts = startsMap[t][d];
        if (!starts || starts.length === 0) {
          tthtml += '<td></td>';
        } else {
          const ev = starts[0];
          const span = Math.min(parseInt(ev.duration_slots, 10) || 1, timeSlotLabels.length - t);
          const subj = ev.subject_name || ev.subject_code || '';
          const range = computeEventTimeRange(ev);
          const bg = getSubjectColor(ev.subject_code, ev.type);
          const fg = getTextColorForBackground(bg);
          tthtml += `<td rowspan="${span}" style="background:${bg}; color:${fg};">
            <b>${subj}</b> <small style=\"color:#000; opacity:.85\">(${range})</small><br>
            ${ev.section_id}<br>${ev.teacher_name}<br>${getRoomName(ev.room_id)}
          </td>`;
          for (let k = 1; k < span; k++) skip[t + k][d] = true;
        }
      }
      tthtml += '</tr>';
    }
  } else {
    // Combined view: show subject and full time range in the start slot
    for (let t = 0; t < timeSlotLabels.length; t++) {
      tthtml += `<tr><th>${timeSlotLabels[t]}</th>`;
      for (let d = 0; d < dayLabels.length; d++) {
        const eventsInSlot = timetable[t][d];
        if (eventsInSlot.length > 0) {
          const uniqueEvents = [];
          const seenEventIds = new Set();
          eventsInSlot.forEach(event => {
            const id = event.section_id + event.type + event.start_time_slot + event.day;
            if (timeSlotLabels.indexOf(event.start_time_slot) === t && !seenEventIds.has(id)) {
              uniqueEvents.push(event);
              seenEventIds.add(id);
            }
          });
          if (uniqueEvents.length > 0) {
            tthtml += '<td>' + uniqueEvents.map(slot => {
              const subj = slot.subject_name || slot.subject_code || '';
              const range = computeEventTimeRange(slot);
              const bg = getSubjectColor(slot.subject_code, slot.type);
              const fg = getTextColorForBackground(bg);
              return `<div style=\"background:${bg}; color:${fg}; padding:4px 6px; border-radius:6px; margin-bottom:4px;\">
                <b>${subj}</b> <small style=\"opacity:.85; color:#000\">(${range})</small><br>
                ${slot.section_id}<br>${slot.teacher_name}<br>${getRoomName(slot.room_id)}
              </div>`;
            }).join('') + '</td>';
          } else {
            tthtml += '<td></td>';
          }
        } else {
          tthtml += '<td></td>';
        }
      }
      tthtml += '</tr>';
    }
  }
  tthtml += '</tbody></table></div>';
  const timetableDiv = document.getElementById('timetable');
  if (timetableDiv) {
    timetableDiv.innerHTML = tthtml;
  }
  // View toggle handling
  applyViewMode();
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

// Change view when selector changes
if (viewMode) {
  viewMode.addEventListener('change', () => {
    applyViewMode();
  });
}


// Lazy-load per-tab data loaders
async function loadSubjectsTable() {
  try {
    const subjectsResponse = await fetch('/data/cs_curriculum', {
      headers: getAuthHeaders()
    });
    if (!subjectsResponse.ok) throw new Error('Failed to load subjects');
    subjectsCache = await subjectsResponse.json();
    renderTable(subjectsCache, 'subjectsData', ['subject_code', 'subject_name', 'lecture_hours_per_week', 'lab_hours_per_week', 'units', 'semester', 'program_specialization', 'year_level']);
  } catch (e) {
    console.warn('Could not load subjects:', e);
    document.getElementById('subjectsData').innerHTML = '<p>No data available.</p>';
  }
  // Attach client-side search handler
  const sInput = document.getElementById('subjectsSearch');
  if (sInput) {
    sInput.oninput = () => filterTable('subjectsData', subjectsCache, ['subject_code', 'subject_name']);
  }
}

async function loadTeachersTable() {
  try {
    const teachersResponse = await fetch('/data/teachers', {
      headers: getAuthHeaders()
    });
    if (!teachersResponse.ok) throw new Error('Failed to load teachers');
    teachersCache = await teachersResponse.json();
    renderTable(teachersCache, 'teachersData', ['teacher_id', 'teacher_name', 'can_teach']);
  } catch (e) {
    console.warn('Could not load teachers:', e);
    document.getElementById('teachersData').innerHTML = '<p>No data available.</p>';
  }
  const tInput = document.getElementById('teachersSearch');
  if (tInput) {
    tInput.oninput = () => filterTable('teachersData', teachersCache, ['teacher_id', 'teacher_name', 'can_teach']);
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

async function loadSectionsTable() {
  try {
    const sectionsResponse = await fetch('/data/sections', {
      headers: getAuthHeaders()
    });
    if (!sectionsResponse.ok) throw new Error('Failed to load sections');
    sectionsCache = await sectionsResponse.json();
    renderTable(sectionsCache, 'sectionsData', ['section_id', 'subject_code', 'year_level', 'num_meetings_non_lab']);
  } catch (e) {
    console.warn('Could not load sections:', e);
    document.getElementById('sectionsData').innerHTML = '<p>No data available.</p>';
  }
  const secInput = document.getElementById('sectionsSearch');
  if (secInput) {
    secInput.oninput = () => filterTable('sectionsData', sectionsCache, ['section_id', 'subject_code']);
  }
}

function filterTable(elementId, data, searchableFields) {
  const input = document.getElementById(elementId.replace('Data','Search')) || document.querySelector(`#${elementId.split('Data')[0]}Search`);
  const q = (input && input.value || '').trim().toLowerCase();
  if (!q) {
    // show full
    if (elementId === 'subjectsData') renderTable(data, elementId, ['subject_code', 'subject_name', 'lecture_hours_per_week', 'lab_hours_per_week', 'units', 'semester', 'program_specialization', 'year_level']);
    else if (elementId === 'teachersData') renderTable(data, elementId, ['teacher_id', 'teacher_name', 'can_teach']);
    else if (elementId === 'roomsData') renderTable(data, elementId, ['room_id', 'room_name', 'is_laboratory']);
    else if (elementId === 'sectionsData') renderTable(data, elementId, ['section_id', 'subject_code', 'year_level', 'num_meetings_non_lab']);
    return;
  }
  const filtered = data.filter(row => searchableFields.some(field => String(row[field] || '').toLowerCase().includes(q)));
  // reuse renderTable but with filtered data
  if (elementId === 'subjectsData') renderTable(filtered, elementId, ['subject_code', 'subject_name', 'lecture_hours_per_week', 'lab_hours_per_week', 'units', 'semester', 'program_specialization', 'year_level']);
  else if (elementId === 'teachersData') renderTable(filtered, elementId, ['teacher_id', 'teacher_name', 'can_teach']);
  else if (elementId === 'roomsData') renderTable(filtered, elementId, ['room_id', 'room_name', 'is_laboratory']);
  else if (elementId === 'sectionsData') renderTable(filtered, elementId, ['section_id', 'subject_code', 'year_level', 'num_meetings_non_lab']);
}

async function loadDataManagementTables() {
  // Determine active tab and load only it
  const activeBtn = document.querySelector('#dataTabs .nav-link.active');
  const tab = activeBtn ? activeBtn.dataset.tab : 'subjects';
  if (tab === 'subjects') await loadSubjectsTable();
  else if (tab === 'teachers') await loadTeachersTable();
  else if (tab === 'rooms') await loadRoomsTable();
  else if (tab === 'sections') await loadSectionsTable();
}

// Wire tab buttons to load content when activated (use Bootstrap event)
document.querySelectorAll('#dataTabs button[data-bs-toggle="tab"]').forEach(btn => {
  btn.addEventListener('shown.bs.tab', (e) => {
    const tab = e.target.dataset.tab;
    if (tab === 'subjects') loadSubjectsTable();
    else if (tab === 'teachers') loadTeachersTable();
    else if (tab === 'rooms') loadRoomsTable();
    else if (tab === 'sections') loadSectionsTable();
  });
});

// Wire refresh buttons
['subjects','teachers','rooms','sections'].forEach(key => {
  const btn = document.getElementById(`${key}Refresh`);
  if (btn) btn.addEventListener('click', () => {
    if (key === 'subjects') loadSubjectsTable();
    if (key === 'teachers') loadTeachersTable();
    if (key === 'rooms') loadRoomsTable();
    if (key === 'sections') loadSectionsTable();
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
      headers.forEach(header => { tableHtml += `<td>${row[header]}</td>`; });
      tableHtml += '</tr>';
    });
  } else {
    tableHtml += `<tr><td colspan="${headers.length + 1}" class="text-center text-muted">No data available.</td></tr>`;
  }
  tableHtml += '</tbody></table>';
  document.getElementById(elementId).innerHTML = tableHtml;
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
  for (const f of fields) {
    const val = prompt(`Enter ${f}`, initial[f] != null ? String(initial[f]) : '');
    if (val === null) return null;
    result[f] = val;
  }
  return result;
}

function setupCrudButtons() {
  // Subjects
  const subAdd = document.getElementById('subjectsAdd');
  const subEdit = document.getElementById('subjectsEdit');
  const subDel = document.getElementById('subjectsDelete');
  if (subAdd) subAdd.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const data = promptForData(fields);
    if (!data) return;
    data.lecture_hours_per_week = data.lecture_hours_per_week ? parseInt(data.lecture_hours_per_week, 10) : 0;
    data.lab_hours_per_week = data.lab_hours_per_week ? parseInt(data.lab_hours_per_week, 10) : 0;
    data.units = data.units ? parseInt(data.units, 10) : 0;
    data.semester = data.semester ? parseInt(data.semester, 10) : null;
    data.year_level = data.year_level ? parseInt(data.year_level, 10) : null;
    await fetch('/api/subjects', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    loadSubjectsTable();
  };
  if (subEdit) subEdit.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const selected = getSelectedRowData('subjectsData', fields);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('subjects', fields, selected);
  };
  if (subDel) subDel.onclick = async () => {
    const fields = ['subject_code','subject_name','lecture_hours_per_week','lab_hours_per_week','units','semester','program_specialization','year_level'];
    const selected = getSelectedRowData('subjectsData', fields);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    if (!confirm(`Delete ${selected.length} subject(s)?`)) return;
    for (const item of selected) {
      await fetch(`/api/subjects/${encodeURIComponent(item.subject_code)}`, { method: 'DELETE', headers: getAuthHeaders() });
    }
    loadSubjectsTable();
  };
  // Teachers
  const tAdd = document.getElementById('teachersAdd');
  const tEdit = document.getElementById('teachersEdit');
  const tDel = document.getElementById('teachersDelete');
  if (tAdd) tAdd.onclick = async () => {
    const data = promptForData(['teacher_id','teacher_name','can_teach']);
    if (!data) return;
    await fetch('/api/teachers', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    loadTeachersTable();
  };
  if (tEdit) tEdit.onclick = async () => {
    const selected = getSelectedRowData('teachersData', ['teacher_id','teacher_name','can_teach']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('teachers', ['teacher_id','teacher_name','can_teach'], selected);
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
    const data = promptForData(['room_id','room_name','is_laboratory']);
    if (!data) return;
    data.is_laboratory = ['1','true','yes','y'].includes(String(data.is_laboratory).trim().toLowerCase());
    await fetch('/api/rooms', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    loadRoomsTable();
  };
  if (rEdit) rEdit.onclick = async () => {
    const selected = getSelectedRowData('roomsData', ['room_id','room_name','is_laboratory']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('rooms', ['room_id','room_name','is_laboratory'], selected);
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

  // Sections
  const sAdd = document.getElementById('sectionsAdd');
  const sEdit = document.getElementById('sectionsEdit');
  const sDel = document.getElementById('sectionsDelete');
  if (sAdd) sAdd.onclick = async () => {
    const data = promptForData(['section_id','subject_code','year_level','num_meetings_non_lab']);
    if (!data) return;
    data.year_level = data.year_level ? parseInt(data.year_level, 10) : null;
    data.num_meetings_non_lab = data.num_meetings_non_lab ? parseInt(data.num_meetings_non_lab, 10) : 0;
    await fetch('/api/sections', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    loadSectionsTable();
  };
  if (sEdit) sEdit.onclick = async () => {
    const selected = getSelectedRowData('sectionsData', ['section_id','subject_code','year_level','num_meetings_non_lab']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('sections', ['section_id','subject_code','year_level','num_meetings_non_lab'], selected);
  };
  if (sDel) sDel.onclick = async () => {
    const selected = getSelectedRowData('sectionsData', ['section_id','subject_code','year_level','num_meetings_non_lab']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    if (!confirm(`Delete ${selected.length} section(s)?`)) return;
    for (const item of selected) {
      await fetch(`/api/sections/${encodeURIComponent(item.section_id)}`, { method: 'DELETE', headers: getAuthHeaders() });
    }
    loadSectionsTable();
  };
}

function openBulkEditModal(kind, fields, selectedRows) {
  const modalEl = document.getElementById('bulkEditModal');
  const content = document.getElementById('bulkEditContent');
  const saveBtn = document.getElementById('bulkEditSaveBtn');
  if (!modalEl || !content || !saveBtn) return;

  // Build form: checkboxes for fields and inputs for new values
  let html = '';
  html += `<p>${selectedRows.length} row(s) selected.</p>`;
  html += '<div class="table-responsive"><table class="table"><thead><tr><th>Apply</th><th>Field</th><th>New value</th></tr></thead><tbody>';
  fields.forEach(f => {
    const disabled = (f.endsWith('_id') || f === 'teacher_id' || f === 'room_id' || f === 'section_id') ? 'disabled' : '';
    html += `<tr>
      <td><input type="checkbox" class="form-check-input" data-role="field-check" data-field="${f}" ${disabled && 'disabled'}></td>
      <td>${f}</td>
      <td><input type="text" class="form-control form-control-sm" data-role="field-input" data-field="${f}" ${disabled && 'disabled'}></td>
    </tr>`;
  });
  html += '</tbody></table></div>';
  content.innerHTML = html;

  // Attach handler
  saveBtn.onclick = async () => {
    const checks = Array.from(content.querySelectorAll('input[data-role="field-check"]'));
    const inputs = Array.from(content.querySelectorAll('input[data-role="field-input"]'));
    const toApply = {};
    checks.forEach(chk => {
      if (chk.checked && !chk.disabled) {
        const f = chk.getAttribute('data-field');
        const inp = inputs.find(i => i.getAttribute('data-field') === f);
        toApply[f] = inp ? inp.value : '';
      }
    });
    if (Object.keys(toApply).length === 0) {
      alert('Select at least one field to apply.');
      return;
    }
    // Cast booleans/ints where needed
    if (kind === 'rooms' && toApply.hasOwnProperty('is_laboratory')) {
      toApply.is_laboratory = ['1','true','yes','y'].includes(String(toApply.is_laboratory).trim().toLowerCase());
    }
    if (kind === 'sections') {
      if (toApply.hasOwnProperty('year_level')) toApply.year_level = toApply.year_level ? parseInt(toApply.year_level, 10) : null;
      if (toApply.hasOwnProperty('num_meetings_non_lab')) toApply.num_meetings_non_lab = toApply.num_meetings_non_lab ? parseInt(toApply.num_meetings_non_lab, 10) : 0;
    }
    if (kind === 'subjects') {
      ['lecture_hours_per_week','lab_hours_per_week','units','semester','year_level'].forEach(k => {
        if (toApply.hasOwnProperty(k)) {
          const v = toApply[k];
          toApply[k] = v === '' || v == null ? (k === 'semester' || k === 'year_level' ? null : 0) : parseInt(v, 10);
        }
      });
    }

    // Perform PUT per selected row
    for (const row of selectedRows) {
      let idField = (kind === 'teachers') ? 'teacher_id' : (kind === 'rooms') ? 'room_id' : (kind === 'sections') ? 'section_id' : 'subject_code';
      const idVal = row[idField];
      const body = { ...row, ...toApply };
      const url = `/api/${kind}/${encodeURIComponent(idVal)}`;
      await fetch(url, { method: 'PUT', headers: getAuthHeaders(), body: JSON.stringify(body) });
    }

    // Refresh table
    if (kind === 'teachers') await loadTeachersTable();
    if (kind === 'rooms') await loadRoomsTable();
    if (kind === 'sections') await loadSectionsTable();
    if (kind === 'subjects') await loadSubjectsTable();

    // Close modal
    const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    bsModal.hide();
  };

  // Show modal
  const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
  bsModal.show();
}