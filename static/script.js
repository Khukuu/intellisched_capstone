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
// Saved schedule controls removed - now handled in separate page

// Keep last generated schedule in memory for filtering
let lastGeneratedSchedule = [];
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
const dayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const timeSlotLabels = [
  "06:00-06:30", "06:30-07:00", "07:00-07:30", "07:30-08:00",
  "08:00-08:30", "08:30-09:00", "09:00-09:30", "09:30-10:00",
  "10:00-10:30", "10:30-11:00", "11:00-11:30", "11:30-12:00",
  "13:00-13:30", "13:30-14:00", "14:00-14:30", "14:30-15:00",
  "15:00-15:30", "15:30-16:00", "16:00-16:30", "16:30-17:00",
  "17:00-17:30", "17:30-18:00", "18:00-18:30", "18:30-19:00",
  "19:00-19:30", "19:30-20:00", "20:00-20:30", "20:30-21:00",
  "21:00-21:30", "21:30-22:00"
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

  // Get selected programs from checkboxes
  const selectedPrograms = [];
  if (document.getElementById('programCS').checked) selectedPrograms.push('CS');
  if (document.getElementById('programIT').checked) selectedPrograms.push('IT');
  
  const selectedSemester = elValue(document.getElementById('semesterSelect')) || null;
  const requestBody = { 
    programs: selectedPrograms,
    semester: selectedSemester 
  };
  requestBody.numSectionsYear1 = parseInt(elValue(document.getElementById('numSectionsYear1')) || 0, 10);
  requestBody.numSectionsYear2 = parseInt(elValue(document.getElementById('numSectionsYear2')) || 0, 10);
  requestBody.numSectionsYear3 = parseInt(elValue(document.getElementById('numSectionsYear3')) || 0, 10);
  requestBody.numSectionsYear4 = parseInt(elValue(document.getElementById('numSectionsYear4')) || 0, 10);

  // Validate that at least one program is selected
  if (selectedPrograms.length === 0) {
    document.getElementById('result').innerHTML = '<div class="alert alert-warning">Please select at least one program (CS or IT).</div>';
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
      // Saved schedule list refresh moved to separate page
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

async function loadDataManagementTables() {
  // Determine active tab and load only it
  const activeBtn = document.querySelector('#dataTabs .nav-link.active');
  const tab = activeBtn ? activeBtn.dataset.tab : 'subjects';
  if (tab === 'subjects') await loadSubjectsTable();
  else if (tab === 'teachers') await loadTeachersTable();
  else if (tab === 'rooms') await loadRoomsTable();
}

// Wire tab buttons to load content when activated (use Bootstrap event)
document.querySelectorAll('#dataTabs button[data-bs-toggle="tab"]').forEach(btn => {
  btn.addEventListener('shown.bs.tab', (e) => {
    const tab = e.target.dataset.tab;
    if (tab === 'subjects') {
      // Small delay to ensure DOM is rendered
      setTimeout(() => loadSubjectsTable(), 100);
    }
    else if (tab === 'teachers') loadTeachersTable();
    else if (tab === 'rooms') loadRoomsTable();
  });
});

// Wire refresh buttons
['subjects','teachers','rooms'].forEach(key => {
  const btn = document.getElementById(`${key}Refresh`);
  if (btn) btn.addEventListener('click', () => {
    if (key === 'subjects') loadSubjectsTable();
    if (key === 'teachers') loadTeachersTable();
    if (key === 'rooms') loadRoomsTable();
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
    const val = prompt(`Enter ${label}:`, initial[f] != null ? String(initial[f]) : '');
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
    const data = promptForData(['teacher_name','can_teach']);
    if (!data) return;
    const response = await fetch('/api/teachers', { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data) });
    if (response.ok) {
      const result = await response.json();
      alert(`Teacher added successfully with ID: ${result.teacher_id}`);
    }
    loadTeachersTable();
  };
  if (tEdit) tEdit.onclick = async () => {
    const selected = getSelectedRowData('teachersData', ['teacher_id','teacher_name','can_teach']);
    if (!selected || selected.length === 0) return alert('Select at least one row.');
    openBulkEditModal('teachers', ['teacher_name','can_teach'], selected);
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

  // Build form: checkboxes for fields and inputs for new values
  let html = '';
  html += `<p>${selectedRows.length} row(s) selected.</p>`;
  html += '<div class="table-responsive"><table class="table"><thead><tr><th>Apply</th><th>Field</th><th>New value</th></tr></thead><tbody>';
  fields.forEach(f => {
    const disabled = (f.endsWith('_id') || f === 'teacher_id' || f === 'room_id' || f === 'section_id') ? 'disabled' : '';
    const label = fieldLabels[f] || f;
    html += `<tr>
      <td><input type="checkbox" class="form-check-input" data-role="field-check" data-field="${f}" ${disabled && 'disabled'}></td>
      <td>${label}</td>
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
        ${!notification.is_read ? '<span class="badge bg-primary rounded-pill ms-2">New</span>' : ''}
      </div>
    </div>
  `;
  
  // Add click handler to mark as read
  li.addEventListener('click', async () => {
    if (!notification.is_read) {
      await markNotificationAsRead(notification.id);
      notification.is_read = true;
      li.querySelector('.dropdown-item').classList.remove('bg-light');
      li.querySelector('.badge').remove();
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

// Auto-refresh notifications every 30 seconds
setInterval(loadNotifications, 30000);
