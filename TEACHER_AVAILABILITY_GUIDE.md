# Teacher Availability Days Feature - User Guide

## Overview
The Teacher Availability Days feature allows you to specify which days of the week each teacher is available to teach. This ensures that the scheduler only assigns teachers to classes on days when they're actually available.

## How to Use

### 1. Viewing Teacher Availability
- Navigate to the **Teachers** tab in the web interface
- You'll see a new column called **availability_days** showing each teacher's available days
- Days are displayed as comma-separated values (e.g., "Mon, Wed, Fri")

### 2. Adding a New Teacher with Availability
1. Click the **Add** button in the Teachers section
2. Enter the teacher's name and subjects they can teach
3. When prompted for "Available Days", enter the days they're available
   - Format: `Mon,Tue,Wed,Thu,Fri,Sat` (comma-separated)
   - Example: `Mon,Wed,Fri` (only Monday, Wednesday, Friday)
   - Example: `Tue,Thu,Sat` (only Tuesday, Thursday, Saturday)
4. Click OK to save

### 3. Editing Teacher Availability
1. Select one or more teachers from the table
2. Click the **Edit** button
3. In the bulk edit modal, check the "Available Days" field
4. Enter the new availability days (comma-separated)
5. Click **Save** to apply changes

### 4. Examples of Availability Days
- **Full-time teacher**: `Mon,Tue,Wed,Thu,Fri,Sat`
- **Part-time (MWF)**: `Mon,Wed,Fri`
- **Part-time (TThS)**: `Tue,Thu,Sat`
- **Weekdays only**: `Mon,Tue,Wed,Thu,Fri`
- **Weekends only**: `Sat`

## How It Works in Scheduling

When generating schedules:
1. The scheduler checks each teacher's availability days
2. Teachers are only assigned to classes on days they're available
3. If a teacher is only available Mon/Wed/Fri, they won't be scheduled on Tue/Thu/Sat
4. This prevents scheduling conflicts and respects teacher preferences

## Benefits

- **Flexible Scheduling**: Accommodate part-time teachers and varying availability
- **Conflict Prevention**: Avoid scheduling teachers on unavailable days
- **Better Resource Management**: Optimize teacher assignments based on availability
- **Realistic Constraints**: Reflect real-world teacher availability patterns

## Technical Notes

- Availability days are stored as arrays in the database
- The frontend displays them as comma-separated strings for easy reading
- The scheduler uses constraint programming to enforce availability rules
- Default availability is all days (Mon-Sat) for backward compatibility

## Troubleshooting

- **No availability shown**: Teachers default to all days available
- **Scheduling issues**: Check if teacher availability conflicts with class requirements
- **Display issues**: Refresh the page to see updated availability days
