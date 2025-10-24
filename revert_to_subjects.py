#!/usr/bin/env python3
"""
Script to revert all course terminology back to subject terminology
"""

import os
import re

def revert_file(file_path, replacements):
    """Revert a file by applying replacements"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {file_path}")
        return True
    else:
        print(f"No changes needed: {file_path}")
        return False

def main():
    """Main revert function"""
    print("Reverting all course terminology back to subject terminology...")
    
    # HTML replacements
    html_replacements = [
        # Navigation and tabs
        ('courses-tab', 'subjects-tab'),
        ('cs-courses-tab', 'cs-subjects-tab'),
        ('it-courses-tab', 'it-subjects-tab'),
        ('cs-courses-pane', 'cs-subjects-pane'),
        ('it-courses-pane', 'it-subjects-pane'),
        ('courseProgramTabs', 'subjectProgramTabs'),
        ('courseProgramTabsContent', 'subjectProgramTabsContent'),
        ('CS Courses', 'CS Subjects'),
        ('IT Courses', 'IT Subjects'),
        ('Course Program Tabs', 'Subject Program Tabs'),
        
        # Form elements
        ('csCoursesSearch', 'csSubjectsSearch'),
        ('itCoursesSearch', 'itSubjectsSearch'),
        ('csCoursesRefresh', 'csSubjectsRefresh'),
        ('itCoursesRefresh', 'itSubjectsRefresh'),
        ('csCoursesAdd', 'csSubjectsAdd'),
        ('itCoursesAdd', 'itSubjectsAdd'),
        ('csCoursesEdit', 'csSubjectsEdit'),
        ('itCoursesEdit', 'itSubjectsEdit'),
        ('csCoursesDelete', 'csSubjectsDelete'),
        ('itCoursesDelete', 'itSubjectsDelete'),
        ('csCoursesData', 'csSubjectsData'),
        ('itCoursesData', 'itSubjectsData'),
        
        # Form IDs
        ('uploadCoursesForm', 'uploadSubjectsForm'),
        ('uploadITCoursesForm', 'uploadITSubjectsForm'),
        
        # Search placeholders
        ('Search CS courses (code, name)…', 'Search CS subjects (code, name)…'),
        ('Search IT courses (code, name)…', 'Search IT subjects (code, name)…'),
        
        # Headers
        ('<h2>Courses</h2>', '<h2>Subjects</h2>'),
        ('<h3>CS Courses</h3>', '<h3>CS Subjects</h3>'),
        ('<h3>IT Courses</h3>', '<h3>IT Subjects</h3>'),
        
        # Summary cards
        ('totalCourses', 'totalSubjects'),
        ('Total Courses', 'Total Subjects'),
    ]
    
    # JavaScript replacements
    js_replacements = [
        # Cache variables
        ('coursesCache', 'subjectsCache'),
        ('csCoursesCache', 'csSubjectsCache'),
        ('itCoursesCache', 'itSubjectsCache'),
        
        # Function names
        ('loadCoursesTable', 'loadSubjectsTable'),
        ('loadCSCoursesTable', 'loadCSSubjectsTable'),
        ('loadITCoursesTable', 'loadITSubjectsTable'),
        
        # Color functions
        ('getCourseColor', 'getSubjectColor'),
        ('COURSE_COLOR_PALETTE', 'SUBJECT_COLOR_PALETTE'),
        ('courseColorCache', 'subjectColorCache'),
        
        # Field names
        ('course_code', 'subject_code'),
        ('course_name', 'subject_name'),
        
        # API endpoints
        ('/api/courses/', '/api/subjects/'),
        ('/api/it-courses/', '/api/it-subjects/'),
        
        # Form handling
        ('uploadCoursesForm', 'uploadSubjectsForm'),
        ('uploadITCoursesForm', 'uploadITSubjectsForm'),
        
        # Table rendering
        ('coursesData', 'subjectsData'),
        ('csCoursesData', 'csSubjectsData'),
        ('itCoursesData', 'itSubjectsData'),
        
        # Messages
        ('No courses exist for the selected semester', 'No subjects exist for the selected semester'),
        ('Course', 'Subject'),
        ('course', 'subject'),
    ]
    
    # Apply HTML replacements
    print("\n=== Reverting HTML files ===")
    revert_file('static/index.html', html_replacements)
    
    # Apply JavaScript replacements
    print("\n=== Reverting JavaScript files ===")
    revert_file('static/script.js', js_replacements)
    
    print("\n=== Revert completed ===")
    print("All course terminology has been reverted to subject terminology.")
    print("Please test the application to ensure everything works correctly.")

if __name__ == "__main__":
    main()
