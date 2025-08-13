from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from scheduler import load_csv, generate_schedule
import os
import csv
import io

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

@app.get('/')
async def index():
    index_path = os.path.join('static', 'index.html')
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail='Index file not found')
    return FileResponse(index_path, media_type='text/html')

@app.post('/schedule')
async def schedule(payload: dict):
    print('Received request for /schedule')
    subjects = load_csv('cs_curriculum.csv')
    teachers = load_csv('teachers.csv')
    rooms = load_csv('rooms.csv')

    semester_filter = payload.get('semester')

    num_sections_year_1 = payload.get('numSectionsYear1', 0)
    num_sections_year_2 = payload.get('numSectionsYear2', 0)
    num_sections_year_3 = payload.get('numSectionsYear3', 0)
    num_sections_year_4 = payload.get('numSectionsYear4', 0)

    desired_sections_per_year = {
        1: num_sections_year_1,
        2: num_sections_year_2,
        3: num_sections_year_3,
        4: num_sections_year_4,
    }

    print(f"Filtering for semester: {semester_filter}. Desired sections per year: {desired_sections_per_year}")

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
        print('Scheduler: No applicable year levels for the selected semester based on requested sections. Returning empty schedule.')
        return JSONResponse(content=[])

    result = generate_schedule(subjects, teachers, rooms, semester_filter, filtered_desired_sections_per_year)
    return JSONResponse(content=result)

@app.get('/download_schedule')
async def download_schedule(semester: str | None = None):
    fieldnames = ['section_id', 'subject_code', 'type', 'teacher_name', 'room_id', 'day', 'start_time_slot', 'duration_slots']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    csv_bytes = output.getvalue().encode('utf-8')
    headers = {"Content-Disposition": "attachment; filename=schedule.csv"}
    return Response(content=csv_bytes, media_type='text/csv', headers=headers)

@app.get('/data/{filename}')
async def get_data(filename: str):
    filepath = os.path.join('.', f'{filename}.csv')
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail='File not found')
    try:
        data = load_csv(filepath)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/upload/{filename}')
async def upload_file(filename: str, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail='No selected file')
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail='Invalid file type. Only CSV allowed.')
    contents = await file.read()
    filepath = os.path.join('.', f'{filename}.csv')
    with open(filepath, 'wb') as f:
        f.write(contents)
    return { 'message': f'{filename}.csv updated successfully' }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='127.0.0.1', port=5000, reload=True)
