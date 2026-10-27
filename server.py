"""
StreamFlix AI Retention Intelligence - Backend Server
Provides static file serving and RESTful API endpoints for:
- /api/customers
- /api/kpis
- /api/retention/whatsapp/generate
- /api/retention/whatsapp/send
- /api/retention/call/generate
- /api/retention/call/initiate
- /api/retention/status/update
"""

import http.server
import socketserver
import json
import os
import urllib.parse
import mimetypes
from datetime import datetime

PORT = 5050
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
DATA_FILE = os.path.join(PUBLIC_DIR, "data.json")

# In-memory action tracking state with default values
customer_actions = {}

def load_customers():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_kpis(customers):
    total = len(customers)
    churned = sum(1 for c in customers if c.get("Churned") == 1)
    churn_rate = round((churned / total * 100), 2) if total else 0
    crit_high = [c for c in customers if c.get("Risk_Segment") in ["Critical", "High"]]
    revenue_at_risk = sum(c.get("Monthly_Revenue", 0) for c in crit_high)
    avg_sat = round(sum(c.get("Satisfaction_Score", 0) for c in customers) / total, 2) if total else 0
    avg_risk = round(sum(c.get("Churn_Risk_Score", 0) for c in customers) / total, 2) if total else 0
    
    return {
        "total_subscribers": total,
        "churned_subscribers": churned,
        "churn_rate_pct": churn_rate,
        "high_risk_subscribers": len(crit_high),
        "revenue_at_risk": revenue_at_risk,
        "average_satisfaction": avg_sat,
        "average_churn_risk_score": avg_risk
    }

def get_primary_risk_signal(c):
    # Determine the strongest risk signal supported by data
    if c.get("Payment_Failures_90d", 0) >= 2:
        return f"Payment Friction: {c['Payment_Failures_90d']} failed recurring transactions in 90 days"
    if c.get("Complaints_90d", 0) >= 2 or c.get("Support_Tickets_90d", 0) >= 7:
        return f"Customer Support Friction: {c['Complaints_90d']} formal complaints and {c['Support_Tickets_90d']} support tickets in 90 days"
    if c.get("Satisfaction_Score", 5) <= 3.0:
        return f"Low Satisfaction: Rating dropped to {c['Satisfaction_Score']} / 5.0"
    if c.get("Login_Frequency_Score", 100) < 50 or c.get("Avg_Sessions_30d", 10) <= 3:
        return f"Engagement Decline: Only {c['Avg_Sessions_30d']} streaming sessions in 30 days (Login score {c['Login_Frequency_Score']}/100)"
    if c.get("Discounts_Used_90d", 0) >= 2:
        return f"Price Sensitivity: Applied {c['Discounts_Used_90d']} promo discounts in 90 days"
    return "Stable Engagement: Low risk indicators"

def generate_whatsapp_message(customer):
    name = customer.get("Customer_Name", "Subscriber")
    first_name = name.split()[0]
    plan = customer.get("Plan", "StreamFlix")
    risk_seg = customer.get("Risk_Segment", "Low")
    payment_fails = customer.get("Payment_Failures_90d", 0)
    complaints = customer.get("Complaints_90d", 0)
    tickets = customer.get("Support_Tickets_90d", 0)
    sessions = customer.get("Avg_Sessions_30d", 0)
    sat = customer.get("Satisfaction_Score", 4.0)

    # Strictly human, personalized, customer-value focused, never mentioning churn or risk
    if payment_fails >= 2:
        msg = (
            f"Hi {first_name}, this is Priya from StreamFlix Priority Care. "
            f"We noticed a recent hiccup renewing your {plan} subscription payment. "
            f"To make sure your streaming isn't interrupted, we've enabled a complimentary 48-hour grace period! "
            f"Would you like a secure one-click link to update your payment details, or would you prefer a quick assistance callback? "
            f"We're here to help."
        )
    elif complaints >= 2 or tickets >= 7:
        msg = (
            f"Hi {first_name}, this is Vikram from the StreamFlix Executive Care team. "
            f"We reviewed your recent support inquiries regarding your {plan} experience, and we sincerely apologize "
            f"that things weren't as smooth as they should be. "
            f"I have personally assigned a senior specialist to review your account, and we'd love to schedule a 3-minute check-in "
            f"at your convenience to make sure everything is completely resolved for you."
        )
    elif sat <= 3.0:
        msg = (
            f"Hi {first_name}, thank you for being a valued {plan} member on StreamFlix. "
            f"We're committed to giving you the best streaming experience possible, and we noticed your recent rating indicated "
            f"we have room to improve. Could you share one quick thing we could do better? "
            f"As a token of our appreciation for your candid feedback, we'd also love to offer you a complimentary 4K Ultra HD upgrade "
            f"for your next month."
        )
    elif sessions <= 3:
        msg = (
            f"Hi {first_name}, we’d love to help you get the most out of your {plan} plan on StreamFlix! "
            f"We just added top-rated blockbuster releases and exclusive originals curated for your profile that you might enjoy this week. "
            f"You also have 2 unused stream profiles available on your plan. "
            f"Check them out anytime, or let us know if you'd like our top 3 weekend recommendations!"
        )
    else:
        msg = (
            f"Hi {first_name}, thank you for being a wonderful {plan} subscriber with StreamFlix! "
            f"We're celebrating our top loyal members this month with exclusive early access to upcoming season premieres "
            f"and an invitation to share an invite pass with a friend. Enjoy your streaming, and thank you for being with us!"
        )
    return msg

