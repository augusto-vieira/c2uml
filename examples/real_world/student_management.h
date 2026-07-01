#ifndef STUDENT_MANAGEMENT_H
#define STUDENT_MANAGEMENT_H

#define MAX_STUDENTS 100

// Structure to represent a student
typedef struct {
    int id;
    char name[100];
    float grade;
} Student;

// Function prototypes
void add_student(Student students[], int *count, int id, const char *name, float grade);
void display_students(const Student students[], int count);

#endif // STUDENT_MANAGEMENT_H