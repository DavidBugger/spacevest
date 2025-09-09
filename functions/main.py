# main.py
# Firebase Cloud Functions for the SpaceVest App, written in Python.
# This version is feature-complete and includes robust error handling and increased timeout.

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_functions import https_fn
from firebase_functions.params import SecretParam
import requests
import hmac
import hashlib

# --- CORRECTED INITIALIZATION ---
# Initialize the app with a service account key file.
# Make sure 'serviceAccountKey.json' is in the same 'functions' folder.
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
# --- END OF FIX ---


# --- HELPER FUNCTIONS ---
def add_transaction(user_id, tx_type, status, amount, description):
    """Adds a transaction record to a user's subcollection in Firestore."""
    try:
        tx_ref = db.collection("users").doc(user_id).collection("transactions")
        tx_ref.add(
            {
                "type": tx_type,
                "status": status,
                "amount": amount,
                "description": description,
                "timestamp": firestore.SERVER_TIMESTAMP,
            }
        )
    except Exception as e:
        print(f"Error in add_transaction for user {user_id}: {e}")


# --- CALLABLE FUNCTIONS (Called from the app) ---


@https_fn.on_call(secrets=["PAYSTACK_SECRET"], timeout_sec=120)
def provisionNewUserAccount(req: https_fn.CallableRequest):
    """Creates a dedicated virtual account for a user on-demand."""
    if not req.auth or not req.auth.token.get("email_verified"):
        raise https_fn.HttpsError(
            "unauthenticated", "You must be a verified user to perform this action."
        )

    uid = req.auth.uid
    user_doc_ref = db.collection("users").doc(uid)
    paystack_secret = SecretParam("PAYSTACK_SECRET").value()

    try:
        print("Function triggered for user:", uid)
        user_doc = user_doc_ref.get()
        if not user_doc.exists:
            raise https_fn.HttpsError("not-found", "User data not found in database.")

        user_data = user_doc.to_dict()

        if user_data.get("virtualAccount") and user_data["virtualAccount"].get(
            "accountNumber"
        ):
            return {"status": "exists", "account": user_data["virtualAccount"]}

        full_name = user_data.get("fullname", "Valued User").strip()
        name_parts = full_name.split(" ")
        first_name = name_parts[0] if name_parts and name_parts[0] else "Valued"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "User"

        headers = {"Authorization": f"Bearer {paystack_secret}"}

        customer_payload = {
            "email": user_data.get("email"),
            "first_name": first_name,
            "last_name": last_name,
        }

        print("Creating Paystack customer...")
        customer_response = requests.post(
            "https://api.paystack.co/customer", json=customer_payload, headers=headers
        )
        customer_response.raise_for_status()
        customer_code = customer_response.json()["data"]["customer_code"]
        print("Paystack customer created successfully:", customer_code)

        dva_payload = {"customer": customer_code, "preferred_bank": "wema-bank"}
        print("Creating dedicated virtual account...")
        dva_response = requests.post(
            "https://api.paystack.co/dedicated_account",
            json=dva_payload,
            headers=headers,
        )
        dva_response.raise_for_status()
        virtual_account_data = dva_response.json()["data"]
        print("Dedicated virtual account created successfully.")

        new_virtual_account = {
            "bankName": virtual_account_data["bank"]["name"],
            "accountNumber": virtual_account_data["account_number"],
            "accountName": virtual_account_data["account_name"],
        }

        print("Updating user document in Firestore...")
        user_doc_ref.update(
            {
                "paystackCustomerCode": customer_code,
                "virtualAccount": new_virtual_account,
            }
        )
        print("User document updated successfully.")

        return {"status": "created", "account": new_virtual_account}

    except requests.exceptions.RequestException as e:
        if e.response is not None:
            print(
                f"Paystack API Error during virtual account creation: {e.response.text}"
            )
        raise https_fn.HttpsError(
            "internal",
            "Could not create virtual account due to a payment provider error.",
        )
    except Exception as e:
        print(f"Unexpected error in provisionNewUserAccount: {e}")
        raise https_fn.HttpsError("internal", "An unexpected error occurred.")