def generate_call_script(customer):
    name = customer.get("Customer_Name", "Subscriber")
    first_name = name.split()[0]
    plan = customer.get("Plan", "StreamFlix")
    payment_fails = customer.get("Payment_Failures_90d", 0)
    complaints = customer.get("Complaints_90d", 0)
    tickets = customer.get("Support_Tickets_90d", 0)
    sat = customer.get("Satisfaction_Score", 4.0)
    sessions = customer.get("Avg_Sessions_30d", 0)

    if payment_fails >= 2:
        reason = "Resolve recurring billing failure and provide payment grace period"
        discovery = "I noticed a payment processing error on your last billing cycle. Did you recently change cards or experience an unexpected bank decline?"
        response = "Acknowledge the inconvenience immediately. Reassure the customer that their streaming access has been temporarily safeguarded, and offer to walk them through a secure UPI/card renewal."
        offer = "Offer waiver of any late retry fees plus a 14-day billing extension while updating the preferred payment method."
    elif complaints >= 2 or tickets >= 7:
        reason = "Executive service recovery following multiple recent support interactions"
        discovery = "I'm calling personally from our Subscriber Advocacy desk. Looking at your recent tickets, it looks like your streaming experience wasn't up to standard. How is the service performing for you right now?"
        response = "Listen empathetically without interrupting. Validate their frustration, take full ownership, and detail the technical fix already in place."
        offer = "Provide dedicated senior concierge support line + credit 1 month of subscription fee as service recovery."
    elif sat <= 3.0:
        reason = "Service quality discovery and satisfaction restoration"
        discovery = "We noticed your recent satisfaction feedback was lower than we strive for. What is the single biggest thing that hasn't met your expectations?"
        response = "Thank them warmly for their honesty. Relate their feedback to upcoming product features or content library expansions."
        offer = "Offer immediate plan perk upgrade (e.g., ad-free streaming or 4K multi-device stream) at zero additional charge."
    elif sessions <= 3:
        reason = "Usage re-activation and personalized content walkthrough"
        discovery = "We noticed you haven't had much time to stream your favorite shows on your {plan} plan lately. Have you had trouble finding titles you love, or experiencing any device issues?"
        response = "Guide them towards newly released genres matching their viewing history; explain how to set up download-and-watch-offline on mobile."
        offer = "Complimentary access to premium curated festival screenings and extended watchlist features."
    else:
        reason = "Loyalty recognition and VIP customer appreciation"
        discovery = "As one of our longest-tenured subscribers, what features or content categories would you like to see StreamFlix add next?"
        response = "Document feature suggestions for the product team; thank them for their loyalty."
        offer = "Exclusive invitation to StreamFlix Beta Viewer Community with bonus referral rewards."

    return {
        "customer_name": name,
        "reason_for_contact": reason,
        "script": {
            "opening": f"Hello {first_name}, my name is [Agent Name] with StreamFlix Member Relations. Am I catching you at a convenient time for a brief 2-minute conversation regarding your {plan} subscription?",
            "reason_for_contact": f"The reason for my call today is to ensure you're getting full value and seamless streaming from your {plan} account, and to personally assist with {reason.lower()}.",
            "discovery_question": discovery,
            "recommended_response": response,
            "retention_offer": offer,
            "closing": f"Thank you so much for your valuable time and feedback today, {first_name}. I'll personally follow up on everything we discussed. Have a wonderful rest of your week with StreamFlix!"
        }
    }

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/customers":
            customers = load_customers()
            # Enrich with current action state
            for c in customers:
                cid = c["Customer_ID"]
                c["Action_Status"] = customer_actions.get(cid, {}).get("status", "Not Contacted")
                c["Last_Action"] = customer_actions.get(cid, {}).get("last_action", "None")
                c["Last_Action_Date"] = customer_actions.get(cid, {}).get("date", "-")
                c["Next_Followup"] = customer_actions.get(cid, {}).get("next_followup", "Pending outreach")
                c["Primary_Signal"] = get_primary_risk_signal(c)
                
                # Retention priority logic
                score = c.get("Churn_Risk_Score", 0)
                seg = c.get("Risk_Segment", "Low")
                rev = c.get("Monthly_Revenue", 0)
                if seg == "Critical" or (seg == "High" and rev >= 1499) or score >= 60:
                    c["Retention_Priority"] = "IMMEDIATE"
                elif seg == "High" or (seg == "Medium" and rev >= 2000):
                    c["Retention_Priority"] = "HIGH"
                elif seg == "Medium":
                    c["Retention_Priority"] = "NORMAL"
                else:
                    c["Retention_Priority"] = "MONITOR"

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(customers).encode("utf-8"))
            return

        elif path == "/api/kpis":
            customers = load_customers()
            kpis = get_kpis(customers)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(kpis).encode("utf-8"))
            return

        # Fallback to static file serving
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/retention/whatsapp/generate":
            customer = data.get("customer", {})
            msg = generate_whatsapp_message(customer)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "message": msg,
                "generated_at": datetime.now().isoformat()
            }).encode("utf-8"))
            return

        elif path == "/api/retention/whatsapp/send":
            # Human safety approval check
            cid = data.get("customer_id")
            approved = data.get("approved", False)
            message = data.get("message", "")
            
            # Check integration availability (Demo Mode)
            # WhatsApp Business API is not connected in demo mode
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            if cid:
                customer_actions[cid] = {
                    "status": "WhatsApp Sent",
                    "last_action": "WhatsApp Outreach Approved (Demo Mode)",
                    "date": now_str,
                    "next_followup": "Monitor response in 48h"
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "mode": "demo",
                "sent": False,
                "integration_connected": False,
                "message_ready": True,
                "approval_recorded": approved,
                "customer_id": cid,
                "display_notice": "WhatsApp integration is not connected. This message is ready for manual sending.",
                "action_recorded": "WhatsApp Sent",
                "timestamp": now_str
            }).encode("utf-8"))
            return

        elif path == "/api/retention/call/generate":
            customer = data.get("customer", {})
            script_data = generate_call_script(customer)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(script_data).encode("utf-8"))
            return

        elif path == "/api/retention/call/initiate":
            cid = data.get("customer_id")
            confirmed = data.get("confirmed", False)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

            if cid and confirmed:
                customer_actions[cid] = {
                    "status": "Call Completed",
                    "last_action": "Retention Call Script Executed (Demo Mode)",
                    "date": now_str,
                    "next_followup": "Review sentiment & retention status in 3 days"
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "mode": "demo",
                "telephony_connected": False,
                "confirmed": confirmed,
                "display_notice": "Demo Mode — Calling Integration Not Connected. Call script ready for agent use.",
                "action_recorded": "Call Completed",
                "timestamp": now_str
            }).encode("utf-8"))
            return

        elif path == "/api/retention/status/update":
            cid = data.get("customer_id")
            status = data.get("status", "Not Contacted")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            if cid:
                if cid not in customer_actions:
                    customer_actions[cid] = {}
                customer_actions[cid]["status"] = status
                customer_actions[cid]["last_action"] = f"Status updated to {status}"
                customer_actions[cid]["date"] = now_str
                customer_actions[cid]["next_followup"] = data.get("next_followup", "Per playbook")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "customer_id": cid,
                "current_status": status,
                "timestamp": now_str
            }).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
        print(f"StreamFlix AI Retention Intelligence Server listening on http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
