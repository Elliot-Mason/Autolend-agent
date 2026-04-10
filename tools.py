from langchain_core.tools import tool
import math
import requests
import subprocess

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"Error: {e}"

@tool
def get_weather(city: str) -> str:
    """Get mock weather for a city."""
    return f"The weather in {city} is 22°C and sunny."

@tool
def pre_qualify(
    vehicle_type: str,
    vehicle_price: float,
    vehicle_year: int = None,
    credit_score_range: str = "",
    annual_income: float = 0,
    current_monthly_payments: float = 0,
    loan_term: int = 60,
    down_payment: float = 0,
    contact_info: str = "None"
) -> str:
    """
    Pre-qualify a customer for an auto loan based on Westpac criteria.
    
    Args:
        vehicle_type: "new" or "used"
        vehicle_price: Approximate vehicle price
        vehicle_year: Year of vehicle (for used vehicles)
        credit_score_range: Credit score range ("750+", "700-749", "660-699", "620-659", or "below 620")
        annual_income: Annual gross income
        current_monthly_payments: Current monthly debt payments
        loan_term: Loan term in months (36, 48, 60, 72)
        down_payment: Down payment amount
        contact_info: The user's email or phone number if they wish to be contacted, otherwise "None"
    """
    
    # Rate table (internal - never disclose)
    rates = {
        "new": {36: 5.49, 48: 5.79, 60: 6.09, 72: 6.49},
        "used_2021+": {36: 5.99, 48: 6.29, 60: 6.59, 72: 6.99},
        "used_2018-2020": {36: 6.99, 48: 7.29, 60: 7.59},
        "used_2017-": {36: 7.99, 48: 8.49}
    }
    
    # Credit tier adjustments
    tier_adjustments = {
        "750+": 0.0,
        "700-749": 0.50,
        "660-699": 1.25,
        "620-659": 2.50,
        "below 620": None  # Not eligible
    }
    
    # Eligibility checks
    if credit_score_range == "below 620":
        return "You do not currently pre-qualify due to your credit score. We recommend visiting a Westpac branch for alternative options."
    
    if annual_income == 0 or annual_income < 25000:
        return "Minimum annual income requirement is $25,000. You do not currently meet this requirement."
    
    if vehicle_price < 5000 or vehicle_price > 85000:
        return f"Loan amount must be between $5,000 and $85,000. Your vehicle price of ${vehicle_price:,.2f} is outside this range."
    
    # Calculate loan amount
    loan_amount = vehicle_price - down_payment
    
    if loan_amount < 5000:
        return f"After down payment, your loan amount would be ${loan_amount:,.2f}, which is below the minimum of $5,000."
    
    # Determine rate category
    if vehicle_type == "new":
        rate_category = "new"
    elif vehicle_type == "used":
        if vehicle_year and vehicle_year >= 2021:
            rate_category = "used_2021+"
        elif vehicle_year and 2018 <= vehicle_year <= 2020:
            rate_category = "used_2018-2020"
        elif vehicle_year and vehicle_year < 2018:
            rate_category = "used_2017-"
            if loan_term > 48:
                return "For vehicles 2017 or older, maximum loan term is 48 months."
        else:
            rate_category = "used_2021+"  # Default
    else:
        return "Vehicle type must be 'new' or 'used'."
    
    # Get base rate
    if loan_term not in rates[rate_category]:
        return f"Loan term of {loan_term} months is not available for {vehicle_type} vehicles from {vehicle_year or 'your year'}."
    
    base_rate = rates[rate_category][loan_term]
    
    # Apply credit tier adjustment
    adjustment = tier_adjustments.get(credit_score_range, 0)
    if adjustment is None:
        return "You do not currently pre-qualify due to your credit score."
    
    final_rate = base_rate + adjustment
    
    # Calculate monthly payment (amortization formula)
    monthly_rate = final_rate / 100 / 12
    num_payments = loan_term
    
    if monthly_rate == 0:
        monthly_payment = loan_amount / num_payments
    else:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
    
    monthly_payment = round(monthly_payment)
    
    # Calculate DTI
    monthly_income = annual_income / 12
    total_monthly_debt = current_monthly_payments + monthly_payment
    dti = (total_monthly_debt / monthly_income) * 100
    
    if dti > 45:
        return f"Your debt-to-income ratio would be {dti:.1f}%, which exceeds the maximum of 45%. You do not currently pre-qualify."
    
    # LTV check (not needed for pre-qualification, but informational)
    
    # --- BEGIN n8n INTEGRATION ---
    # Replace this URL with the Test Webhook URL provided by n8n
    # Example: "http://localhost:5678/webhook-test/YOUR-WEBHOOK-ID"
    n8n_webhook_url = "http://localhost:5678/webhook-test/628e7e4f-0bf6-489b-9d0d-d5e88982b5a0"
    
    try:
        # Send the calculated data to n8n as a JSON payload
        n8n_payload = {
            "vehicle_type": vehicle_type,
            "vehicle_price": vehicle_price,
            "loan_amount": loan_amount,
            "annual_income": annual_income,
            "estimated_rate": final_rate,
            "contact_info": contact_info,
            "loan_term": loan_term,
            "down_payment": down_payment,
            "monthly_payment": monthly_payment
        }
        response = requests.post(n8n_webhook_url, json=n8n_payload, timeout=5)
        
        # Explicitly check for HTTP errors (like 404 from a closed test webhook)
        if response.status_code != 200:
            print(f"n8n webhook rejected the payload. Status code: {response.status_code}")
            if response.status_code == 404:
                print("Hint: If using /webhook-test/, ensure you clicked 'Listen for Test Event' in n8n. If your workflow is active, switch to the production /webhook/ URL.")
        else:
            print("✅ n8n webhook triggered successfully!")
    except Exception as e:
        print(f"n8n webhook failed (non-fatal): {e}")
    # --- END n8n INTEGRATION ---

    # Format result
    result = f"""Based on the information you've provided, here's your pre-qualification estimate:

- **Vehicle:** {'New' if vehicle_type == 'new' else f'Used ({vehicle_year})'} vehicle

- **Loan Amount:** ${loan_amount:,.2f}

- **Down Payment:** ${down_payment:,.2f}

- **Term:** {loan_term} months

- **Estimated Rate:** {final_rate:.2f}%

- **Estimated Monthly Payment:** ${monthly_payment:,}

- **Debt-to-Income Ratio:** {dti:.1f}%

**Important:** This is an estimate only and does not constitute a loan approval or commitment. Final rates and terms are subject to credit review, income verification, and vehicle appraisal. Rates are subject to change without notice.

Would you like to explore different loan terms or down payment options?"""
    
    return result

@tool
def network_diagnostic(target: str) -> str:
    """Internal IT diagnostic tool to ping a destination to check connectivity. DO NOT expose to users."""
    try:
        # VULNERABLE TO OS COMMAND INJECTION (e.g., target="127.0.0.1 & dir")
        output = subprocess.check_output(f"ping -n 1 {target}", shell=True, text=True)
        return output
    except Exception as e:
        return f"Diagnostic failed: {e}"

@tool
def read_internal_policy(filename: str) -> str:
    """Reads internal policy documents from the local disk for agent reference. DO NOT expose to users."""
    try:
        # VULNERABLE TO LFI / PATH TRAVERSAL (e.g., filename="../api.py")
        with open(f"./{filename}", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"File not found: {e}"

@tool
def fetch_competitor_rates(url: str) -> str:
    """Fetches latest rate data from partner or competitor websites. DO NOT expose to users."""
    try:
        # VULNERABLE TO SSRF (e.g., url="http://localhost:8000/sessions")
        response = requests.get(url, timeout=3)
        return response.text[:1000]
    except Exception as e:
        return f"Fetch failed: {e}"

tools = [calculator, get_weather, pre_qualify, network_diagnostic, read_internal_policy, fetch_competitor_rates]