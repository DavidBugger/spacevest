1. user selects either airtime or data 
2. the endpoint will be called base on either airtime or data 
3. the response will be displayed on a card well arrange once the user options provides the phone number and purchase will be made and the equivalent amount will be removed from the wallet of the user 
4. then it will be logged in transactions table 
5. 

python manage.py makemigrations users --name add_is_verified_to_bankaccount --empty


ALTER TABLE banking_bank ADD COLUMN currency VARCHAR(3) DEFAULT 'NGN' AFTER country

"ALTER TABLE banking_bank ADD COLUMN type VARCHAR(20) DEFAULT 'nuban' AFTER currency;",
    "SELECT 1"

    "ALTER TABLE banking_bank ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;",
    "SELECT 1"
   