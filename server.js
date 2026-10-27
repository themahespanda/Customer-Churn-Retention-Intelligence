const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 5050;
const PUBLIC_DIR = path.join(__dirname, 'public');
const DATA_FILE = path.join(PUBLIC_DIR, 'data.json');

let customers = [];
try {
    customers = JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));
} catch (e) {
    console.error('Error loading data.json:', e);
}

const customerActions = {};

function getKpis(list) {
    const total = list.length;
    const churned = list.filter(c => c.Churned === 1).length;
    const churnRate = total ? +(churned / total * 100).toFixed(2) : 0;
    const critHigh = list.filter(c => c.Risk_Segment === 'Critical' || c.Risk_Segment === 'High');
    const revAtRisk = critHigh.reduce((sum, c) => sum + (c.Monthly_Revenue || 0), 0);
    const avgSat = total ? +(list.reduce((sum, c) => sum + (c.Satisfaction_Score || 0), 0) / total).toFixed(2) : 0;
    const avgRisk = total ? +(list.reduce((sum, c) => sum + (c.Churn_Risk_Score || 0), 0) / total).toFixed(2) : 0;

    return {
        total_subscribers: total,
        churned_subscribers: churned,
        churn_rate_pct: churnRate,
        high_risk_subscribers: critHigh.length,
        revenue_at_risk: revAtRisk,
        average_satisfaction: avgSat,
        average_churn_risk_score: avgRisk
    };
}

function getPrimaryRiskSignal(c) {
    if ((c.Payment_Failures_90d || 0) >= 2) {
        return `Payment Friction: ${c.Payment_Failures_90d} failed recurring transactions in 90 days`;
    }
    if ((c.Complaints_90d || 0) >= 2 || (c.Support_Tickets_90d || 0) >= 7) {
        return `Customer Support Friction: ${c.Complaints_90d} formal complaints and ${c.Support_Tickets_90d} support tickets in 90 days`;
    }
    if ((c.Satisfaction_Score || 5) <= 3.0) {
        return `Low Satisfaction: Rating dropped to ${c.Satisfaction_Score} / 5.0`;
    }
    if ((c.Login_Frequency_Score || 100) < 50 || (c.Avg_Sessions_30d || 10) <= 3) {
        return `Engagement Decline: Only ${c.Avg_Sessions_30d} streaming sessions in 30 days (Login score ${c.Login_Frequency_Score}/100)`;
    }
    if ((c.Discounts_Used_90d || 0) >= 2) {
        return `Price Sensitivity: Applied ${c.Discounts_Used_90d} promo discounts in 90 days`;
    }
    return "Stable Engagement: Low risk indicators";
}

function generateWhatsAppMessage(customer) {
    const name = customer.Customer_Name || 'Subscriber';
    const firstName = name.split(' ')[0];
    const plan = customer.Plan || 'StreamFlix';
    const paymentFails = customer.Payment_Failures_90d || 0;
    const complaints = customer.Complaints_90d || 0;
    const tickets = customer.Support_Tickets_90d || 0;
    const sessions = customer.Avg_Sessions_30d || 0;
    const sat = customer.Satisfaction_Score || 4.0;

    if (paymentFails >= 2) {
        return `Hi ${firstName}, this is Priya from StreamFlix Priority Care. We noticed a recent hiccup renewing your ${plan} subscription payment. To make sure your streaming isn't interrupted, we've enabled a complimentary 48-hour grace period! Would you like a secure one-click link to update your payment details, or would you prefer a quick assistance callback? We're here to help.`;
    } else if (complaints >= 2 || tickets >= 7) {
        return `Hi ${firstName}, this is Vikram from the StreamFlix Executive Care team. We reviewed your recent support inquiries regarding your ${plan} experience, and we sincerely apologize that things weren't as smooth as they should be. I have personally assigned a senior specialist to review your account, and we'd love to schedule a 3-minute check-in at your convenience to make sure everything is completely resolved for you.`;
    } else if (sat <= 3.0) {
        return `Hi ${firstName}, thank you for being a valued ${plan} member on StreamFlix. We're committed to giving you the best streaming experience possible, and we noticed your recent rating indicated we have room to improve. Could you share one quick thing we could do better? As a token of our appreciation for your candid feedback, we'd also love to offer you a complimentary 4K Ultra HD upgrade for your next month.`;
    } else if (sessions <= 3) {
        return `Hi ${firstName}, we’d love to help you get the most out of your ${plan} plan on StreamFlix! We just added top-rated blockbuster releases and exclusive originals curated for your profile that you might enjoy this week. You also have 2 unused stream profiles available on your plan. Check them out anytime, or let us know if you'd like our top 3 weekend recommendations!`;
    } else {
        return `Hi ${firstName}, thank you for being a wonderful ${plan} subscriber with StreamFlix! We're celebrating our top loyal members this month with exclusive early access to upcoming season premieres and an invitation to share an invite pass with a friend. Enjoy your streaming, and thank you for being with us!`;
    }
}

