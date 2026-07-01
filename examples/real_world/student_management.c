#include <stdio.h>
#include <string.h>
#include "student_management.h"

// Function to add a student
void add_student(Student students[], int *count, int id, const char *name, float grade) {
    if (*count < MAX_STUDENTS) {
        students[*count].id = id;
        strcpy(students[*count].name, name);
        students[*count].grade = grade;
        (*count)++;
        printf("Student %s added successfully.\n", name);
    } else {
        printf("Cannot add more students. Maximum limit reached.\n");
    }
}

// Function to display all students
void display_students(const Student students[], int count) {
    printf("\nList of Students:\n");
    for (int i = 0; i < count; i++) {
        printf("ID: %d, Name: %s, Grade: %.2f\n", students[i].id, students[i].name, students[i].grade);
    }
}

int main() {
    Student students[MAX_STUDENTS];
    int student_count = 0;

    add_student(students, &student_count, 1, "John Doe", 85.5);
    add_student(students, &student_count, 2, "Jane Smith", 92.0);
    add_student(students, &student_count, 3, "Emily Davis", 78.0);

    display_students(students, student_count);

    return 0;
}