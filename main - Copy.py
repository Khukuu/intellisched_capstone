from ortools.sat.python import cp_model
from database import load_courses_from_db, load_teachers_from_db, load_rooms_from_db

model = cp_model.CpModel()

# Load subjects from database
subjects_data = load_courses_from_db()
subjects = []
for row in subjects_data:
    # Convert database format to expected format
    is_lab = row.get('lab_hours_per_week', 0) > 0
    subjects.append({
        'code': row['subject_code'],
        'name': row['subject_name'],
        'units': int(row['units']),
        'is_lab': is_lab
    })

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