@https_fn.on_call(secrets=["PAYSTACK_SECRET"])
def resolveAccountNumber(req: https_fn.CallableRequest):
    """Verifies a bank account number via Paystack."""
    if not req.auth:
        raise https_fn.HttpsError("unauthenticated", "You must be logged in.")

    account_number = req.data.get("accountNumber")
    bank_code = req.data.get("bankCode")
    if not account_number or not bank_code:
        raise https_fn.HttpsError(
            "invalid-argument", "Account number and bank code are required."
        )

    paystack_secret = SecretParam("PAYSTACK_SECRET").value()
    headers = {"Authorization": f"Bearer {paystack_secret}"}
    url = f"https://api.paystack.co/bank/resolve?account_number={account_number}&bank_code={bank_code}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise https_fn.HttpsError(
            "internal", e.response.json().get("message", "Could not resolve account.")
        )


@https_fn.on_call(secrets=["PAYSTACK_SECRET"], timeout_sec=120)
def initiateWithdrawal(req: https_fn.CallableRequest):
    """Creates a transfer recipient and initiates a withdrawal to a user's bank account."""
    if not req.auth:
        raise https_fn.HttpsError(
            "unauthenticated", "You must be logged in to withdraw funds."
        )

    uid = req.auth.uid
    user_doc_ref = db.collection("users").doc(uid)

    recipient_data = req.data.get("recipient")
    amount_naira = req.data.get("amount")

    if not all([recipient_data, amount_naira]):
        raise https_fn.HttpsError(
            "invalid-argument", "Recipient data and amount are required."
        )

    account_number = recipient_data.get("account_number")
    bank_code = recipient_data.get("bank_code")
    account_name = recipient_data.get("account_name")

    try:
        amount_naira = float(amount_naira)
        if amount_naira <= 0:
            raise https_fn.HttpsError(
                "invalid-argument", "Amount must be a positive number."
            )
    except (ValueError, TypeError):
        raise https_fn.HttpsError("invalid-argument", "Invalid amount specified.")

    paystack_secret = SecretParam("PAYSTACK_SECRET").value()
    headers = {"Authorization": f"Bearer {paystack_secret}"}

    try:
        user_doc = user_doc_ref.get()
        if not user_doc.exists:
            raise https_fn.HttpsError("not-found", "User data not found.")

        user_data = user_doc.to_dict()
        current_balance = user_data.get("walletBalance", 0)

        if current_balance < amount_naira:
            raise https_fn.HttpsError(
                "failed-precondition", "Insufficient wallet balance."
            )

        recipient_payload = {
            "type": "nuban",
            "name": account_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN",
        }
        recipient_res = requests.post(
            "https://api.paystack.co/transferrecipient",
            json=recipient_payload,
            headers=headers,
        )
        recipient_res.raise_for_status()
        recipient_code = recipient_res.json()["data"]["recipient_code"]

        amount_kobo = int(amount_naira * 100)
        transfer_payload = {
            "source": "balance",
            "amount": amount_kobo,
            "recipient": recipient_code,
            "reason": f"SpaceVest Wallet Withdrawal for {user_data.get('email')}",
        }
        transfer_res = requests.post(
            "https://api.paystack.co/transfer", json=transfer_payload, headers=headers
        )
        transfer_res.raise_for_status()

        @firestore.transactional
        def debit_wallet(transaction):
            user_snapshot = transaction.get(user_doc_ref)
            new_balance = user_snapshot.to_dict().get("walletBalance", 0) - amount_naira
            if new_balance < 0:
                raise https_fn.HttpsError(
                    "failed-precondition",
                    "Transaction failed due to insufficient funds.",
                )

            transaction.update(user_doc_ref, {"walletBalance": new_balance})

            tx_ref = user_doc_ref.collection("transactions").document()
            transaction.set(
                tx_ref,
                {
                    "type": "debit",
                    "status": "pending",
                    "amount": amount_naira,
                    "description": f"Withdrawal to account {account_number}",
                    "timestamp": firestore.SERVER_TIMESTAMP,
                },
            )

        transaction = db.transaction()
        debit_wallet(transaction)

        return {"status": "success", "message": "Withdrawal initiated successfully."}

    except requests.exceptions.RequestException as e:
        error_message = e.response.json().get(
            "message", "A payment provider error occurred."
        )
        raise https_fn.HttpsError("internal", error_message)
    except Exception as e:
        raise https_fn.HttpsError("internal", f"An unexpected error occurred: {e}")


