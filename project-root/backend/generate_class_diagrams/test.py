class Bank:
    def _init_(self, name):
        self.name = name
        self.accounts = {}

    def create_account(self, customer, initial_balance):
        account = Account(customer, initial_balance)
        self.accounts[customer.name] = account
        print(f"Account created for {customer.name} with balance {initial_balance}.")

    def deposit(self, customer, amount):
        account = self.accounts.get(customer.name)
        if account:
            account.balance += amount
            print(f"{customer.name} deposited ${amount}. New balance: ${account.balance}")

    def withdraw(self, customer, amount):
        account = self.accounts.get(customer.name)
        if account and account.balance >= amount:
            account.balance -= amount
            print(f"{customer.name} withdrew ${amount}. New balance: ${account.balance}")
        else:
            print(f"{customer.name} cannot withdraw ${amount}. Insufficient funds.")

class Account:
    def _init_(self, owner, balance):
        self.owner = owner
        self.balance = balance

class Customer:
    def _init_(self, name):
        self.name = name

    def make_deposit(self, bank, amount):
        bank.deposit(self, amount)

    def make_withdrawal(self, bank, amount):
        bank.withdraw(self, amount)

# Usage
bank = Bank("MyBank")
customer1 = Customer("Alice")
customer2 = Customer("Bob")

# Creating accounts
bank.create_account(customer1, 1000)
bank.create_account(customer2, 500)

# Transactions
customer1.make_deposit(bank, 200)
customer2.make_withdrawal(bank, 100)
customer1.make_withdrawal(bank, 1500)  # Insufficient funds
customer2.make_deposit(bank, 300)