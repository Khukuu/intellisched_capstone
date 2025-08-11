from flask import Flask, request, jsonify, send_from_directory, Response, make_response
from scheduler import load_csv, generate_schedule
import os
import csv
import io

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/schedule', methods=['POST'])
def schedule():
    print('Received request for /schedule')
    subjects = load_csv('cs_curriculum.csv')
    teachers = load_csv('teachers.csv')
    rooms = load_csv('rooms.csv')

    # Get semester from request, default to None if not provided
    semester_filter = request.json.get('semester')
    
    # New: Get desired number of sections per year level
    num_sections_year_1 = request.json.get('numSectionsYear1', 0)
    num_sections_year_2 = request.json.get('numSectionsYear2', 0)
    num_sections_year_3 = request.json.get('numSectionsYear3', 0)
    num_sections_year_4 = request.json.get('numSectionsYear4', 0)

    # Pass a dictionary of desired sections per year to generate_schedule
    desired_sections_per_year = {
        1: num_sections_year_1,
        2: num_sections_year_2,
        3: num_sections_year_3,
        4: num_sections_year_4,
    }

    print(f"Filtering for semester: {semester_filter}. Desired sections per year: {desired_sections_per_year}")

    # Filter desired sections to only years that have subjects for the selected semester
    try:
        if semester_filter:
            available_years = set(
                int(s.get('year_level', 0)) for s in subjects
                if s.get('semester') == semester_filter and s.get('year_level')
            )
        else:
            available_years = set(
                int(s.get('year_level', 0)) for s in subjects if s.get('year_level')
            )
    except Exception:
        available_years = {1, 2, 3, 4}

    filtered_desired_sections_per_year = {
        year: count for year, count in desired_sections_per_year.items()
        if count and (year in available_years)
    }

    if not filtered_desired_sections_per_year:
        print("Scheduler: No applicable year levels for the selected semester based on requested sections. Returning empty schedule.")
        return jsonify([])

    # Call generate_schedule with filtered years
    result = generate_schedule(subjects, teachers, rooms, semester_filter, filtered_desired_sections_per_year)
    return jsonify(result)

@app.route('/download_schedule', methods=['GET'])
def download_schedule():
    subjects = load_csv('cs_curriculum.csv')
    teachers = load_csv('teachers.csv')
    rooms = load_csv('rooms.csv')
    # Removed: sections = load_csv('sections.csv')

    semester_filter = request.args.get('semester')
    
    # For download, we assume all sections that could be generated were generated
    # For now, let's assume a default for all years if not specified for download
    # The actual sections for download will come from the generated schedule, not a CSV
    # This part needs to be re-evaluated once we confirm schedule generation works without sections.csv

    # Placeholder: if you need to download a schedule, it should be the one already generated.
    # If the schedule is dynamically generated without a sections.csv, you might need
    # to store the last generated schedule in a session or similar for download.
    # For now, leaving this simplified as we are focusing on generation.

    # The previous logic in /schedule now directly passes desired_sections_per_year
    # The download endpoint will likely need a different approach if sections are not stored.
    # For now, this part will be simplified and only retrieve the semester.

    # Original data loading (simplified for download for now)
    # This endpoint logic will need to be adjusted significantly once the new section generation is stable
    # schedule = generate_schedule(subjects, teachers, rooms, semester_filter, {}) # Placeholder for now

    # For direct download, we might need a way to fetch the last generated schedule,
    # or re-run a simplified generation based on query parameters.
    # For now, we'll keep it minimal, as the primary goal is generation.

    # Assuming the schedule is already stored or can be re-generated simply for download
    # This will likely require changes to how the generated schedule is stored or retrieved
    # For the sake of removing sections.csv, this will be simplified.

    # Temporary measure: For download, if sections.csv is gone, we cannot load it.
    # The download functionality will need a rework if the sections are generated on the fly.
    # For now, we will simply filter subjects/teachers/rooms data to show it can still load.

    # This entire block needs a rework for the download functionality later.

    # For now, we will just return a dummy CSV if sections.csv is gone.
    # This is to avoid errors while we refactor section generation.
    # In a real scenario, you'd store the generated schedule and serve that.

    # Dummy data for CSV download without sections.csv
    fieldnames = ['section_id', 'subject_code', 'type', 'teacher_name', 'room_id', 'day', 'start_time_slot', 'duration_slots']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    # This would typically be the generated schedule. For now, it's empty.
    # For testing, we can add a dummy row.
    # writer.writerow({
    #     'section_id': 'DUMMY-1A',
    #     'subject_code': 'DUMMY_SUB',
    #     'type': 'lecture',
    #     'teacher_name': 'Dummy Teacher',
    #     'room_id': 'Dummy Room',
    #     'day': 'Mon',
    #     'start_time_slot': '8:00-8:30',
    #     'duration_slots': 2
    # })

    # If no generated schedule is available, return empty
    # This part will need to be properly linked to the actual generated schedule later.
    # For now, we focus on removing sections.csv dependency.

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=schedule.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/data/<filename>', methods=['GET'])
def get_data(filename):
    filepath = os.path.join('.', f'{filename}.csv')
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    try:
        data = load_csv(filepath)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload/<filename>', methods=['POST'])
def upload_file(filename):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.csv'):
        filepath = os.path.join('.', f'{filename}.csv')
        file.save(filepath)
        return jsonify({'message': f'{filename}.csv updated successfully'}), 200
    return jsonify({'error': 'Invalid file type. Only CSV allowed.'}), 400

if __name__ == '__main__':
    app.run(debug=True)