function generateCallScript(customer) {
    const name = customer.Customer_Name || 'Subscriber';
    const firstName = name.split(' ')[0];
    const plan = customer.Plan || 'StreamFlix';
    const paymentFails = customer.Payment_Failures_90d || 0;
    const complaints = customer.Complaints_90d || 0;
    const tickets = customer.Support_Tickets_90d || 0;
    const sat = customer.Satisfaction_Score || 4.0;
    const sessions = customer.Avg_Sessions_30d || 0;

    let reason, discovery, response, offer;

    if (paymentFails >= 2) {
        reason = "Resolve recurring billing failure and provide payment grace period";
        discovery = "I noticed a payment processing error on your last billing cycle. Did you recently change cards or experience an unexpected bank decline?";
        response = "Acknowledge the inconvenience immediately. Reassure the customer that their streaming access has been temporarily safeguarded, and offer to walk them through a secure UPI/card renewal.";
        offer = "Offer waiver of any late retry fees plus a 14-day billing extension while updating the preferred payment method.";
    } else if (complaints >= 2 || tickets >= 7) {
        reason = "Executive service recovery following multiple recent support interactions";
        discovery = "I'm calling personally from our Subscriber Advocacy desk. Looking at your recent tickets, it looks like your streaming experience wasn't up to standard. How is the service performing for you right now?";
        response = "Listen empathetically without interrupting. Validate their frustration, take full ownership, and detail the technical fix already in place.";
        offer = "Provide dedicated senior concierge support line + credit 1 month of subscription fee as service recovery.";
    } else if (sat <= 3.0) {
        reason = "Service quality discovery and satisfaction restoration";
        discovery = "We noticed your recent satisfaction feedback was lower than we strive for. What is the single biggest thing that hasn't met your expectations?";
        response = "Thank them warmly for their honesty. Relate their feedback to upcoming product features or content library expansions.";
        offer = "Offer immediate plan perk upgrade (e.g., ad-free streaming or 4K multi-device stream) at zero additional charge.";
    } else if (sessions <= 3) {
        reason = "Usage re-activation and personalized content walkthrough";
        discovery = `We noticed you haven't had much time to stream your favorite shows on your ${plan} plan lately. Have you had trouble finding titles you love, or experiencing any device issues?`;
        response = "Guide them towards newly released genres matching their viewing history; explain how to set up download-and-watch-offline on mobile.";
        offer = "Complimentary access to premium curated festival screenings and extended watchlist features.";
    } else {
        reason = "Loyalty recognition and VIP customer appreciation";
        discovery = "As one of our longest-tenured subscribers, what features or content categories would you like to see StreamFlix add next?";
        response = "Document feature suggestions for the product team; thank them for their loyalty.";
        offer = "Exclusive invitation to StreamFlix Beta Viewer Community with bonus referral rewards.";
    }

    return {
        customer_name: name,
        reason_for_contact: reason,
        script: {
            opening: `Hello ${firstName}, my name is [Agent Name] with StreamFlix Member Relations. Am I catching you at a convenient time for a brief 2-minute conversation regarding your ${plan} subscription?`,
            reason_for_contact: `The reason for my call today is to ensure you're getting full value and seamless streaming from your ${plan} account, and to personally assist with ${reason.toLowerCase()}.`,
            discovery_question: discovery,
            recommended_response: response,
            retention_offer: offer,
            closing: `Thank you so much for your valuable time and feedback today, ${firstName}. I'll personally follow up on everything we discussed. Have a wonderful rest of your week with StreamFlix!`
        }
    };
}

