from ortools.sat.python import cp_model
from database import load_subjects_from_db, load_teachers_from_db, load_rooms_from_db

model = cp_model.CpModel()

# Load subjects from database
subjects_data = load_subjects_from_db()
subjects = []
seen_codes = set()
for row in subjects_data:
    code = row['subject_code']
    if code in seen_codes:
        continue
    seen_codes.add(code)
    # Convert database format to expected format
    is_lab = row.get('lab_hours_per_week', 0) > 0
    subjects.append({
        'code': code,
        'name': row['subject_name'],
        'units': int(row['units']),
        'is_lab': is_lab
    })
print("📦 Loaded Subjects:", [s['code'] for s in subjects])

# Load teachers from database
teachers_data = load_teachers_from_db()
teachers = []
for row in teachers_data:
    teachers.append({
        'id': row['teacher_id'],
        'name': row['teacher_name'],
        'can_teach': [s.strip() for s in row['can_teach'].split(',')] if row['can_teach'] else []
    })

# Load rooms from database
rooms_data = load_rooms_from_db()
rooms = []
for row in rooms_data:
    rooms.append({
        'id': row['room_id'],
        'name': row['room_name'],
        'is_lab': row['is_laboratory']
    })

#MAPPING SUBJECTS TO TEACHERS AND ROOMS

#Subject code and mapping
subject_codes = [s['code'] for s in subjects]
subject_map = {scode: i for i, scode in enumerate(subject_codes)}
subject_code_from_index = {i: scode for scode, i in subject_map.items()}

#Teacher ID and mapping
teacher_ids = [t['id'] for t in teachers]
teacher_map = {tid: i for i, tid in enumerate(teacher_ids)}
teacher_id_from_index = {i: tid for tid, i in teacher_map.items()}

#Room ID and mapping
room_ids = [r['id'] for r in rooms]
room_map = {rid: i for i, rid in enumerate(room_ids)}
room_id_from_index = {i: rid for rid, i in room_map.items()}

#DEBUGGING OUTPUT
print("✅ Teacher Map:", teacher_map)
print("✅ Room Map:", room_map)
print("✅ Subject Map:", subject_map)


# Build subject options
subject_options = []

for s in subjects:
    subject_index = subject_map[s['code']]
    
    valid_teachers = [
        teacher_map[t['id']] for t in teachers if s['code'] in t['can_teach']
    ]
    
    valid_rooms = [
        room_map[r['id']] for r in rooms if r['is_lab'] == s['is_lab']
    ]
    
    subject_options.append({
        'subject_index': subject_index,
        'valid_teachers': valid_teachers,
        'valid_rooms': valid_rooms
    })

print("🔢 Total Subject Options:", len(subject_options))
for options in subject_options:
    code = subject_code_from_index[options['subject_index']]
    print(f"Subject {code} - Valid Teachers: {options['valid_teachers']}, Valid Rooms: {options['valid_rooms']}")


day_groups = [0,1,2] # 0 MW, 1 TTh, 2 F
time_slots_per_day = 4


assigned_teachers = []
assigned_rooms = []
assigned_days = []
assigned_time_slots = []

for option in subject_options:
    subj_idx = option['subject_index']
    
    teacher_var = model.NewIntVarFromDomain(
        cp_model.Domain.FromValues(option['valid_teachers']),
        f'teacher_{subj_idx}'
    )
    
    room_var = model.NewIntVarFromDomain(
        cp_model.Domain.FromValues(option['valid_rooms']),
        f'room_{subj_idx}'
    )
    day_var = model.NewIntVar(0,len(day_groups) - 1, f'day_{subj_idx}')
    time_var = model.NewIntVar(0, time_slots_per_day - 1, f'time_{subj_idx}')
    
    assigned_teachers.append(teacher_var)
    assigned_rooms.append(room_var) 
    assigned_days.append(day_var)
    assigned_time_slots.append(time_var)
    
    
    
# DEBUG CODE
print("\n📋 Assigned Variables Summary:")
for i, option in enumerate(subject_options):
    code = subject_code_from_index[option['subject_index']]
    print(f"\nSubject {code}:")
    print(f"  ➤ Valid Teachers (IDs): {option['valid_teachers']}")
    print(f"  ➤ Valid Rooms (IDs): {option['valid_rooms']}")
    print(f"  ➤ Variable Names: teacher_s{i}, room_s{i}, day_s{i}, time_s{i}")

print(f"\n🧮 Total Subjects: {len(subject_options)}")
print(f"🧠 Total Variables Created: {len(assigned_teachers)} teachers, {len(assigned_rooms)} rooms")
