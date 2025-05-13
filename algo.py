from ortools.sat.python import cp_model

#TEST DATA
subjects = [
    {
        "name": "Data Structures",
        "faculty": "Prof. Ada",
        "section": "BSCS1A",
        "total_duration": 5,
        "min_sessions": 2,
        "max_sessions": 2,
        "room": "Lab_01",  #MAY MGA ASSIGN ROOM MERON WALA
    },
    {
        "name": "Programming",
        "faculty": "Prof. Melody",
        "section": "BSCS1A",
        "total_duration": 5,
        "min_sessions": 2,
        "max_sessions": 2,
        "room": "Lab_02",
    },
    {
        "name": "Comp Architecture",
        "faculty": "Prof. Jeram",
        "section": "BSCS1A",
        "total_duration": 5,
        "min_sessions": 2,
        "max_sessions": 2,
        "room": "Lab_01",
    },
    {
        "name": "Trigonometry",
        "faculty": "Prof. AA",
        "section": "BSCS1A",
        "total_duration": 3,
        "min_sessions": 1,
        "max_sessions": 2,
        "room": "Lab_02",
    },
    {
        "name": "Geometry",
        "faculty": "Prof. BB",
        "section": "BSCS1A",
        "total_duration": 3,
        "min_sessions": 1,
        "max_sessions": 2,
    },
    {
        "name": "Networking 1",
        "faculty": "Prof. D",
        "section": "BSCS1A",
        "total_duration": 5,
        "min_sessions": 2,
        "max_sessions": 2,
        "room": "Cisco_Lab"
    }
]

rooms = ["Lab_01", "Lab_02", "Cisco_Lab"]
time_slots = [
    "7-8AM", "8-9AM", "9-10AM", "10-11AM", "11-12PM",
    "12-1PM", "1-2PM", "2-3PM", "3-4PM", "4-5PM"
]
days = ["MW", "TTh", "FS"]
sections = ["BSCS1A", "BSCS2B"]

model = cp_model.CpModel()

#CURRENT VARIABLES
subject_day_vars = {}
subject_day_start = {}
subject_day_dur = {}
class_intervals = []

for subject in subjects:
    #ASSIGNS SPECFIC ROOM IF GIVEN
    if "room" in subject and subject["room"]:
        assigned_rooms = [rooms.index(subject["room"])]
    else:
        assigned_rooms = list(range(len(rooms)))  #ALL ROOMS POSSIBKLE

    for day in days:
        is_scheduled = model.NewBoolVar(f"{subject['name']}_{day}_scheduled")
        start = model.NewIntVar(0, len(time_slots) - 1, f"{subject['name']}_{day}_start")
        dur = model.NewIntVar(0, subject["total_duration"], f"{subject['name']}_{day}_dur")

        subject_day_vars[(subject['name'], day)] = is_scheduled
        subject_day_start[(subject['name'], day)] = start
        subject_day_dur[(subject['name'], day)] = dur

        model.Add(dur == 0).OnlyEnforceIf(is_scheduled.Not())
        model.Add(start == 0).OnlyEnforceIf(is_scheduled.Not())

        for room_id in assigned_rooms:
            room = rooms[room_id]
            var = model.NewBoolVar(f"{subject['name']}_{day}_in_{room}")
            end = model.NewIntVar(0, len(time_slots), f"{subject['name']}_{day}_{room}_end")
            model.Add(end == start + dur)

            interval = model.NewOptionalIntervalVar(
                start, dur, end, var, f"{subject['name']}_{day}_{room}_interval"
            )

            model.Add(var == is_scheduled)

            class_intervals.append((interval, subject, day, room_id, subject['faculty'], subject['section']))

#FOR TOTAL DURATION OF THE WEEK
for subject in subjects:
    total_duration = subject["total_duration"]
    min_sessions = subject["min_sessions"]
    max_sessions = subject["max_sessions"]

    dur_sum = sum(subject_day_dur[(subject['name'], d)] for d in days)
    model.Add(dur_sum == total_duration)

    session_count = sum(subject_day_vars[(subject['name'], d)] for d in days)
    model.Add(session_count >= min_sessions)
    model.Add(session_count <= max_sessions)

#FOR NO ROOM OVERLAP
for day in days:
    for room_id in range(len(rooms)):
        intervals = [iv for iv, subj, d, r, f, s in class_intervals if d == day and r == room_id]
        model.AddNoOverlap(intervals)

#SOLVER
solver = cp_model.CpSolver()
status = solver.Solve(model)

#OUTPUT
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print("Schedule:")
    for (interval, subject, day, room_id, _, _) in class_intervals:
        start_time = solver.Value(interval.StartExpr())
        duration = solver.Value(interval.SizeExpr())
        if start_time != -1 and duration != 0:
            end_time = start_time + duration
            print(f"{subject['section']} - {subject['name']} ({subject['faculty']})")
            print(f"  {day} {7 + start_time}:00 to {7 + end_time}:00 in {rooms[room_id]}")

else:
    print("NO SOLUTIONS BEECH")