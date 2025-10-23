"""
Analytics module for schedule analysis
Provides room utilization, faculty contact hours, and occupancy rate analytics
"""

from collections import defaultdict, Counter
from datetime import datetime
import json

def calculate_room_utilization(schedule_data, rooms_data):
    """
    Calculate room utilization analytics
    Returns: dict with room utilization statistics
    """
    if not schedule_data:
        return {}
    
    # Initialize room usage tracking
    room_usage = defaultdict(lambda: {
        'total_slots_used': 0,
        'total_slots_available': 0,
        'usage_by_day': defaultdict(int),
        'usage_by_time': defaultdict(int),
        'events_count': 0,
        'unique_teachers': set(),
        'unique_subjects': set()
    })
    
    # Calculate total available slots (6 days * 22 time slots per day)
    total_slots_per_day = 22  # 7 AM to 6 PM in 30-min slots
    total_days = 6  # Mon-Sat
    
    # Track time slot usage
    time_slots = []
    for h in range(7, 18):  # 7 AM to 6 PM
        time_slots.append(f"{h:02d}:00-{h:02d}:30")
        time_slots.append(f"{h:02d}:30-{h+1:02d}:00")
    
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    # Process each schedule event
    for event in schedule_data:
        room_id = event.get('room_id', '')
        if not room_id:
            continue
            
        # Get room info
        room_info = next((r for r in rooms_data if r.get('room_id') == room_id), {})
        room_name = room_info.get('room_name', room_id)
        
        # Calculate duration in slots
        duration_slots = int(event.get('duration_slots', 1))
        day = event.get('day', '')
        start_time = event.get('start_time_slot', '')
        
        # Update room usage
        room_usage[room_id]['total_slots_used'] += duration_slots
        room_usage[room_id]['usage_by_day'][day] += duration_slots
        room_usage[room_id]['usage_by_time'][start_time] += duration_slots
        room_usage[room_id]['events_count'] += 1
        room_usage[room_id]['unique_teachers'].add(event.get('teacher_name', ''))
        room_usage[room_id]['unique_subjects'].add(event.get('subject_code', ''))
    
    # Calculate utilization percentages
    analytics = {
        'room_utilization': {},
        'summary': {
            'total_rooms': len(rooms_data),
            'rooms_used': len([r for r in room_usage.values() if r['total_slots_used'] > 0]),
            'total_events': len(schedule_data),
            'total_slots_used': sum(r['total_slots_used'] for r in room_usage.values())
        }
    }
    
    for room_id, usage in room_usage.items():
        room_info = next((r for r in rooms_data if r.get('room_id') == room_id), {})
        room_name = room_info.get('room_name', room_id)
        
        # Calculate total available slots for this room
        total_available = total_slots_per_day * total_days
        utilization_percentage = (usage['total_slots_used'] / total_available * 100) if total_available > 0 else 0
        
        analytics['room_utilization'][room_id] = {
            'room_name': room_name,
            'room_id': room_id,
            'total_slots_used': usage['total_slots_used'],
            'total_slots_available': total_available,
            'utilization_percentage': round(utilization_percentage, 2),
            'events_count': usage['events_count'],
            'unique_teachers': len(usage['unique_teachers']),
            'unique_subjects': len(usage['unique_subjects']),
            'usage_by_day': dict(usage['usage_by_day']),
            'most_used_day': max(usage['usage_by_day'].items(), key=lambda x: x[1])[0] if usage['usage_by_day'] else None,
            'is_laboratory': room_info.get('is_laboratory', False)
        }
    
    return analytics

