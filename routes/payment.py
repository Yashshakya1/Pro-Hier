from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import razorpay
import hmac
import hashlib
import os
import json
from datetime import datetime, timedelta

router = APIRouter()

client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID", "mock_id"), os.getenv("RAZORPAY_KEY_SECRET", "mock_secret"))
)

class OrderRequest(BaseModel):
    user_id: str
    plan: str

class VerifyPayment(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    user_id: str
    plan: str

PLANS = {
    "monthly": 9900,
    "annual":  59900,
    "pro":     24900,
}

PLAN_DAYS = {
    "monthly": 30,
    "annual":  365,
    "pro":     30,
}

DB_FILE = "payment_db.json"

def read_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "usage": {}}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "usage": {}}

def write_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

@router.post("/payment/create-order")
async def create_order(req: OrderRequest):
    try:
        amount = PLANS.get(req.plan)
        if not amount:
            raise HTTPException(status_code=400, detail="Invalid plan")

        order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"prohire_{req.user_id[:8]}_{req.plan}",
            "notes": {
                "user_id": req.user_id,
                "plan": req.plan
            }
        })

        return {
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key_id": os.getenv("RAZORPAY_KEY_ID", "mock_id")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/verify")
async def verify_payment(req: VerifyPayment):
    try:
        msg = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
        secret = os.getenv("RAZORPAY_KEY_SECRET", "").encode()
        generated_sig = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()

        if generated_sig != req.razorpay_signature:
            raise HTTPException(status_code=400, detail="Invalid signature")

        days = PLAN_DAYS.get(req.plan, 30)
        expiry = datetime.utcnow() + timedelta(days=days)

        db = read_db()
        db["users"][req.user_id] = {
            "plan": req.plan,
            "is_pro": True,
            "subscription_expiry": expiry.isoformat(),
            "payment_id": req.razorpay_payment_id,
            "updated_at": datetime.utcnow().isoformat()
        }
        write_db(db)

        return {
            "success": True,
            "plan": req.plan,
            "expiry": expiry.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment/status/{user_id}")
async def check_status(user_id: str):
    try:
        db = read_db()
        user_data = db["users"].get(user_id)

        if not user_data:
            return {"is_pro": False, "plan": "free"}

        expiry_str = user_data.get("subscription_expiry")
        if expiry_str:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.utcnow() > expiry:
                user_data["is_pro"] = False
                user_data["plan"] = "free"
                db["users"][user_id] = user_data
                write_db(db)
                return {"is_pro": False, "plan": "free"}

        return {
            "is_pro": user_data.get("is_pro", False),
            "plan": user_data.get("plan", "free"),
            "expiry": expiry_str
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/check-usage")
async def check_usage(user_id: str, feature: str):
    try:
        db = read_db()
        user_data = db["users"].get(user_id, {})
        is_pro = user_data.get("is_pro", False)

        if is_pro:
            return {"allowed": True, "remaining": 999}

        today = datetime.utcnow().strftime("%Y-%m-%d")
        usage_key = f"{user_id}_{today}"
        usage_data = db["usage"].get(usage_key, {})

        FREE_LIMITS = {
            "resume": 99999,
            "interview": 1,
            "skill_gap": 3,
            "apply": 2,
            "job_search": 1,
        }

        limit = FREE_LIMITS.get(feature, 1)
        current = usage_data.get(feature, 0)

        if current >= limit:
            return {
                "allowed": False,
                "remaining": 0,
                "message": "Free limit khatam! Pro plan lo unlimited access ke liye."
            }

        usage_data[feature] = current + 1
        db["usage"][usage_key] = usage_data
        write_db(db)

        return {
            "allowed": True,
            "remaining": limit - current - 1
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))