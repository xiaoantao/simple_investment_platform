import hashlib

import uvicorn
from fastapi import FastAPI, Query
from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI,HTTPException,Depends
from models import InstitutionPOJO, CustomerPOJO, ProductPOJO, PurchaseProduct,RedeemProduct,LoginRequest
from services import Services
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
services = Services()
services.init_db()
@app.post("/api/login")
async def login(body : LoginRequest):
    conn = Services.get_db()
    password_hash = hashlib.sha256(body.password.encode()).hexdigest()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                        (body.username,password_hash)).fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401,detail="用户名或密码错误!")

    user_token = Services.create_token(user["id"],user["username"],user["role"])
    return {
        "code" : 200,
        "message" : "登陆成功",
        "token" : user_token,
        "user" : {
            "id" : user["id"],
            "username" : user["username"],
            "role" : user["role"]
        }
    }

@app.post("/add_institutions")
async def add_institutions(body : InstitutionPOJO):
    return services.add_institutions(body)

@app.get("/institutions_list")
async def load_institutions():
    return services.load_institution()

@app.post("/add_customer")
async def add_customer(body : CustomerPOJO):
    return services.add_customer(body)

@app.get("/load_customers")
async def load_customers():
    return services.load_customer()

@app.post("/add_product")
async def add_product(body : ProductPOJO):
    return services.add_product(body)

@app.get("/load_products")
async def load_products():
    return services.load_products()

@app.post("/purchase_product")
async def purchase_product(body : PurchaseProduct):
    return services.purchase_product(body)

@app.get("/current_investments")
async def current_investment():
    return services.load_investment()

@app.post("/redeem_product")
async def redeem_product(body : RedeemProduct):
    return services.redeem_product(body)

@app.get("/customers")
async def customers(limit : int=1000):
    return services.customers()

@app.get("/customers_groupby")
async def customers_groupby():
    return services.customers_groupby()

@app.get("/analysis/institution")
async def analysis_institution():
    return services.analysis_institution()

@app.get("/analysis/customer")
async def analysis_customer():
    return services.analysis_customer()

@app.get("/analysis/product")
async def analysis_product():
    return services.analysis_product()

@app.get("/analysis/month")
async def analysis_month():
    return services.analysis_month()

@app.get("/ml/anomalies")
async def ml_anomalies(z: float = Query(description="前端传入Z-score阈值"),top: int = Query(default=20,description="展示前N条异常数据")):
    return services.ml_anomalies(z,top)

@app.get("/ml/segments")
async def ml_segments(k: int = Query(description="前端传入k质心取值")):
    return services.ml_segments(k)

@app.get("/ml/regression")
async def ml_regression():
    return services.ml_regression()

if __name__ == "__main__" :
    uvicorn.run(app,host="127.0.0.1",port=8002)