from ortools.sat.python import cp_model

model = cp_model.CpModel()

import csv

# Load subjects
subjects = []
with open('subjects.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print("Detected Headers:", reader.fieldnames)
    for row in reader:
        subjects.append({
            'code': row['subject_code'],
            'name': row['subject_name'],
            'units': int(row['units']),
            'is_lab': row['is_laboratory'].lower() == 'true'
        })

# Load teachers
teachers = []
with open('teachers.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print("Detected Headers:", reader.fieldnames)
    for row in reader:
        teachers.append({
            'id': row['teacher_id'],
            'name': row['teacher_name'],
            'can_teach': [s.strip() for s in row['can_teach'].split(',')]
        })

# Load rooms
rooms = []
with open('rooms.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print("Detected Headers:", reader.fieldnames)
    for row in reader:
        rooms.append({
            'id': row['room_id'],
            'name': row['room_name'],
            'is_lab': row['is_laboratory'].lower() == 'true'
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