@https_fn.on_call(secrets=["PAYSTACK_SECRET"])
def verifyBvn(req: https_fn.CallableRequest):
    """Verifies a user's BVN via Paystack."""
    if not req.auth:
        raise https_fn.HttpsError("unauthenticated", "You must be logged in.")

    bvn = req.data.get("bvn")
    if not bvn or not len(bvn) == 11:
        raise https_fn.HttpsError(
            "invalid-argument", "A valid 11-digit BVN is required."
        )

    paystack_secret = SecretParam("PAYSTACK_SECRET").value()
    headers = {"Authorization": f"Bearer {paystack_secret}"}
    url = f"https://api.paystack.co/bvn/match"

    uid = req.auth.uid
    user_doc = db.collection("users").doc(uid).get()
    if not user_doc.exists or not user_doc.to_dict().get("bankDetails"):
        raise https_fn.HttpsError(
            "failed-precondition", "Please add a bank account before verifying BVN."
        )

    bank_details = user_doc.to_dict()["bankDetails"]

    payload = {
        "bvn": bvn,
        "account_number": bank_details["accountNumber"],
        "bank_code": bank_details["bankCode"],
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise https_fn.HttpsError(
            "internal", e.response.json().get("message", "Could not verify BVN.")
        )


@https_fn.on_call()
def updateRate(req: https_fn.CallableRequest):
    """Allows an admin to update the crypto selling rates."""
    if not req.auth:
        raise https_fn.HttpsError("unauthenticated", "You must be logged in.")

    uid = req.auth.uid
    user_doc = db.collection("users").doc(uid).get()
    if not user_doc.exists or user_doc.to_dict().get("role") != "admin":
        raise https_fn.HttpsError(
            "permission-denied", "You do not have permission to perform this action."
        )

    crypto_id = req.data.get("cryptoId")
    naira_rate = req.data.get("nairaRate")

    if not crypto_id or naira_rate is None:
        raise https_fn.HttpsError(
            "invalid-argument", "Crypto ID and Naira rate are required."
        )

    try:
        rate_ref = db.collection("rates").doc(crypto_id)
        rate_ref.update({"nairaRate": float(naira_rate)})
        return {
            "status": "success",
            "message": f"Rate for {crypto_id} updated successfully.",
        }
    except Exception as e:
        raise https_fn.HttpsError(
            "internal", f"An error occurred while updating the rate: {e}"
        )


# --- HTTP-TRIGGERED FUNCTIONS ---


@https_fn.on_request(secrets=["PAYSTACK_SECRET"])
def paystackWebhookHandler(req: https_fn.Request) -> https_fn.Response:
    """Handles webhook events from Paystack for deposits."""
    paystack_secret = SecretParam("PAYSTACK_SECRET").value()

    signature = req.headers.get("x-paystack-signature")
    body = req.raw_body
    hash_val = hmac.new(
        paystack_secret.encode("utf-8"), body, hashlib.sha512
    ).hexdigest()
    if hash_val != signature:
        print("Webhook Error: Invalid signature.")
        return https_fn.Response("Invalid signature", status=401)

    event = req.get_json()

    if event.get("event") == "charge.success":
        data = event.get("data")
        amount_in_kobo = data.get("amount")
        customer_email = data.get("customer", {}).get("email")
        reference = data.get("reference")

        if not all([amount_in_kobo, customer_email, reference]):
            return https_fn.Response("Missing data", status=400)

        amount_in_naira = amount_in_kobo / 100
        tx_ref = db.collection("processed_transactions").doc(reference)

        try:
            user_query = (
                db.collection("users")
                .where("email", "==", customer_email)
                .limit(1)
                .get()
            )
            if not user_query:
                raise Exception(f"No user found with email: {customer_email}")

            user_doc_snapshot = user_query[0]
            user_id = user_doc_snapshot.id
            user_doc_ref = db.collection("users").doc(user_id)

            @firestore.transactional
            def credit_wallet(transaction):
                tx_doc = transaction.get(tx_ref)
                if tx_doc.exists:
                    print(f"Transaction {reference} already processed.")
                    return

                transaction.update(
                    user_doc_ref,
                    {"walletBalance": firestore.Increment(amount_in_naira)},
                )
                transaction.set(
                    tx_ref,
                    {
                        "status": "processed",
                        "userId": user_id,
                        "amount": amount_in_naira,
                    },
                )

            transaction = db.transaction()
            credit_wallet(transaction)

            add_transaction(
                user_id,
                "credit",
                "completed",
                amount_in_naira,
                f"Wallet deposit via bank transfer. Ref: {reference}",
            )

            return https_fn.Response("Webhook processed successfully.", status=200)

        except Exception as e:
            print(f"Error processing webhook: {e}")
            return https_fn.Response(f"Internal server error: {e}", status=500)

    return https_fn.Response("Event received.", status=200)
