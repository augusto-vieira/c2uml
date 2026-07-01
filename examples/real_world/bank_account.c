#include <stdio.h>
#include <string.h>
#include "bank_account.h"

// Function to deposit money into the account
void deposit(BankAccount *account, double amount) {
    if (amount > 0) {
        account->balance += amount;
        printf("Deposited %.2f into account %d. New balance: %.2f\n", amount, account->account_number, account->balance);
    } else {
        printf("Invalid deposit amount.\n");
    }
}

// Function to withdraw money from the account
void withdraw(BankAccount *account, double amount) {
    if (amount > 0 && account->balance >= amount) {
        account->balance -= amount;
        printf("Withdrew %.2f from account %d. New balance: %.2f\n", amount, account->account_number, account->balance);
    } else {
        printf("Invalid withdrawal amount or insufficient funds.\n");
    }
}

int main() {
    BankAccount account1 = {12345, "Alice", 1000.0};

    printf("Account %d owned by %s has an initial balance of %.2f\n", account1.account_number, account1.owner_name, account1.balance);

    deposit(&account1, 500.0);
    withdraw(&account1, 200.0);
    withdraw(&account1, 1500.0);

    return 0;
}