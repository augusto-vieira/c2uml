#ifndef BANK_ACCOUNT_H
#define BANK_ACCOUNT_H

// Structure to represent a bank account
typedef struct {
    int account_number;
    char owner_name[100];
    double balance;
} BankAccount;

// Function prototypes
void deposit(BankAccount *account, double amount);
void withdraw(BankAccount *account, double amount);

#endif // BANK_ACCOUNT_H