from ortools.sat.python import cp_model
from database import load_courses_from_db, load_teachers_from_db, load_rooms_from_db

model = cp_model.CpModel()

# Load courses from database
courses_data = load_courses_from_db()
courses = []
seen_codes = set()
for row in courses_data:
    code = row['course_code']
    if code in seen_codes:
        continue
    seen_codes.add(code)
    # Convert database format to expected format
    is_lab = row.get('lab_hours_per_week', 0) > 0
    courses.append({
        'code': code,
        'name': row['course_name'],
        'units': int(row['units']),
        'is_lab': is_lab
    })
print("📦 Loaded Courses:", [c['code'] for c in courses])

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

#MAPPING COURSES TO TEACHERS AND ROOMS

#Course code and mapping
course_codes = [c['code'] for c in courses]
course_map = {ccode: i for i, ccode in enumerate(course_codes)}
course_code_from_index = {i: ccode for ccode, i in course_map.items()}

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
print("✅ Course Map:", course_map)


# Build course options
course_options = []

for c in courses:
    course_index = course_map[c['code']]
    
    valid_teachers = [
        teacher_map[t['id']] for t in teachers if c['code'] in t['can_teach']
    ]
    
    valid_rooms = [
        room_map[r['id']] for r in rooms if r['is_lab'] == c['is_lab']
    ]
    
    course_options.append({
        'course_index': course_index,
        'valid_teachers': valid_teachers,
        'valid_rooms': valid_rooms
    })

print("🔢 Total Course Options:", len(course_options))
for options in course_options:
    code = course_code_from_index[options['course_index']]
    print(f"Course {code} - Valid Teachers: {options['valid_teachers']}, Valid Rooms: {options['valid_rooms']}")


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
for i, option in enumerate(course_options):
    code = course_code_from_index[option['course_index']]
    print(f"\n🔧 Course {code}:")
    print(f"  ➤ Valid Teachers (IDs): {option['valid_teachers']}")
    print(f"  ➤ Valid Rooms (IDs): {option['valid_rooms']}")
    print(f"  ➤ Variable Names: teacher_c{i}, room_c{i}, day_c{i}, time_c{i}")

print(f"\n🧮 Total Courses: {len(course_options)}")
print(f"🧠 Total Variables Created: {len(assigned_teachers)} teachers, {len(assigned_rooms)} rooms")