def calculate_faculty_contact_hours(schedule_data, teachers_data):
    """
    Calculate faculty contact hours analytics
    Returns: dict with faculty workload statistics
    """
    if not schedule_data:
        return {}
    
    # Initialize teacher tracking
    teacher_workload = defaultdict(lambda: {
        'total_hours': 0,
        'total_slots': 0,
        'subjects_taught': set(),
        'sections_taught': set(),
        'rooms_used': set(),
        'hours_by_day': defaultdict(float),
        'hours_by_subject': defaultdict(float),
        'events_count': 0
    })
    
    # Process each schedule event
    for event in schedule_data:
        teacher_name = event.get('teacher_name', '')
        if not teacher_name:
            continue
            
        # Calculate hours (each slot is 30 minutes = 0.5 hours)
        duration_slots = int(event.get('duration_slots', 1))
        duration_hours = duration_slots * 0.5
        
        # Update teacher workload
        teacher_workload[teacher_name]['total_hours'] += duration_hours
        teacher_workload[teacher_name]['total_slots'] += duration_slots
        teacher_workload[teacher_name]['subjects_taught'].add(event.get('subject_code', ''))
        teacher_workload[teacher_name]['sections_taught'].add(event.get('section_id', ''))
        teacher_workload[teacher_name]['rooms_used'].add(event.get('room_id', ''))
        teacher_workload[teacher_name]['hours_by_day'][event.get('day', '')] += duration_hours
        teacher_workload[teacher_name]['hours_by_subject'][event.get('subject_code', '')] += duration_hours
        teacher_workload[teacher_name]['events_count'] += 1
    
    # Calculate analytics
    analytics = {
        'faculty_workload': {},
        'summary': {
            'total_teachers': len(teachers_data),
            'teachers_used': len([t for t in teacher_workload.values() if t['total_hours'] > 0]),
            'total_contact_hours': sum(t['total_hours'] for t in teacher_workload.values()),
            'average_hours_per_teacher': 0
        }
    }
    
    # Calculate average hours per teacher
    if analytics['summary']['teachers_used'] > 0:
        analytics['summary']['average_hours_per_teacher'] = round(
            analytics['summary']['total_contact_hours'] / analytics['summary']['teachers_used'], 2
        )
    
    for teacher_name, workload in teacher_workload.items():
        # Find teacher info
        teacher_info = next((t for t in teachers_data if t.get('teacher_name') == teacher_name), {})
        
        analytics['faculty_workload'][teacher_name] = {
            'teacher_name': teacher_name,
            'teacher_id': teacher_info.get('teacher_id', ''),
            'total_hours': round(workload['total_hours'], 2),
            'total_slots': workload['total_slots'],
            'subjects_count': len(workload['subjects_taught']),
            'sections_count': len(workload['sections_taught']),
            'rooms_count': len(workload['rooms_used']),
            'events_count': workload['events_count'],
            'subjects_taught': list(workload['subjects_taught']),
            'sections_taught': list(workload['sections_taught']),
            'rooms_used': list(workload['rooms_used']),
            'hours_by_day': dict(workload['hours_by_day']),
            'hours_by_subject': dict(workload['hours_by_subject']),
            'most_used_day': max(workload['hours_by_day'].items(), key=lambda x: x[1])[0] if workload['hours_by_day'] else None,
            'workload_level': get_workload_level(workload['total_hours'])
        }
    
    return analytics

