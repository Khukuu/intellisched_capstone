from ortools.sat.python import cp_model
from database import load_subjects_from_db, load_teachers_from_db, load_rooms_from_db

def generate_schedule(subjects_data, teachers_data, rooms_data, semester_filter, desired_sections_per_year):
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
            cleaned_teachers_data.append({
                'teacher_id': teacher_id,  # Keep as integer
                'teacher_name': teacher_name.strip(),
                'can_teach': str(t.get('can_teach', '' )).replace(' ', '') # Ensure it's a string before replace
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

    # Define granular days and time slots (30-minute increments)
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    # Assuming 7 AM to 8 PM with a lunch break (12-1 PM)
    time_slot_labels = []
    for h in range(7, 20): # 7 AM to 8 PM (exclusive 9 PM)
        time_slot_labels.append(f"{h:02d}:00-{h:02d}:30")
        time_slot_labels.append(f"{h:02d}:30-{h+1:02d}:00")
    # Remove 12:00-1:00 for lunch break
    time_slot_labels = [ts for ts in time_slot_labels if not ("12:00-12:30" in ts or "12:30-13:00" in ts)]

    # Map 0 MW, 1 TTh, 2 FS to actual day indices for paired scheduling
    # (Mon, Wed), (Tue, Thu), (Fri, Sat)
    day_group_pairs_indices = {
        "MW": (day_labels.index("Mon"), day_labels.index("Wed")), 
        "TTh": (day_labels.index("Tue"), day_labels.index("Thu")), 
        "FS": (day_labels.index("Fri"), day_labels.index("Sat"))  
    }

    # Prepare a list of all individual meeting events to be scheduled
    meeting_events = []
    
    # Dynamically generate cohort sections (e.g., CS1A, CS1B) based on desired_sections_per_year
    all_dynamic_cohort_sections = [] 
    for year_level, num_sections in desired_sections_per_year.items():
        if num_sections <= 0:
            continue

        for section_idx in range(num_sections):
            # Generate section letter (A, B, C...)
            section_letter = chr(ord('A') + section_idx)
            # Generate cohort section ID (e.g., CS1A, CS2B) - assuming 'CS' prefix for now
            cohort_section_id = f"CS{year_level}{section_letter}"
            all_dynamic_cohort_sections.append({
                'section_id': cohort_section_id,
                'year_level': str(year_level),
                'semester': semester_filter # Attach the filtered semester for the cohort
            })

    if not all_dynamic_cohort_sections:
        print("Scheduler: No dynamic cohort sections generated based on desired year levels and semester filter.")
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
               (not cohort_semester or safe_int(s.get('semester'), None) == safe_int(cohort_semester, None))
        ]

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
            
            # Apply special room assignment rules
            # Rule 1: Specific CS subjects (CS6, CS10, CS14, CS21) must use Cisco Lab only
            if subject_code.upper() in ['CS6', 'CS10', 'CS14', 'CS21']:
                # Find Cisco Lab room
                cisco_lab_rooms = [r['room_id'] for r in rooms_data if 'cisco' in str(r.get('room_name', '')).lower()]
                if cisco_lab_rooms:
                    lecture_rooms_for_subj = cisco_lab_rooms
                    lab_rooms_for_subj = cisco_lab_rooms
                    print(f"Applied CS constraint: {subject_code} assigned to Cisco Lab only")
                else:
                    print(f"Warning: Cisco Lab not found for CS subject {subject_code}")
            
            # Rule 2: Only specific PE subjects (PE1, PE2, PE3, PE4) can use LPU_Gymnasium
            elif subject_code.upper() in ['PE1', 'PE2', 'PE3', 'PE4']:
                # Find LPU_Gymnasium room
                gym_rooms = [r['room_id'] for r in rooms_data if 'gymnasium' in str(r.get('room_name', '')).lower()]
                if gym_rooms:
                    lecture_rooms_for_subj = gym_rooms
                    lab_rooms_for_subj = gym_rooms
                    print(f"Applied PE constraint: {subject_code} assigned to LPU_Gymnasium only")
                else:
                    print(f"Warning: LPU_Gymnasium not found for PE subject {subject_code}")

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
                        'duration_slots': lecture_hours * 2,
                        'valid_teachers': valid_teachers_for_subj,
                        'valid_rooms': lecture_rooms_for_subj,
                        'meeting_idx': 0 
                    })
                if lab_hours > 0:
                    meeting_events.append({
                        'section_id': cohort_section_id, # Use cohort ID
                        'subject_code': subject_code,
                        'type': 'lab',
                        'duration_slots': lab_hours * 2,
                        'valid_teachers': valid_teachers_for_subj,
                        'valid_rooms': lab_rooms_for_subj,
                        'meeting_idx': 1 
                    })
            else:
                if lecture_hours > 0:
                    total_slots = int(lecture_hours * 2)
                    # If total slots can be evenly split, create two meetings across day pairs (e.g., MW/TTh/FS)
                    if total_slots % 2 == 0 and total_slots >= 2:
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
                        # Otherwise, schedule as a single meeting on one day
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
    
    # Add no-overlap constraint for each room (except LPU_Gymnasium for PE subjects only)
    for room_idx, room_id in enumerate(room_ids):
        if room_id in gym_room_ids:
            # Only skip room overlap constraint for LPU_Gymnasium if both events are PE subjects
            print(f"Checking LPU_Gymnasium constraint for room_id: {room_id}")
            # Find all events that can use this room
            events_for_room = []
            for i, event in enumerate(meeting_events):
                if room_id in event['valid_rooms']:
                    events_for_room.append(i)
            
            if len(events_for_room) > 1:
                print(f"Adding special LPU_Gymnasium constraint for room {room_id} with {len(events_for_room)} events")
                
                # Create conditional intervals for this room
                room_intervals = []
                for i in events_for_room:
                    # Check if this event is a PE subject
                    is_pe_subject = meeting_events[i]['subject_code'].upper() in ['PE1', 'PE2', 'PE3', 'PE4']
                    
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
                print(f"Applied AddNoOverlap constraint for LPU_Gymnasium with {len(room_intervals)} intervals")
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
    for i in range(len(meeting_events)):
        for j in range(i + 1, len(meeting_events)):
            if meeting_events[i]['section_id'] != meeting_events[j]['section_id']:
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

            mw_selected = model.NewBoolVar(f'daypair_MW_{section_id}_{subject_code}')
            tth_selected = model.NewBoolVar(f'daypair_TTh_{section_id}_{subject_code}')
            fs_selected = model.NewBoolVar(f'daypair_FS_{section_id}_{subject_code}')

            # Enforce lecture on first day and lab on second day of the pair
            model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["MW"][0]).OnlyEnforceIf(mw_selected)
            model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["MW"][1]).OnlyEnforceIf(mw_selected)

            model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["TTh"][0]).OnlyEnforceIf(tth_selected)
            model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["TTh"][1]).OnlyEnforceIf(tth_selected)

            model.Add(assigned_days[lecture_event_idx] == day_group_pairs_indices["FS"][0]).OnlyEnforceIf(fs_selected)
            model.Add(assigned_days[lab_event_idx] == day_group_pairs_indices["FS"][1]).OnlyEnforceIf(fs_selected)

            # Exactly one day pair must be selected
            model.Add(mw_selected + tth_selected + fs_selected == 1)

        # Case 2: Two non-lab meetings should be on the two days of a selected day pair
        non_lab_indices = [i for i in indices if meeting_events[i]['type'] == 'non_lab']
        if len(non_lab_indices) == 2:
            # Determine order via meeting_idx (0 -> first day, 1 -> second day)
            idx0 = min(non_lab_indices, key=lambda i: meeting_events[i]['meeting_idx'])
            idx1 = max(non_lab_indices, key=lambda i: meeting_events[i]['meeting_idx'])

            mw_selected = model.NewBoolVar(f'daypair_MW_nonlab_{section_id}_{subject_code}')
            tth_selected = model.NewBoolVar(f'daypair_TTh_nonlab_{section_id}_{subject_code}')
            fs_selected = model.NewBoolVar(f'daypair_FS_nonlab_{section_id}_{subject_code}')

            model.Add(assigned_days[idx0] == day_group_pairs_indices["MW"][0]).OnlyEnforceIf(mw_selected)
            model.Add(assigned_days[idx1] == day_group_pairs_indices["MW"][1]).OnlyEnforceIf(mw_selected)

            model.Add(assigned_days[idx0] == day_group_pairs_indices["TTh"][0]).OnlyEnforceIf(tth_selected)
            model.Add(assigned_days[idx1] == day_group_pairs_indices["TTh"][1]).OnlyEnforceIf(tth_selected)

            model.Add(assigned_days[idx0] == day_group_pairs_indices["FS"][0]).OnlyEnforceIf(fs_selected)
            model.Add(assigned_days[idx1] == day_group_pairs_indices["FS"][1]).OnlyEnforceIf(fs_selected)

            model.Add(mw_selected + tth_selected + fs_selected == 1)

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
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.num_search_workers = 8
    solver.parameters.cp_model_presolve = True
    solver.parameters.linearization_level = 1
    status = solver.Solve(model)
    print(f'Scheduler: Solver finished with status {status}')
    logs.append(f'Scheduler: Solver finished with status {status}')

    result = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
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

    # In fallback, keep constraints minimal to ensure a schedule is produced

    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = 10.0
    solver2.parameters.num_search_workers = 8
    status2 = solver2.Solve(model2)
    print(f'Scheduler: Fallback solver finished with status {status2}')
    logs.append(f'Scheduler: Fallback solver finished with status {status2}')

    if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
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
        return { 'schedule': result, 'logs': logs }

    print('Scheduler: No feasible solution found even after fallback.')
    logs.append('Scheduler: No feasible solution found even after fallback.')
    return { 'schedule': [], 'logs': logs }