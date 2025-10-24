from ortools.sat.python import cp_model
from database import load_subjects_from_db, load_teachers_from_db, load_rooms_from_db
import gc
import sys

def generate_schedule(subjects_data, teachers_data, rooms_data, semester_filter, program_sections, programs=['CS']):
    logs = []
    print('Scheduler: Initializing model...')
    model = cp_model.CpModel()

    # Mappings
    subject_map = {s['subject_code']: s for s in subjects_data}
    
    # Filter out teachers with missing IDs or names, and clean can_teach strings
    cleaned_teachers_data = []
    for t in teachers_data:
        teacher_id = t.get('teacher_id')
        teacher_name = t.get('teacher_name')
        if teacher_id and teacher_name:
            # Handle availability_days - default to all days if not specified
            availability_days = t.get('availability_days', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'])
            if not availability_days:  # Handle empty/null availability
                availability_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            
            cleaned_teachers_data.append({
                'teacher_id': teacher_id,  # Keep as integer
                'teacher_name': teacher_name.strip(),
                'can_teach': str(t.get('can_teach', '' )).replace(' ', ''), # Ensure it's a string before replace
                'availability_days': availability_days
            })
        else:
            print(f"Warning: Skipping teacher row due to missing ID or name: {t}")

    teacher_map = {t['teacher_id']: t for t in cleaned_teachers_data}
    print(f"Debug: Cleaned teachers data: {cleaned_teachers_data}") # New debug line
    
    # Handle case where no valid teachers are loaded
    if not cleaned_teachers_data:
        print("Error: No valid teacher data loaded. Cannot generate schedule.")
        return []

    teacher_ids = [t['teacher_id'] for t in cleaned_teachers_data]
    teacher_id_to_name = {t['teacher_id']: t['teacher_name'] for t in cleaned_teachers_data}

    room_map = {r['room_id']: r for r in rooms_data}
    room_ids = [r['room_id'] for r in rooms_data]
    room_names = [r['room_name'] for r in rooms_data]

    # Define days and time slots (30-minute increments to support 1.5 hour classes)
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]  # No Sunday classes
    # Standard hours: 7 AM to 6 PM (classes end at 6 PM)
    time_slot_labels = []
    for h in range(7, 18): # 7 AM to 6 PM (exclusive 6 PM)
        time_slot_labels.append(f"{h:02d}:00-{h:02d}:30")
        time_slot_labels.append(f"{h:02d}:30-{h+1:02d}:00")

    # Map 0 MW, 1 TTh, 2 FS to actual day indices for paired scheduling
    # (Mon, Wed), (Tue, Thu), (Fri, Sat)
    day_group_pairs_indices = {
        "MW": (day_labels.index("Mon"), day_labels.index("Wed")), 
        "TTh": (day_labels.index("Tue"), day_labels.index("Thu")), 
        "FS": (day_labels.index("Fri"), day_labels.index("Sat"))  
    }

    # Prepare a list of all individual meeting events to be scheduled
    meeting_events = []
    
    # Get available years from curriculum to avoid creating sections for non-existent years
    available_years = set()
    for subject in subjects_data:
        if subject.get('program', '').upper() in [p.upper() for p in programs]:
            year_level = subject.get('year_level')
            if year_level is not None:
                try:
                    available_years.add(int(year_level))
                except (ValueError, TypeError):
                    print(f"Warning: Invalid year_level '{year_level}' for subject {subject.get('subject_code', 'Unknown')}")
                    continue
    
    print(f"Available years in curriculum: {sorted(available_years)}")
    
    # Dynamically generate cohort sections for each program (e.g., CS1A, CS1B, IT1A, IT1B) based on program_sections
    all_dynamic_cohort_sections = [] 
    print(f"Debug: programs = {programs}")
    print(f"Debug: program_sections = {program_sections}")
    
    for program in programs:
        program_prefix = program.upper()
        program_section_counts = program_sections.get(program, {})
        print(f"Debug: Processing program {program_prefix}, section_counts = {program_section_counts}")
        
        for year_level, num_sections in program_section_counts.items():
            print(f"Debug: Processing year {year_level} with {num_sections} sections")
            if num_sections <= 0:
                print(f"Debug: Skipping year {year_level} - no sections requested")
                continue
            if year_level not in available_years:
                print(f"Skipping {program_prefix} Year {year_level} - no curriculum available")
                continue

            for section_idx in range(num_sections):
                # Generate section letter (A, B, C...)
                section_letter = chr(ord('A') + section_idx)
                # Generate cohort section ID (e.g., CS1A, CS2B or IT1A, IT2B)
                cohort_section_id = f"{program_prefix}{year_level}{section_letter}"
                cohort_section = {
                    'section_id': cohort_section_id,
                    'year_level': str(year_level),
                    'semester': semester_filter, # Attach the filtered semester for the cohort
                    'program': program.upper()
                }
                all_dynamic_cohort_sections.append(cohort_section)
                print(f"Debug: Created cohort section: {cohort_section}")

    if not all_dynamic_cohort_sections:
        print("Scheduler: No dynamic cohort sections generated based on desired year levels and semester filter.")
        print(f"Debug: semester_filter = {semester_filter}, program_sections = {program_sections}")
        print(f"Debug: available_years = {sorted(available_years)}")
        return []

    # Now, for each generated cohort section, add all relevant subjects as meeting events
    for cohort_section in all_dynamic_cohort_sections:
        cohort_section_id = cohort_section['section_id']
        cohort_year_level = int(cohort_section['year_level'])
        cohort_semester = cohort_section['semester']

        # Filter subjects that belong to this cohort's year_level and selected semester
        def safe_int(x, default=None):
            try:
                return int(float(x))
            except Exception:
                return default
        relevant_subjects = [
            s for s in subjects_data 
            if safe_int(s.get('year_level'), None) == cohort_year_level and 
               (not cohort_semester or safe_int(s.get('semester'), None) == safe_int(cohort_semester, None)) and
               (s.get('program', '').upper() == cohort_section['program'].upper() or 
                cohort_section['program'].upper() in s.get('available_programs', []))
        ]

        print(f"Debug: Cohort {cohort_section_id} (Program: {cohort_section['program']}, Year: {cohort_year_level}, Semester: {cohort_semester}) found {len(relevant_subjects)} relevant subjects")
        if relevant_subjects:
            for subj in relevant_subjects[:3]:  # Show first 3 subjects
                print(f"  - {subj.get('subject_code')} ({subj.get('program')})")
        
        if not relevant_subjects:
            print(f"Warning: No relevant subjects found for cohort {cohort_section_id} (Year {cohort_year_level}) in Semester {cohort_semester or 'All'}. Skipping this cohort.")
            continue

        for subj in relevant_subjects:
            subject_code = subj['subject_code'].strip()

            def safe_float(x):
                try:
                    return float(x)
                except Exception:
                    return 0.0
            lecture_hours = safe_float(subj.get('lecture_hours_per_week', 0))
            lab_hours = safe_float(subj.get('lab_hours_per_week', 0))
            is_lab_subject = (lab_hours > 0)

            valid_teachers_for_subj = [
                t['teacher_id'] for t in cleaned_teachers_data 
                if subject_code in t['can_teach'].split(',')
            ]
            # Prepare room lists for lecture vs lab components with special constraints
            lecture_rooms_for_subj = [
                r['room_id'] for r in rooms_data
                if not r.get('is_laboratory', False)
            ]
            lab_rooms_for_subj = [
                r['room_id'] for r in rooms_data
                if r.get('is_laboratory', False)
            ]
            
            # Apply special room assignment rules with exclusivity
            # Rule 1: Cisco Lab EXCLUSIVE to networking subjects (both lecture and lab sessions)
            networking_subjects = ['CS6', 'CS10', 'CS14', 'CS21', 'IT6', 'IT11', 'IT15', 'IT20']
            if subject_code.upper() in networking_subjects:
                # Find Cisco Lab room
                cisco_lab_rooms = [r['room_id'] for r in rooms_data if 'cisco' in str(r.get('room_name', '')).lower()]
                if cisco_lab_rooms:
                    # Both lecture and lab sessions use Cisco Lab only
                    lecture_rooms_for_subj = cisco_lab_rooms
                    lab_rooms_for_subj = cisco_lab_rooms
                    print(f"Applied Cisco Lab constraint: {subject_code} (lecture and lab) assigned to Cisco Lab only (networking subject)")
                else:
                    print(f"Warning: Cisco Lab not found for networking subject {subject_code}")
            else:
                # NON-networking subjects: EXCLUDE Cisco Lab rooms
                cisco_lab_rooms = [r['room_id'] for r in rooms_data if 'cisco' in str(r.get('room_name', '')).lower()]
                lecture_rooms_for_subj = [r for r in lecture_rooms_for_subj if r not in cisco_lab_rooms]
                lab_rooms_for_subj = [r for r in lab_rooms_for_subj if r not in cisco_lab_rooms]
            
            # Rule 2: Gymnasium EXCLUSIVE to PE subjects only
            pe_subjects = ['PE1', 'PE2', 'PE3', 'PE4']
            if subject_code.upper() in pe_subjects:
                # Find LPU_Gymnasium room
                gym_rooms = [r['room_id'] for r in rooms_data if 'gymnasium' in str(r.get('room_name', '')).lower()]
                if gym_rooms:
                    lecture_rooms_for_subj = gym_rooms
                    lab_rooms_for_subj = gym_rooms
                    print(f"Applied Gymnasium constraint: {subject_code} assigned to LPU_Gymnasium only (PE subject)")
                else:
                    print(f"Warning: LPU_Gymnasium not found for PE subject {subject_code}")
            else:
                # NON-PE subjects: EXCLUDE Gymnasium rooms
                gym_rooms = [r['room_id'] for r in rooms_data if 'gymnasium' in str(r.get('room_name', '')).lower()]
                lecture_rooms_for_subj = [r for r in lecture_rooms_for_subj if r not in gym_rooms]
                lab_rooms_for_subj = [r for r in lab_rooms_for_subj if r not in gym_rooms]

            # Rule 3: Physics subjects can use regular rooms for lab sessions (no computers needed)
            physics_subjects = ['PHYS1', 'PHYS2']
            if subject_code.upper() in physics_subjects:
                # Physics labs can use regular lecture rooms instead of laboratory rooms
                # But still respect gymnasium exclusion (physics doesn't need gymnasium)
                lab_rooms_for_subj = [
                    r['room_id'] for r in rooms_data
                    if not r.get('is_laboratory', False) and 'gymnasium' not in str(r.get('room_name', '')).lower()
                ]
                print(f"Applied Physics constraint: {subject_code} lab sessions can use regular rooms (no computers needed, excluding gymnasium)")

            # Skip unschedulable subjects
            if not valid_teachers_for_subj:
                print(f"Warning: Skipping {subject_code} for {cohort_section_id} due to no qualified teachers.")
                continue
            # For room feasibility, ensure at least one relevant room exists for any component that will be added
            if is_lab_subject:
                if lecture_hours > 0 and not lecture_rooms_for_subj:
                    print(f"Warning: Skipping {subject_code} lecture for {cohort_section_id} due to no matching lecture rooms.")
                    # do not continue yet; maybe the lab part can still be scheduled
                    lecture_hours = 0
                if lab_hours > 0 and not lab_rooms_for_subj:
                    print(f"Warning: Skipping {subject_code} lab for {cohort_section_id} due to no matching lab rooms.")
                    lab_hours = 0
                if lecture_hours == 0 and lab_hours == 0:
                    continue
            else:
                # non-lab subjects use lecture rooms
                if lecture_hours > 0 and not lecture_rooms_for_subj:
                    print(f"Warning: Skipping {subject_code} for {cohort_section_id} due to no matching lecture rooms.")
                    continue

            if is_lab_subject:
                if lecture_hours > 0:
                    meeting_events.append({
                        'section_id': cohort_section_id, # Use cohort ID
                        'subject_code': subject_code,
                        'type': 'lecture',
                        'duration_slots': int(lecture_hours * 2),
                        'valid_teachers': valid_teachers_for_subj,
                        'valid_rooms': lecture_rooms_for_subj,
                        'meeting_idx': 0 
                    })
                if lab_hours > 0:
                    meeting_events.append({
                        'section_id': cohort_section_id, # Use cohort ID
                        'subject_code': subject_code,
                        'type': 'lab',
                        'duration_slots': int(lab_hours * 2),
                        'valid_teachers': valid_teachers_for_subj,
                        'valid_rooms': lab_rooms_for_subj,
                        'meeting_idx': 1 
                    })
            else:
                if lecture_hours > 0:
                    total_slots = int(lecture_hours * 2)
                    
                    # Single session constraint for specific subjects
                    single_session_subjects = ['BSC1', 'BSC2', 'PE1', 'PE2', 'PE3', 'PE4']
                    is_single_session = subject_code in single_session_subjects
                    
                    if is_single_session:
                        print(f"Debug: Applying single session constraint for {subject_code}")
                    
                    # If total slots can be evenly split AND it's not a single session subject, create two meetings across day pairs (e.g., MW/TTh/FS)
                    if total_slots % 2 == 0 and total_slots >= 2 and not is_single_session:
                        half_slots = total_slots // 2
                        meeting_events.append({
                            'section_id': cohort_section_id,
                            'subject_code': subject_code,
                            'type': 'non_lab',
                            'duration_slots': half_slots,
                            'valid_teachers': valid_teachers_for_subj,
                            'valid_rooms': lecture_rooms_for_subj,
                            'meeting_idx': 0
                        })
                        meeting_events.append({
                            'section_id': cohort_section_id,
                            'subject_code': subject_code,
                            'type': 'non_lab',
                            'duration_slots': half_slots,
                            'valid_teachers': valid_teachers_for_subj,
                            'valid_rooms': lecture_rooms_for_subj,
                            'meeting_idx': 1
                        })
                    else:
                        # For single session subjects or when splitting is not possible, schedule as a single meeting on one day
                        meeting_events.append({
                            'section_id': cohort_section_id,
                            'subject_code': subject_code,
                            'type': 'non_lab',
                            'duration_slots': total_slots,
                            'valid_teachers': valid_teachers_for_subj,
                            'valid_rooms': lecture_rooms_for_subj,
                            'meeting_idx': 0
                        })
    
    print(f"Scheduler: Processing {len(meeting_events)} meeting events for scheduling.")

    # Variables for each meeting event
    assigned_starts = []
    assigned_days = []
    assigned_teachers_vars = [] # Teachers for each meeting event
    assigned_rooms_vars = [] # Rooms for each meeting event
    all_intervals = [] # For no-overlap constraint

    for i, event in enumerate(meeting_events):
        duration_slots = event['duration_slots']
        
        # Start time variable (index of 30-min slot)
        # Max start index ensures the meeting does not go past the end of the day
        latest_start = max(0, len(time_slot_labels) - int(duration_slots))
        start_var = model.NewIntVar(0, latest_start, f'start_{i}')
        assigned_starts.append(start_var)
        
        day_var = model.NewIntVar(0, len(day_labels) - 1, f'day_{i}')
        assigned_days.append(day_var)

        # Ensure valid_teachers is not empty before creating domain
        if not event['valid_teachers']:
            print(f"Error: No valid teachers for section {event['section_id']} (subject {event['subject_code']}). Problem infeasible.")
            return [] # Infeasible due to lack of teachers
        else:
            print(f"Debug: Section {event['section_id']} ({event['subject_code']}) has {len(event['valid_teachers'])} valid teachers.")

        teacher_var = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues([teacher_ids.index(tid) for tid in event['valid_teachers']]),
            f'teacher_{i}'
        )
        assigned_teachers_vars.append(teacher_var)
        
        # Add teacher availability day constraints
        # For each valid teacher, ensure they are only assigned to days they're available
        for teacher_idx, teacher_id in enumerate(event['valid_teachers']):
            teacher_data = teacher_map.get(teacher_id)
            if teacher_data and 'availability_days' in teacher_data:
                teacher_available_days = teacher_data['availability_days']
                teacher_name = teacher_data.get('teacher_name', 'Unknown')
                
                
                # Create a boolean variable for this teacher being selected
                # The teacher_var represents the index in valid_teachers, teacher_idx is the current teacher's position
                teacher_selected = model.NewBoolVar(f'teacher_selected_{i}_{teacher_idx}')
                model.Add(teacher_var == teacher_idx).OnlyEnforceIf(teacher_selected)
                model.Add(teacher_var != teacher_idx).OnlyEnforceIf(teacher_selected.Not())
                
                # For each day, if this teacher is selected, ensure the day is in their availability
                for day_idx, day_label in enumerate(day_labels):
                    if day_label not in teacher_available_days:
                        
                        # Create boolean variable for day assignment
                        day_assigned = model.NewBoolVar(f'day_assigned_{i}_{day_idx}')
                        model.Add(assigned_days[i] == day_idx).OnlyEnforceIf(day_assigned)
                        model.Add(assigned_days[i] != day_idx).OnlyEnforceIf(day_assigned.Not())
                        
                        # If teacher is selected, they cannot be assigned to unavailable days
                        # This means: NOT(teacher_selected AND day_assigned) when day is not available
                        # Which is equivalent to: NOT(teacher_selected) OR NOT(day_assigned)
                        model.AddBoolOr([teacher_selected.Not(), day_assigned.Not()])

        # Ensure valid_rooms is not empty before creating domain
        if not event['valid_rooms']:
            print(f"Error: No valid rooms for section {event['section_id']} (subject {event['subject_code']}). Problem infeasible.")
            return [] # Infeasible due to lack of rooms
        else:
            print(f"Debug: Section {event['section_id']} ({event['subject_code']}) has {len(event['valid_rooms'])} valid rooms.")
        room_var = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues([room_ids.index(rid) for rid in event['valid_rooms']]),
            f'room_{i}'
        )
        assigned_rooms_vars.append(room_var)

        # Create interval for no-overlap constraint
        interval_var = model.NewIntervalVar(
            start_var, int(duration_slots), start_var + int(duration_slots), f'interval_{i}'
        )
        all_intervals.append(interval_var)

    print('Scheduler: Adding constraints...')
    logs.append('Scheduler: Adding constraints...')
    
    # Debug: Print room availability
    print(f"Total events to schedule: {len(meeting_events)}")
    print(f"Total rooms available: {len(rooms_data)}")
    for room in rooms_data:
        print(f"  - {room['room_id']}: {room['room_name']}")
    
    # Debug: Print event room requirements
    for i, event in enumerate(meeting_events):
        print(f"Event {i}: {event['subject_code']} ({event['section_id']}) - {len(event['valid_rooms'])} valid rooms: {event['valid_rooms']}")
    
    # Add room preference to distribute events more evenly
    # Create a simple room preference based on event index to avoid all events using the same room
    for i, event in enumerate(meeting_events):
        if len(event['valid_rooms']) > 1:
            # Add a small preference to use different rooms based on event index
            preferred_room_idx = i % len(event['valid_rooms'])
            preferred_room_id = event['valid_rooms'][preferred_room_idx]
            preferred_room_index = room_ids.index(preferred_room_id)
            
            # Add a soft constraint to prefer this room (but don't make it mandatory)
            # This will help distribute events across different rooms
            room_preference = model.NewBoolVar(f'room_pref_{i}')
            model.Add(assigned_rooms_vars[i] == preferred_room_index).OnlyEnforceIf(room_preference)
            model.Add(assigned_rooms_vars[i] != preferred_room_index).OnlyEnforceIf(room_preference.Not())

    # Pairwise no-overlap for teachers on the same day
    for i in range(len(meeting_events)):
        for j in range(i + 1, len(meeting_events)):
            # Same teacher indicator (consistent with equality)
            same_teacher = model.NewBoolVar(f'same_teacher_{i}_{j}')
            model.Add(assigned_teachers_vars[i] == assigned_teachers_vars[j]).OnlyEnforceIf(same_teacher)
            model.Add(assigned_teachers_vars[i] != assigned_teachers_vars[j]).OnlyEnforceIf(same_teacher.Not())

            # Same day indicator
            same_day = model.NewBoolVar(f'same_day_{i}_{j}')
            model.Add(assigned_days[i] == assigned_days[j]).OnlyEnforceIf(same_day)
            model.Add(assigned_days[i] != assigned_days[j]).OnlyEnforceIf(same_day.Not())

            # Time separation disjunction for teacher overlap
            sep_ij_t = model.NewBoolVar(f'separate_{i}_{j}_t')
            sep_ji_t = model.NewBoolVar(f'separate_{j}_{i}_t')
            model.Add(assigned_starts[i] + int(meeting_events[i]['duration_slots']) <= assigned_starts[j]).OnlyEnforceIf(sep_ij_t)
            model.Add(assigned_starts[j] + int(meeting_events[j]['duration_slots']) <= assigned_starts[i]).OnlyEnforceIf(sep_ji_t)
            model.AddBoolOr([sep_ij_t, sep_ji_t, same_teacher.Not(), same_day.Not()])

    # Simple room overlap constraint using AddNoOverlap
    # Get gymnasium room IDs
    gym_room_ids = [r['room_id'] for r in rooms_data if 'gymnasium' in str(r.get('room_name', '')).lower()]
    
    # Create intervals for each event
    event_intervals = []
    for i, event in enumerate(meeting_events):
        # Create interval for this event
        interval = model.NewIntervalVar(
            assigned_starts[i],
            int(event['duration_slots']),
            assigned_starts[i] + int(event['duration_slots']),
            f'event_interval_{i}'
        )
        event_intervals.append(interval)
    
    # Add no-overlap constraint for each room (except LPU_Gymnasium - can host multiple PE classes)
    for room_idx, room_id in enumerate(room_ids):
        if room_id in gym_room_ids:
            # Skip room overlap constraint for LPU_Gymnasium - it can host multiple PE classes simultaneously
            print(f"Skipping overlap constraint for LPU_Gymnasium (room_id: {room_id}) - can host multiple PE classes")
            continue
            
        # Find all events that can use this room
        events_for_room = []
        for i, event in enumerate(meeting_events):
            if room_id in event['valid_rooms']:
                events_for_room.append(i)
        
        if len(events_for_room) > 1:
            print(f"Adding room overlap constraint for room {room_id} with {len(events_for_room)} events")
            
            # Create conditional intervals for this room
            room_intervals = []
            for i in events_for_room:
                # Create a conditional interval that only exists if this event is assigned to this room
                room_assigned = model.NewBoolVar(f'room_{room_id}_assigned_{i}')
                model.Add(assigned_rooms_vars[i] == room_idx).OnlyEnforceIf(room_assigned)
                model.Add(assigned_rooms_vars[i] != room_idx).OnlyEnforceIf(room_assigned.Not())
                
                # Create interval that only exists when room is assigned
                room_interval = model.NewOptionalIntervalVar(
                    assigned_starts[i], 
                    int(meeting_events[i]['duration_slots']), 
                    assigned_starts[i] + int(meeting_events[i]['duration_slots']),
                    room_assigned,
                    f'room_{room_id}_interval_{i}'
                )
                room_intervals.append(room_interval)
            
            # Add no-overlap constraint for this room
            model.AddNoOverlap(room_intervals)
            print(f"Applied AddNoOverlap constraint for room {room_id} with {len(room_intervals)} intervals")

    # Pairwise no-overlap for sections on the same day (prevent students' schedule clashes)
    # Only applies within the same program - IT and CS can coexist in same timeslot
    for i in range(len(meeting_events)):
        for j in range(i + 1, len(meeting_events)):
            # Extract program from section_id (e.g., "CS1A" -> "CS", "IT2B" -> "IT")
            section_i = meeting_events[i]['section_id']
            section_j = meeting_events[j]['section_id']
            
            # Only apply section overlap constraint if same section
            # Different programs (IT vs CS) can coexist in same timeslot
            if section_i != section_j:
                continue
                
            # Same day indicator for section
            same_day_s = model.NewBoolVar(f'same_day_section_{i}_{j}')
            model.Add(assigned_days[i] == assigned_days[j]).OnlyEnforceIf(same_day_s)
            model.Add(assigned_days[i] != assigned_days[j]).OnlyEnforceIf(same_day_s.Not())

            # Time separation disjunction for section overlap
            sep_ij_s = model.NewBoolVar(f'separate_{i}_{j}_s')
            sep_ji_s = model.NewBoolVar(f'separate_{j}_{i}_s')
            model.Add(assigned_starts[i] + int(meeting_events[i]['duration_slots']) <= assigned_starts[j]).OnlyEnforceIf(sep_ij_s)
            model.Add(assigned_starts[j] + int(meeting_events[j]['duration_slots']) <= assigned_starts[i]).OnlyEnforceIf(sep_ji_s)
            model.AddBoolOr([sep_ij_s, sep_ji_s, same_day_s.Not()])

    # Enforce same teacher across all meetings of the same subject within a section,
    # and apply day-pairing constraints for subject/section groups
    # Group events by (section_id, subject_code)
    groups = {}
    for idx, event in enumerate(meeting_events):
        key = (event['section_id'], event['subject_code'])
        groups.setdefault(key, []).append(idx)

    for (section_id, subject_code), indices in groups.items():
        # Same teacher for all meetings of this subject within the section
        if len(indices) > 1:
            first_teacher = assigned_teachers_vars[indices[0]]
            for k in indices[1:]:
                model.Add(assigned_teachers_vars[k] == first_teacher)

        # Identify event types in this group
        types_in_group = [meeting_events[i]['type'] for i in indices]
        # Case 1: Lecture + Lab pairing across a selected day pair
        if 'lecture' in types_in_group and 'lab' in types_in_group:
            lecture_event_idx = next(i for i in indices if meeting_events[i]['type'] == 'lecture')
            lab_event_idx = next(i for i in indices if meeting_events[i]['type'] == 'lab')

            # Get the teacher assigned to this subject
            teacher_var = assigned_teachers_vars[lecture_event_idx]
            teacher_id = meeting_events[lecture_event_idx]['valid_teachers'][0]  # Get first teacher as reference
            teacher_data = teacher_map.get(teacher_id)
            teacher_available_days = teacher_data.get('availability_days', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']) if teacher_data else ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            
            # Check if teacher has restricted availability (less than all 6 days)
            is_restricted_teacher = len(teacher_available_days) < 6
            
            if is_restricted_teacher:
                # For teachers with restricted availability, prioritize availability over day pairing
                # Schedule both lecture and lab on the same available day
                available_day_indices = [day_labels.index(day) for day in teacher_available_days if day in day_labels]
                
                if len(available_day_indices) > 0:
                    # Force both lecture and lab to be on the same day from available days
                    # Create boolean variables for each available day
                    same_day_vars = {}
                    for day_idx in available_day_indices:
                        day_name = day_labels[day_idx]
                        same_day_vars[day_name] = model.NewBoolVar(f'same_day_{day_name}_{section_id}_{subject_code}')
                    
                    # Exactly one available day must be selected for both lecture and lab
                    model.Add(sum(same_day_vars.values()) == 1)
                    
                    # Enforce both lecture and lab on the same selected day
                    for day_name, day_var in same_day_vars.items():
                        day_idx = day_labels.index(day_name)
                        model.Add(assigned_days[lecture_event_idx] == day_idx).OnlyEnforceIf(day_var)
                        model.Add(assigned_days[lab_event_idx] == day_idx).OnlyEnforceIf(day_var)
                
                # Skip day pairing constraint entirely for restricted teachers
                # Let individual teacher availability constraints handle the scheduling
            else:
                # For teachers with full availability, use standard day pairing
                available_day_pairs = []
                if all(day in teacher_available_days for day in ['Mon', 'Wed']):
                    available_day_pairs.append('MW')
                if all(day in teacher_available_days for day in ['Tue', 'Thu']):
                    available_day_pairs.append('TTh')
                if all(day in teacher_available_days for day in ['Fri', 'Sat']):
                    available_day_pairs.append('FS')
                
                # Create boolean variables only for available day pairs
                day_pair_vars = {}
                for pair in available_day_pairs:
                    day_pair_vars[pair] = model.NewBoolVar(f'daypair_{pair}_{section_id}_{subject_code}')
                
                # Enforce lecture on first day and lab on second day of each available pair
                for pair in available_day_pairs:
                    first_day_idx = day_group_pairs_indices[pair][0]
                    second_day_idx = day_group_pairs_indices[pair][1]
                    
                    model.Add(assigned_days[lecture_event_idx] == first_day_idx).OnlyEnforceIf(day_pair_vars[pair])
                    model.Add(assigned_days[lab_event_idx] == second_day_idx).OnlyEnforceIf(day_pair_vars[pair])
                
                # Exactly one available day pair must be selected
                model.Add(sum(day_pair_vars.values()) == 1)

        # Case 2: Two non-lab meetings should be on the two days of a selected day pair
        non_lab_indices = [i for i in indices if meeting_events[i]['type'] == 'non_lab']
        if len(non_lab_indices) == 2:
            # Determine order via meeting_idx (0 -> first day, 1 -> second day)
            idx0 = min(non_lab_indices, key=lambda i: meeting_events[i]['meeting_idx'])
            idx1 = max(non_lab_indices, key=lambda i: meeting_events[i]['meeting_idx'])

            # Get the teacher assigned to this subject
            teacher_id = meeting_events[idx0]['valid_teachers'][0]  # Get first teacher as reference
            teacher_data = teacher_map.get(teacher_id)
            teacher_available_days = teacher_data.get('availability_days', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']) if teacher_data else ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            
            # Check if teacher has restricted availability (less than all 6 days)
            is_restricted_teacher = len(teacher_available_days) < 6
            
            if is_restricted_teacher:
                # For teachers with restricted availability, prioritize availability over day pairing
                # Schedule both meetings on the same available day
                available_day_indices = [day_labels.index(day) for day in teacher_available_days if day in day_labels]
                
                if len(available_day_indices) > 0:
                    # Force both meetings to be on the same day from available days
                    # Create boolean variables for each available day
                    same_day_vars = {}
                    for day_idx in available_day_indices:
                        day_name = day_labels[day_idx]
                        same_day_vars[day_name] = model.NewBoolVar(f'same_day_nonlab_{day_name}_{section_id}_{subject_code}')
                    
                    # Exactly one available day must be selected for both meetings
                    model.Add(sum(same_day_vars.values()) == 1)
                    
                    # Enforce both meetings on the same selected day
                    for day_name, day_var in same_day_vars.items():
                        day_idx = day_labels.index(day_name)
                        model.Add(assigned_days[idx0] == day_idx).OnlyEnforceIf(day_var)
                        model.Add(assigned_days[idx1] == day_idx).OnlyEnforceIf(day_var)
                
                # Skip day pairing constraint entirely for restricted teachers
                # Let individual teacher availability constraints handle the scheduling
            else:
                # For teachers with full availability, use standard day pairing
                available_day_pairs = []
                if all(day in teacher_available_days for day in ['Mon', 'Wed']):
                    available_day_pairs.append('MW')
                if all(day in teacher_available_days for day in ['Tue', 'Thu']):
                    available_day_pairs.append('TTh')
                if all(day in teacher_available_days for day in ['Fri', 'Sat']):
                    available_day_pairs.append('FS')
                
                # Create boolean variables only for available day pairs
                day_pair_vars = {}
                for pair in available_day_pairs:
                    day_pair_vars[pair] = model.NewBoolVar(f'daypair_{pair}_nonlab_{section_id}_{subject_code}')
                
                # Enforce first meeting on first day and second meeting on second day of each available pair
                for pair in available_day_pairs:
                    first_day_idx = day_group_pairs_indices[pair][0]
                    second_day_idx = day_group_pairs_indices[pair][1]
                    
                    model.Add(assigned_days[idx0] == first_day_idx).OnlyEnforceIf(day_pair_vars[pair])
                    model.Add(assigned_days[idx1] == second_day_idx).OnlyEnforceIf(day_pair_vars[pair])
                
                # Exactly one available day pair must be selected
                model.Add(sum(day_pair_vars.values()) == 1)

    # Constraint 3: Same teacher and room for all meetings of a section
    # sections_meetings = {} # section_id: [list of event indices]
    # for i, event in enumerate(meeting_events):
    #     if event['section_id'] not in sections_meetings:
    #         sections_meetings[event['section_id']] = []
    #     sections_meetings[event['section_id']].append(i)
    
    # for section_id, event_indices in sections_meetings.items():
    #     if len(event_indices) > 1:
    #         # All meetings for this section must have the same teacher
    #         first_teacher_var = assigned_teachers_vars[event_indices[0]]
    #         for i in event_indices[1:]:
    #             model.Add(assigned_teachers_vars[i] == first_teacher_var)
    #         # All meetings for this section must have the same room
    #         first_room_var = assigned_rooms_vars[event_indices[0]]
    #         for i in event_indices[1:]:
    #             model.Add(assigned_rooms_vars[i] == first_room_var)

    # Constraint 4: Lab Day Pairing (MW, TTh, FS)
    # for section_id, indices in sections_meetings.items():
    #     section_events = [meeting_events[idx] for idx in indices]
    #     # Check if this section has both lecture and lab components
    #     has_lecture_comp = any(e['type'] == 'lecture' for e in section_events)
    #     has_lab_comp = any(e['type'] == 'lab' for e in section_events)

    #     if has_lecture_comp and has_lab_comp: 
    #         lecture_event_idx = next(idx for idx in indices if meeting_events[idx]['type'] == 'lecture')
    #         lab_event_idx = next(idx for idx in indices if meeting_events[idx]['type'] == 'lab')
            
    #         # Create Boolean variables for day comparisons
    #         lec_on_mon = model.NewBoolVar(f'lec_mon_{section_id}')
    #         model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["MW"][0]).OnlyEnforceIf(lec_on_mon)
    #         lec_on_wed = model.NewBoolVar(f'lec_wed_{section_id}')
    #         model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["MW"][1]).OnlyEnforceIf(lec_on_wed)
            
    #         lec_on_tue = model.NewBoolVar(f'lec_tue_{section_id}')
    #         model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["TTh"][0]).OnlyEnforceIf(lec_on_tue)
    #         lec_on_thu = model.NewBoolVar(f'lec_thu_{section_id}')
    #         model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["TTh"][1]).OnlyEnforceIf(lec_on_thu)

    #         lec_on_fri = model.NewBoolVar(f'lec_fri_{section_id}')
    #         model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["FS"][0]).OnlyEnforceIf(lec_on_fri)
    #         lec_on_sat = model.NewBoolVar(f'lec_sat_{section_id}')
    #         model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["FS"][1]).OnlyEnforceIf(lec_on_sat)

    #         # Define Boolean variables for each day group being selected
    #         mw_day_group_selected = model.NewBoolVar(f'mw_group_{section_id}')
    #         model.AddBoolOr([lec_on_mon, lec_on_wed]).OnlyEnforceIf(mw_day_group_selected)
    #         model.AddBoolAnd([lec_on_mon.Not(), lec_on_wed.Not()]).OnlyEnforceIf(mw_day_group_selected.Not())
            
    #         tth_day_group_selected = model.NewBoolVar(f'tth_group_{section_id}')
    #         model.AddBoolOr([lec_on_tue, lec_on_thu]).OnlyEnforceIf(tth_day_group_selected)
    #         model.AddBoolAnd([lec_on_tue.Not(), lec_on_thu.Not()]).OnlyEnforceIf(tth_day_group_selected.Not())
            
    #         fs_day_group_selected = model.NewBoolVar(f'fs_group_{section_id}')
    #         model.AddBoolOr([lec_on_fri, lec_on_sat]).OnlyEnforceIf(fs_day_group_selected)
    #         model.AddBoolAnd([lec_on_fri.Not(), lec_on_sat.Not()]).OnlyEnforceIf(fs_day_group_selected.Not())

    #         # Ensure exactly one day group is selected for the pair
    #         model.Add(mw_day_group_selected + tth_day_group_selected + fs_day_group_selected == 1)

    #         # Lab day must be the *other* day in the same pair as lecture day
    #         model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["MW"][1]).OnlyEnforceIf(lec_on_mon)
    #         model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["MW"][0]).OnlyEnforceIf(lec_on_wed)
            
    #         model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["TTh"][1]).OnlyEnforceIf(lec_on_tue)
    #         model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["TTh"][0]).OnlyEnforceIf(lec_on_thu)
            
    #         model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["FS"][1]).OnlyEnforceIf(lec_on_fri)
    #         model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["FS"][0]).OnlyEnforceIf(lec_on_sat)

    print('Scheduler: Constraints added.')
    logs.append('Scheduler: Constraints added.')

    print('Scheduler: Solving...')
    logs.append('Scheduler: Solving...')
    solver = cp_model.CpSolver()
    # Relax search to improve feasibility
    solver.parameters.max_time_in_seconds = 60.0  # Increased time limit
    solver.parameters.num_search_workers = 8
    solver.parameters.cp_model_presolve = True
    solver.parameters.linearization_level = 1
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH  # Try different search strategies
    status = solver.Solve(model)
    print(f'Scheduler: Solver finished with status {status}')
    logs.append(f'Scheduler: Solver finished with status {status}')
    
    # Add detailed status information
    if status == cp_model.INFEASIBLE:
        print('Scheduler: Problem is infeasible - constraints are too strict')
        logs.append('Scheduler: Problem is infeasible - constraints are too strict')
    elif status == cp_model.UNKNOWN:
        print('Scheduler: Solver could not determine feasibility within time limit')
        logs.append('Scheduler: Solver could not determine feasibility within time limit')
    elif status == cp_model.OPTIMAL:
        print('Scheduler: Found optimal solution')
        logs.append('Scheduler: Found optimal solution')
    elif status == cp_model.FEASIBLE:
        print('Scheduler: Found feasible solution (may not be optimal)')
        logs.append('Scheduler: Found feasible solution (may not be optimal)')

    result = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print('Scheduler: Using MAIN solver result')
        logs.append('Scheduler: Using MAIN solver result')
        for i, event in enumerate(meeting_events):
            teacher_idx = solver.Value(assigned_teachers_vars[i])
            room_idx = solver.Value(assigned_rooms_vars[i])
            start_time_idx = solver.Value(assigned_starts[i])
            day_idx = solver.Value(assigned_days[i])

            result.append({
                'section_id': event['section_id'],
                'subject_code': event['subject_code'],
                'subject_name': subject_map.get(event['subject_code'], {}).get('subject_name', event['subject_code']),
                'type': event['type'], # 'lecture', 'lab', 'non_lab'
                'teacher_name': teacher_id_to_name[teacher_ids[teacher_idx]],
                'room_id': room_names[room_idx],
                'day': day_labels[day_idx],
                'start_time_slot': time_slot_labels[start_time_idx],
                'duration_slots': int(event['duration_slots'])
            })
        
        # Validate the schedule for conflicts
        validate_schedule(result, logs)
        # Memory cleanup
        gc.collect()
        return { 'schedule': result, 'logs': logs }

    # Fallback: retry without any overlap constraints to always produce a schedule
    print('Scheduler: No feasible solution found. Retrying without overlap constraints...')
    logs.append('Scheduler: No feasible solution found. Retrying without overlap constraints...')
    model2 = cp_model.CpModel()
    fb_assigned_starts = []
    fb_assigned_days = []
    fb_assigned_teachers = []
    fb_assigned_rooms = []

    for i, event in enumerate(meeting_events):
        duration_slots = int(event['duration_slots'])
        start_var = model2.NewIntVar(0, len(time_slot_labels) - duration_slots, f'fb_start_{i}')
        day_var = model2.NewIntVar(0, len(day_labels) - 1, f'fb_day_{i}')
        teacher_var = model2.NewIntVarFromDomain(
            cp_model.Domain.FromValues([teacher_ids.index(tid) for tid in event['valid_teachers']]),
            f'fb_teacher_{i}'
        )
        room_var = model2.NewIntVarFromDomain(
            cp_model.Domain.FromValues([room_ids.index(rid) for rid in event['valid_rooms']]),
            f'fb_room_{i}'
        )
        fb_assigned_starts.append(start_var)
        fb_assigned_days.append(day_var)
        fb_assigned_teachers.append(teacher_var)
        fb_assigned_rooms.append(room_var)

    # In fallback, add minimal critical constraints to prevent obvious conflicts
    # Add basic teacher and section overlap constraints (most critical)
    for i in range(len(meeting_events)):
        for j in range(i + 1, len(meeting_events)):
            # Same teacher cannot teach at same time
            same_teacher = model2.NewBoolVar(f'fb_same_teacher_{i}_{j}')
            model2.Add(fb_assigned_teachers[i] == fb_assigned_teachers[j]).OnlyEnforceIf(same_teacher)
            model2.Add(fb_assigned_teachers[i] != fb_assigned_teachers[j]).OnlyEnforceIf(same_teacher.Not())
            
            same_day = model2.NewBoolVar(f'fb_same_day_{i}_{j}')
            model2.Add(fb_assigned_days[i] == fb_assigned_days[j]).OnlyEnforceIf(same_day)
            model2.Add(fb_assigned_days[i] != fb_assigned_days[j]).OnlyEnforceIf(same_day.Not())
            
            # Time separation for same teacher on same day
            sep_ij = model2.NewBoolVar(f'fb_sep_{i}_{j}')
            sep_ji = model2.NewBoolVar(f'fb_sep_{j}_{i}')
            model2.Add(fb_assigned_starts[i] + int(meeting_events[i]['duration_slots']) <= fb_assigned_starts[j]).OnlyEnforceIf(sep_ij)
            model2.Add(fb_assigned_starts[j] + int(meeting_events[j]['duration_slots']) <= fb_assigned_starts[i]).OnlyEnforceIf(sep_ji)
            model2.AddBoolOr([sep_ij, sep_ji, same_teacher.Not(), same_day.Not()])
            
            # Same section cannot have overlapping classes (different programs can coexist)
            if meeting_events[i]['section_id'] == meeting_events[j]['section_id']:
                sep_ij_s = model2.NewBoolVar(f'fb_sep_section_{i}_{j}')
                sep_ji_s = model2.NewBoolVar(f'fb_sep_section_{j}_{i}')
                model2.Add(fb_assigned_starts[i] + int(meeting_events[i]['duration_slots']) <= fb_assigned_starts[j]).OnlyEnforceIf(sep_ij_s)
                model2.Add(fb_assigned_starts[j] + int(meeting_events[j]['duration_slots']) <= fb_assigned_starts[i]).OnlyEnforceIf(sep_ji_s)
                model2.AddBoolOr([sep_ij_s, sep_ji_s, same_day.Not()])

    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = 10.0
    solver2.parameters.num_search_workers = 8
    status2 = solver2.Solve(model2)
    print(f'Scheduler: Fallback solver finished with status {status2}')
    logs.append(f'Scheduler: Fallback solver finished with status {status2}')

    if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print('Scheduler: Using FALLBACK solver result')
        logs.append('Scheduler: Using FALLBACK solver result')
        for i, event in enumerate(meeting_events):
            teacher_idx = solver2.Value(fb_assigned_teachers[i])
            room_idx = solver2.Value(fb_assigned_rooms[i])
            start_time_idx = solver2.Value(fb_assigned_starts[i])
            day_idx = solver2.Value(fb_assigned_days[i])

            result.append({
                'section_id': event['section_id'],
                'subject_code': event['subject_code'],
                'subject_name': subject_map.get(event['subject_code'], {}).get('subject_name', event['subject_code']),
                'type': event['type'],
                'teacher_name': teacher_id_to_name[teacher_ids[teacher_idx]],
                'room_id': room_names[room_idx],
                'day': day_labels[day_idx],
                'start_time_slot': time_slot_labels[start_time_idx],
                'duration_slots': int(event['duration_slots'])
            })
        
        # Validate the fallback schedule for conflicts
        validate_schedule(result, logs)
        # Memory cleanup
        gc.collect()
        return { 'schedule': result, 'logs': logs }

    print('Scheduler: No feasible solution found even after fallback.')
    logs.append('Scheduler: No feasible solution found even after fallback.')
    
    # Memory cleanup
    gc.collect()
    return { 'schedule': [], 'logs': logs }

def validate_schedule(schedule, logs):
    """Validate the generated schedule for conflicts"""
    print('Scheduler: Validating schedule for conflicts...')
    logs.append('Scheduler: Validating schedule for conflicts...')
    
    conflicts = []
    
    # Check for section conflicts (same section, same day, overlapping times)
    # Note: Different programs (IT vs CS) can coexist in same timeslot
    for i, event1 in enumerate(schedule):
        for j, event2 in enumerate(schedule[i+1:], i+1):
            if (event1['section_id'] == event2['section_id'] and 
                event1['day'] == event2['day']):
                
                # Parse time slots
                start1 = event1['start_time_slot'].split('-')[0]
                end1 = event1['start_time_slot'].split('-')[1]
                start2 = event2['start_time_slot'].split('-')[0]
                end2 = event2['start_time_slot'].split('-')[1]
                
                # Check for overlap
                if (start1 < end2 and start2 < end1):
                    conflicts.append({
                        'type': 'section_conflict',
                        'section': event1['section_id'],
                        'day': event1['day'],
                        'event1': f"{event1['subject_code']} ({event1['start_time_slot']})",
                        'event2': f"{event2['subject_code']} ({event2['start_time_slot']})"
                    })
    
    # Check for teacher conflicts (same teacher, same day, overlapping times)
    for i, event1 in enumerate(schedule):
        for j, event2 in enumerate(schedule[i+1:], i+1):
            if (event1['teacher_name'] == event2['teacher_name'] and 
                event1['day'] == event2['day']):
                
                # Parse time slots
                start1 = event1['start_time_slot'].split('-')[0]
                end1 = event1['start_time_slot'].split('-')[1]
                start2 = event2['start_time_slot'].split('-')[0]
                end2 = event2['start_time_slot'].split('-')[1]
                
                # Check for overlap
                if (start1 < end2 and start2 < end1):
                    conflicts.append({
                        'type': 'teacher_conflict',
                        'teacher': event1['teacher_name'],
                        'day': event1['day'],
                        'event1': f"{event1['subject_code']} ({event1['start_time_slot']})",
                        'event2': f"{event2['subject_code']} ({event2['start_time_slot']})"
                    })
    
    if conflicts:
        print(f'Scheduler: Found {len(conflicts)} conflicts in generated schedule!')
        logs.append(f'Scheduler: Found {len(conflicts)} conflicts in generated schedule!')
        for conflict in conflicts:
            if conflict['type'] == 'section_conflict':
                msg = f"Section conflict: {conflict['section']} on {conflict['day']} - {conflict['event1']} vs {conflict['event2']}"
            else:
                msg = f"Teacher conflict: {conflict['teacher']} on {conflict['day']} - {conflict['event1']} vs {conflict['event2']}"
            print(f'Scheduler: {msg}')
            logs.append(f'Scheduler: {msg}')
    else:
        print('Scheduler: No conflicts found in generated schedule.')
        logs.append('Scheduler: No conflicts found in generated schedule.')