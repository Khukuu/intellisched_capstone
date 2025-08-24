const downloadBtn = document.getElementById('downloadBtn');
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
const viewMode = document.getElementById('viewMode');
const saveBtn = document.getElementById('saveBtn');
const saveNameInput = document.getElementById('saveNameInput');
const savedSchedulesSelect = document.getElementById('savedSchedulesSelect');
const loadBtn = document.getElementById('loadBtn');

// Keep last generated schedule in memory for filtering
let lastGeneratedSchedule = [];
let lastSavedId = '';

// Cached data for tabs so searches/filtering work reliably
let subjectsCache = [];
let teachersCache = [];
let roomsCache = [];
let sectionsCache = [];

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

  if (sectionId === 'schedule-section') {
    scheduleSection.style.display = 'block';
    scheduleNavLink.classList.add('active');
  } else if (sectionId === 'data-management-section') {
    dataManagementSection.style.display = 'block';
    dataNavLink.classList.add('active');
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
const subjectColorCache = {};
function hashStringToInt(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}
function getSubjectColor(subjectCode) {
  const key = String(subjectCode || '');
  if (subjectColorCache[key]) return subjectColorCache[key];
  const idx = hashStringToInt(key) % SUBJECT_COLOR_PALETTE.length;
  const color = SUBJECT_COLOR_PALETTE[idx];
  subjectColorCache[key] = color;
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
  document.getElementById('result').innerHTML = "Generating schedule...";
  document.getElementById('timetable').innerHTML = "";

  const selectedSemester = elValue(document.getElementById('semesterSelect')) || null;
  const requestBody = { semester: selectedSemester };
  requestBody.numSectionsYear1 = parseInt(elValue(document.getElementById('numSectionsYear1')) || 0, 10);
  requestBody.numSectionsYear2 = parseInt(elValue(document.getElementById('numSectionsYear2')) || 0, 10);
  requestBody.numSectionsYear3 = parseInt(elValue(document.getElementById('numSectionsYear3')) || 0, 10);
  requestBody.numSectionsYear4 = parseInt(elValue(document.getElementById('numSectionsYear4')) || 0, 10);

  // Pre-validate against curriculum: zero-out years that have no subjects in selected semester
  try {
    const subjectsResponse = await fetch('/data/cs_curriculum');
    const subjectsData = await subjectsResponse.json();
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

    renderScheduleAndTimetable(lastGeneratedSchedule);
    populateFilters(lastGeneratedSchedule);
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
  saveBtn.addEventListener('click', async () => {
    if (!Array.isArray(lastGeneratedSchedule) || lastGeneratedSchedule.length === 0) {
      alert('No schedule to save. Generate a schedule first.');
      return;
    }
    const name = (saveNameInput && saveNameInput.value.trim()) || '';
    try {
      const resp = await fetch('/save_schedule', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name,
          semester: semesterSelect ? semesterSelect.value : undefined,
          schedule: lastGeneratedSchedule
        })
      });
      const res = await resp.json();
      if (!resp.ok) {
        throw new Error(res.detail || 'Failed to save schedule');
      }
      lastSavedId = res.id || '';
      refreshSavedSchedulesList(lastSavedId);
      alert('Schedule saved.');
    } catch (e) {
      console.error(e);
      alert('Error saving schedule.');
    }
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
      const count = typeof item.count === 'number' ? ` (${item.count})` : '';
      opt.textContent = `${labelName} ${extra} ${count}`.trim();
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
  renderScheduleAndTimetable(lastGeneratedSchedule);
});

sectionFilter.addEventListener('change', () => {
  renderScheduleAndTimetable(lastGeneratedSchedule);
});

function applyFilters(data) {
  const y = yearFilter.value;
  const s = sectionFilter.value;
  return data.filter(e => {
    let ok = true;
    if (y !== 'all') {
      const m = /^CS(\d)/.exec(e.section_id || '');
      ok = ok && m && m[1] === y;
    }
    if (s !== 'all') ok = ok && e.section_id === s;
    return ok;
  });
}

function renderScheduleAndTimetable(data) {
  const filtered = applyFilters(Array.isArray(data) ? data : []);

  // Schedule Table (left)
  let html = '<div class="table-responsive"><table class="table table-striped"><thead><tr><th>Section ID</th><th>Subject</th><th>Type</th><th>Teacher</th><th>Room</th><th>Day</th><th>Time</th></tr></thead><tbody>';
  for (const row of filtered) {
    const subj = row.subject_name || row.subject_code || '';
    const timeRange = computeEventTimeRange(row);
    html += `<tr>
      <td>${row.section_id}</td>
      <td>${subj}</td>
      <td>${row.type}</td>
      <td>${row.teacher_name}</td>
      <td>${row.room_id}</td>
      <td>${row.day}</td>
      <td>${timeRange}</td>
    </tr>`;
  }
  html += "</tbody></table></div>";
  document.getElementById('result').innerHTML = html;
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
          const bg = getSubjectColor(ev.subject_code);
          const fg = getTextColorForBackground(bg);
          tthtml += `<td rowspan="${span}" style="background:${bg}; color:${fg};">
            <b>${subj}</b> <small style=\"color:#000; opacity:.85\">(${range})</small><br>
            ${ev.section_id}<br>${ev.teacher_name}<br>${ev.room_id}
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
              const bg = getSubjectColor(slot.subject_code);
              const fg = getTextColorForBackground(bg);
              return `<div style=\"background:${bg}; color:${fg}; padding:4px 6px; border-radius:6px; margin-bottom:4px;\">
                <b>${subj}</b> <small style=\"opacity:.85; color:#000\">(${range})</small><br>
                ${slot.section_id}<br>${slot.teacher_name}<br>${slot.room_id}
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
  document.getElementById('timetable').innerHTML = tthtml;
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
  if (!Array.isArray(data) || data.length === 0) {
    document.getElementById(elementId).innerHTML = '<p>No data available.</p>';
    return;
  }
  let tableHtml = '<table class="table table-striped table-bordered"><thead><tr>';
  headers.forEach(header => {
    tableHtml += `<th>${header}</th>`;
  });
  tableHtml += '</tr></thead><tbody>';
  data.forEach(row => {
    tableHtml += '<tr>';
    headers.forEach(header => {
      tableHtml += `<td>${row[header]}</td>`;
    });
    tableHtml += '</tr>';
  });
  tableHtml += '</tbody></table>';
  document.getElementById(elementId).innerHTML = tableHtml;
}