const mimeTypes = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png'
};

const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    const pathname = url.pathname;

    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    if (req.method === 'GET') {
        if (pathname === '/api/customers') {
            const enriched = customers.map(c => {
                const cid = c.Customer_ID;
                const state = customerActions[cid] || {};
                const score = c.Churn_Risk_Score || 0;
                const seg = c.Risk_Segment || 'Low';
                const rev = c.Monthly_Revenue || 0;

                let priority = 'MONITOR';
                if (seg === 'Critical' || (seg === 'High' && rev >= 1499) || score >= 60) priority = 'IMMEDIATE';
                else if (seg === 'High' || (seg === 'Medium' && rev >= 2000)) priority = 'HIGH';
                else if (seg === 'Medium') priority = 'NORMAL';

                return {
                    ...c,
                    Action_Status: state.status || c.Action_Status || 'Not Contacted',
                    Last_Action: state.last_action || c.Last_Action || 'None',
                    Last_Action_Date: state.date || c.Last_Action_Date || '-',
                    Next_Followup: state.next_followup || c.Next_Followup || 'Pending outreach',
                    Primary_Signal: getPrimaryRiskSignal(c),
                    Retention_Priority: priority
                };
            });
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(enriched));
            return;
        }

        if (pathname === '/api/kpis') {
            const kpis = getKpis(customers);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(kpis));
            return;
        }

        let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            const ext = path.extname(filePath).toLowerCase();
            res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
            fs.createReadStream(filePath).pipe(res);
            return;
        }

        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('File not found');
        return;
    }

    if (req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            let data = {};
            try { data = JSON.parse(body); } catch (e) {}

            const nowStr = new Date().toISOString().replace('T', ' ').substring(0, 16);

            if (pathname === '/api/retention/whatsapp/generate') {
                const customer = data.customer || {};
                const message = generateWhatsAppMessage(customer);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, message, generated_at: nowStr }));
                return;
            }

            if (pathname === '/api/retention/whatsapp/send') {
                const cid = data.customer_id;
                const approved = data.approved || false;
                if (cid) {
                    customerActions[cid] = {
                        status: 'WhatsApp Sent',
                        last_action: 'WhatsApp Outreach Approved (Demo Mode)',
                        date: nowStr,
                        next_followup: 'Monitor response in 48h'
                    };
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    mode: 'demo',
                    sent: false,
                    integration_connected: false,
                    approval_recorded: approved,
                    display_notice: 'WhatsApp integration is not connected. This message is ready for manual sending.',
                    action_recorded: 'WhatsApp Sent',
                    timestamp: nowStr
                }));
                return;
            }

            if (pathname === '/api/retention/call/generate') {
                const customer = data.customer || {};
                const scriptData = generateCallScript(customer);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(scriptData));
                return;
            }

            if (pathname === '/api/retention/call/initiate') {
                const cid = data.customer_id;
                if (cid) {
                    customerActions[cid] = {
                        status: 'Call Completed',
                        last_action: 'Retention Call Script Executed (Demo Mode)',
                        date: nowStr,
                        next_followup: 'Review sentiment in 3 days'
                    };
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    mode: 'demo',
                    telephony_connected: false,
                    display_notice: 'Demo Mode — Calling Integration Not Connected. Call script ready for agent use.',
                    action_recorded: 'Call Completed',
                    timestamp: nowStr
                }));
                return;
            }

            if (pathname === '/api/retention/status/update') {
                const cid = data.customer_id;
                const status = data.status || 'Not Contacted';
                if (cid) {
                    customerActions[cid] = {
                        ...(customerActions[cid] || {}),
                        status,
                        last_action: `Status manually updated to ${status}`,
                        date: nowStr,
                        next_followup: data.next_followup || 'Per playbook'
                    };
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, customer_id: cid, current_status: status, timestamp: nowStr }));
                return;
            }

            res.writeHead(404, { 'Content-Type': 'text/plain' });
            res.end('Not found');
        });
        return;
    }

    res.writeHead(405, { 'Content-Type': 'text/plain' });
    res.end('Method Not Allowed');
});

server.listen(PORT, () => {
    console.log(`StreamFlix Retention Intelligence Server running on http://localhost:${PORT}`);
});