def calculate_occupancy_rates(schedule_data):
    """
    Calculate occupancy rates per week
    Returns: dict with weekly occupancy statistics
    """
    if not schedule_data:
        return {}
    
    # Initialize time slot tracking
    time_slots = []
    for h in range(7, 18):  # 7 AM to 6 PM
        time_slots.append(f"{h:02d}:00-{h:02d}:30")
        time_slots.append(f"{h:02d}:30-{h+1:02d}:00")
    
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    # Track occupancy by time slot and day
    occupancy_grid = {}
    for day in day_labels:
        occupancy_grid[day] = {}
        for time_slot in time_slots:
            occupancy_grid[day][time_slot] = 0
    
    # Process each schedule event
    for event in schedule_data:
        day = event.get('day', '')
        start_time = event.get('start_time_slot', '')
        duration_slots = int(event.get('duration_slots', 1))
        
        if day not in day_labels or start_time not in time_slots:
            continue
        
        # Find start time index
        start_idx = time_slots.index(start_time)
        
        # Mark all occupied time slots
        for i in range(duration_slots):
            if start_idx + i < len(time_slots):
                current_time_slot = time_slots[start_idx + i]
                occupancy_grid[day][current_time_slot] += 1
    
    # Calculate analytics
    analytics = {
        'weekly_occupancy': {},
        'summary': {
            'total_time_slots': len(time_slots) * len(day_labels),
            'peak_occupancy_slot': None,
            'peak_occupancy_count': 0,
            'average_occupancy_per_slot': 0
        }
    }
    
    # Calculate statistics
    all_occupancy_values = []
    for day in day_labels:
        for time_slot in time_slots:
            occupancy_count = occupancy_grid[day][time_slot]
            all_occupancy_values.append(occupancy_count)
            
            # Track peak occupancy
            if occupancy_count > analytics['summary']['peak_occupancy_count']:
                analytics['summary']['peak_occupancy_count'] = occupancy_count
                analytics['summary']['peak_occupancy_slot'] = f"{day} {time_slot}"
    
    # Calculate average occupancy
    if all_occupancy_values:
        analytics['summary']['average_occupancy_per_slot'] = round(
            sum(all_occupancy_values) / len(all_occupancy_values), 2
        )
    
    # Calculate daily occupancy rates
    for day in day_labels:
        day_occupancy = [occupancy_grid[day][slot] for slot in time_slots]
        occupied_slots = sum(1 for count in day_occupancy if count > 0)
        total_slots = len(time_slots)
        
        analytics['weekly_occupancy'][day] = {
            'day': day,
            'occupied_slots': occupied_slots,
            'total_slots': total_slots,
            'occupancy_rate': round((occupied_slots / total_slots) * 100, 2) if total_slots > 0 else 0,
            'peak_occupancy': max(day_occupancy) if day_occupancy else 0,
            'average_occupancy': round(sum(day_occupancy) / len(day_occupancy), 2) if day_occupancy else 0
        }
    
    return analytics

def get_workload_level(total_hours):
    """
    Determine workload level based on total hours
    """
    if total_hours <= 10:
        return "Light"
    elif total_hours <= 20:
        return "Moderate"
    elif total_hours <= 30:
        return "Heavy"
    else:
        return "Very Heavy"

def generate_schedule_analytics(schedule_data, rooms_data, teachers_data):
    """
    Generate comprehensive analytics for a schedule
    Returns: dict with all analytics data
    """
    if not schedule_data:
        return {
            'room_utilization': {},
            'faculty_workload': {},
            'weekly_occupancy': {},
            'summary': {
                'total_events': 0,
                'total_rooms': len(rooms_data),
                'total_teachers': len(teachers_data),
                'generated_at': datetime.now().isoformat()
            }
        }
    
    # Calculate all analytics
    room_analytics = calculate_room_utilization(schedule_data, rooms_data)
    faculty_analytics = calculate_faculty_contact_hours(schedule_data, teachers_data)
    occupancy_analytics = calculate_occupancy_rates(schedule_data)
    
    # Combine all analytics
    analytics = {
        'room_utilization': room_analytics.get('room_utilization', {}),
        'faculty_workload': faculty_analytics.get('faculty_workload', {}),
        'weekly_occupancy': occupancy_analytics.get('weekly_occupancy', {}),
        'summary': {
            'total_events': len(schedule_data),
            'total_rooms': room_analytics.get('summary', {}).get('total_rooms', 0),
            'rooms_used': room_analytics.get('summary', {}).get('rooms_used', 0),
            'total_teachers': faculty_analytics.get('summary', {}).get('total_teachers', 0),
            'teachers_used': faculty_analytics.get('summary', {}).get('teachers_used', 0),
            'total_contact_hours': faculty_analytics.get('summary', {}).get('total_contact_hours', 0),
            'average_hours_per_teacher': faculty_analytics.get('summary', {}).get('average_hours_per_teacher', 0),
            'peak_occupancy_slot': occupancy_analytics.get('summary', {}).get('peak_occupancy_slot', ''),
            'peak_occupancy_count': occupancy_analytics.get('summary', {}).get('peak_occupancy_count', 0),
            'average_occupancy_per_slot': occupancy_analytics.get('summary', {}).get('average_occupancy_per_slot', 0),
            'generated_at': datetime.now().isoformat()
        }
    }
    
    return analytics
