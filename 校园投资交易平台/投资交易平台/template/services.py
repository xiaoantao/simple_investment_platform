import os
import datetime
import numpy as np
import pandas as pd
import sqlite3
import jwt
import hashlib

from datetime import datetime,timedelta,timezone

from fastapi import HTTPException

from template.models import InstitutionPOJO, CustomerPOJO, ProductPOJO,PurchaseProduct,RedeemProduct
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score


DATABASE = "investment.db"
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
class Services:
    institution_path = os.path.join("./datas", "inst.csv")
    institution_columns = ["机构编号", "机构名称"]
    customer_path = os.path.join("./datas", "customer.csv")
    customer_columns = ["客户姓名", "机构编号", "账户额度", "客户编号"]
    product_path = os.path.join("./datas", "product.csv")
    product_columns = ["产品名称", "剩余额度", "日收益率", "产品编号"]
    invest_path = os.path.join("./datas", "invest.csv")
    invest_columns = ["客户编号","产品编号","投资金额","投资期限","Flag"]

    @staticmethod


    @staticmethod
    def read_file(path, cols) :
        if os.path.exists(path):
            df = pd.read_csv(path)
            df = df.loc[:,~df.columns.str.startswith("Unnamed")]
        else:
            df = pd.DataFrame(columns=cols)
            df.to_csv(path)
        return df

    @staticmethod
    def generate_code(flag_str: str, df_inst: pd.DataFrame, id_column: str):
        if df_inst.empty:
            return f"{flag_str}_001"
        param_flag = df_inst[id_column].str.extract(r"(\d+)$", expand=False)
        param_id_num = param_flag.astype(int).max() + 1
        return f"{flag_str}_{param_id_num:03d}"

    def init_db(self):
        conn = sqlite3.connect(DATABASE)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        create_at TEXT DEFAULT(datetime('now','localtime'))
        )""")
        existing = conn.execute("SELECT COUNT(*) FROM users WHERE username='test'").fetchone()[0]
        if existing == 0:
            hash_password = hashlib.sha256("123456".encode()).hexdigest()
            conn.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)",
                         ("test",hash_password,"admin"))
            conn.commit()
        conn.close()
    @staticmethod
    def get_db():
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            return conn
    @staticmethod
    def create_token(user_id : int,username : str,role : str):
        payload = {
            "user_id" : user_id,
            "username" : username,
            "role" : role,
            "exp" : datetime.now(timezone.utc) + timedelta(hours=24)
        }
        return jwt.encode(payload,JWT_SECRET,algorithm=JWT_ALGORITHM)

    def verify_token(token : str):
        try :
            payload = jwt.decode(token,JWT_SECRET,JWT_ALGORITHM=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401,detail="Token 已过期")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401,detail="无效 Token")

    def add_institutions(self, institutionPOJO: InstitutionPOJO):
        try:
            df_institution = Services.read_file(self.institution_path, self.institution_columns)
            if (df_institution["机构名称"].astype(str).str.strip() == institutionPOJO.institution_name.strip()).any():
                return {
                    "success": False,
                    "message": f"{institutionPOJO.institution_name}已经存在"
                }
            institution_code = self.generate_code("inst", df_institution, "机构编号")
            new_institution = pd.DataFrame(
                [{"机构编号": institution_code, "机构名称": institutionPOJO.institution_name}])
            pd.concat([df_institution, new_institution], ignore_index=True).to_csv(self.institution_path,index=False)

            return {
                "success": True,
                "message": f"添加{institutionPOJO.institution_name}成功"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"添加{institutionPOJO.institution_name}失败,失败的原因是:{str(e)}"
            }

    def load_institution(self) :
        df_institution = self.read_file(self.institution_path, self.institution_columns)
        return {"institutions": df_institution.fillna("").astype(str).to_dict('records')}

    def add_customer(self, customerPOJO: CustomerPOJO):
        df_customer = Services.read_file(self.customer_path, self.customer_columns)
        try:
            customer_id = self.generate_code("customer", df_customer, "客户编号")
            if (customerPOJO.customer_name.strip() == df_customer["客户姓名"].astype(str).str.strip()).any():
                return {
                    "success": False,
                    "message": f"客户{customerPOJO.customer_name}已存在!"
                }
            else:
                new_df_customer = pd.DataFrame([{"客户姓名": customerPOJO.customer_name,
                                                 "机构编号": customerPOJO.institution_code,
                                                 "账号额度": customerPOJO.customer_balance,
                                                 "客户编号": customer_id}])
                pd.concat([df_customer, new_df_customer], ignore_index=True).to_csv(self.customer_path, index=False)
                return {
                    "success": True,
                    "message": f"客户{customerPOJO.customer_name}添加成功"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"客户{customerPOJO.customer_name}添加失败,失败的原因是{str(e)}"
            }

    def load_customer(self) :
        df_customer = Services.read_file(self.customer_path, self.customer_columns)
        df_customer_dict = df_customer.fillna("").to_dict('records')
        return {
            "customers": df_customer_dict
        }

    def add_product(self,productPOJO : ProductPOJO) :
        df_product = Services.read_file(self.product_path, self.product_columns)
        product_id = self.generate_code("product",df_product,"产品编号")
        try :
            if (productPOJO.product_name.strip() == df_product["产品名称"].fillna("").astype(str).str.strip()).any() :
                return {
                    "success" : False,
                    "message" : f"产品{productPOJO.product_name}已经存在!"
                }
            else :
                new_df_product = pd.DataFrame([{"产品名称":productPOJO.product_name,
                                                "剩余额度":productPOJO.rest_balance,
                                                "日收益率":productPOJO.day_profit,
                                                "产品编号":product_id}])
                pd.concat([df_product,new_df_product],ignore_index=True).fillna("").to_csv(self.product_path,index=False)

                return {
                    "success" : True,
                    "message" : f"产品{productPOJO.product_name}添加成功!"
                }
        except Exception as e :
            return {
                "success" : False,
                "message" : f"产品{productPOJO.product_name}添加失败,失败的原因是:{str(e)}"
            }

    def load_products(self) :
        df_products = Services.read_file(self.product_path,self.product_columns)
        return {
            "products" : df_products.fillna("").astype(str).to_dict('records')
        }

    def purchase_product(self,purchaseProduct : PurchaseProduct) :
        df_customer = self.read_file(self.customer_path, self.customer_columns)
        df_products = self.read_file(self.product_path,self.product_columns)
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        customer_code = purchaseProduct.客户编号
        product_code = purchaseProduct.产品编号
        invest_amount = purchaseProduct.投资金额
        invest_duration = purchaseProduct.投资期限
        flag = purchaseProduct.Flag
        customer_amount = df_customer.query("客户编号 == @purchaseProduct.客户编号")["账号额度"].iloc[0]
        products_quota = df_products.query("产品编号 == @purchaseProduct.产品编号")["剩余额度"].iloc[0]
        if invest_amount <= 0 :
            return {
                "success":False,
                "message":"投资失败,投资金额不能小于0!"
            }
        if products_quota <= 0 :
            return {
                "success":False,
                "message":"投资失败,投资产品余额不足!"
            }
        if customer_amount < invest_amount :
            return {
                "success":False,
                "message":"投资失败,账户余额不足!"
            }
        df_customer.loc[df_customer["客户编号"] == purchaseProduct.客户编号,"账号额度"] = customer_amount - invest_amount
        if products_quota < invest_amount:
            return {
                "success":False,
                "message":"产品剩余余额不足!"
            }
        else:
            df_products.loc[
                df_products["产品编号"] == purchaseProduct.产品编号, "剩余额度"] = products_quota - invest_amount
        purchase_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df_customer.to_csv(self.customer_path,index=False)
        df_products.to_csv(self.product_path,index=False)
        invest_code = self.generate_code("invest",df_invest,"投资编号")

        df_new_invest = pd.DataFrame([{
            "投资编号":invest_code,
            "客户编号":customer_code,
            "产品编号":product_code,
            "投资金额":invest_amount,
            "投资期限":invest_duration,
            "购买时间":purchase_time,
            "Flag": flag
        }])

        pd.concat([self.read_file(self.invest_path,self.invest_columns),df_new_invest],
                  ignore_index=True).to_csv(self.invest_path,index=False)

        return {
            "success":True,
            "message":f"投资产品{purchaseProduct.产品编号}成功!"
        }
    def load_investment(self):
        df_product = self.read_file(self.product_path,self.product_columns)
        df_customer = self.read_file(self.customer_path,self.customer_columns)
        df_inst = self.read_file(self.institution_path,self.institution_columns)
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_invest = df_invest.query("Flag == 0")
        df_cus_invest = pd.merge(df_customer,df_invest,how="inner",left_on="客户编号",right_on="客户编号")
        df_cus_invest_inst = pd.merge(df_cus_invest,df_inst,how="inner",left_on="机构编号",right_on="机构编号")
        df_cus_invest_inst_pro = pd.merge(df_cus_invest_inst,df_product,how="inner",left_on="产品编号",right_on="产品编号")
        all_df_invest = df_cus_invest_inst_pro.sort_values("购买时间",ascending=False).reset_index(drop=True)
        all_invest_col = ["投资编号","客户编号","客户姓名","产品编号","产品名称","投资金额","投资期限","机构编号","机构名称","日收益率","购买时间"]
        return {
            "columns":all_invest_col,
            "data":all_df_invest.fillna("").to_dict("records")
        }

    def redeem_product(self,redeemProduct : RedeemProduct):
        invest_code = redeemProduct.投资编号
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_customer = self.read_file(self.customer_path,self.customer_columns)
        df_product = self.read_file(self.product_path,self.product_columns)
        invest_amount = float(df_invest.loc[df_invest["投资编号"] == invest_code,"投资金额"].iloc[0])
        invest_duration = int(df_invest.loc[df_invest["投资编号"] == invest_code,"投资期限"].iloc[0])
        product_code = df_invest.loc[df_invest["投资编号"] == invest_code,"产品编号"].iloc[0]
        customer_code = df_invest.loc[df_invest["投资编号"] == invest_code,"客户编号"].iloc[0]
        rate_return = df_product.loc[df_product["产品编号"] == product_code,"日收益率"].iloc[0]
        df_customer.loc[df_customer["客户编号"] == customer_code,"账号额度"] += (
            (1 + rate_return) * invest_amount * invest_duration
        )
        df_product.loc[df_product["产品编号"] == product_code,"剩余额度"] += invest_amount
        df_invest.loc[df_invest["投资编号"] == invest_code,"Flag"] = 1
        df_invest_order = df_invest.sort_values("购买时间",ascending=False).reset_index(drop=True)
        df_invest_order.to_csv(self.invest_path,index=False)
        df_customer.to_csv(self.customer_path,index=False)
        df_product.to_csv(self.product_path,index=False)
        return {
            "success":True,
            "message":f"赎回产品成功!"
        }

    def customers(self):
        df_customer = self.read_file(self.customer_path,self.customer_columns)
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_product = self.read_file(self.product_path,self.product_columns)
        df_institution = self.read_file(self.institution_path,self.institution_columns)
        df_cus_inves = pd.merge(df_customer,df_invest,how="inner",left_on="客户编号",right_on="客户编号")
        df_cus_inves_pro = pd.merge(df_cus_inves,df_product,how="inner",left_on="产品编号",right_on="产品编号")
        df_cus_inves_pro_ins = pd.merge(df_cus_inves_pro,df_institution,how="inner",left_on="机构编号",right_on="机构编号")
        df_all = df_cus_inves_pro_ins.sort_values("购买时间",ascending=False).reset_index(drop=True)
        df_all["投资状态"] = df_all["Flag"].apply(lambda x: "投资中" if x == 0 else "已赎回")
        all_invest_col = ["投资编号", "客户编号", "客户姓名", "产品编号", "产品名称", "投资金额", "投资期限",
                          "机构编号", "机构名称", "日收益率", "购买时间","投资状态"]
        total_invest = len(df_invest)
        return {
            "columns":all_invest_col,
            "data":df_all.fillna("").to_dict("records"),
            "total":total_invest
        }

    def customers_groupby(self):
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_invest["购买时间"] = pd.to_datetime(df_invest["购买时间"])
        df_invest["年"] = df_invest["购买时间"].dt.year
        new_df = df_invest.groupby("年").agg({
            "投资期限":"sum"
        }).reset_index()
        return {"chartData":{
            "years":df_invest["年"].to_list(),
            "durations":new_df["投资期限"].to_list()
        }}

    def analysis_institution(self):
        df_institution = self.read_file(self.institution_path,self.institution_columns)
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_customer = self.read_file(self.customer_path,self.customer_columns)
        df_cus_inst = pd.merge(df_customer,df_institution,how="inner",left_on="机构编号",right_on="机构编号")
        df_cus_inst_invest = pd.merge(df_cus_inst,df_invest,how="inner",left_on="客户编号",right_on="客户编号")
        df_group = df_cus_inst_invest.groupby("机构名称").agg(总投资期限=("投资期限","sum"),
                                                              交易数=("投资期限","count")).reset_index()
        df_group["平均交易期限"] = df_group["总投资期限"] / df_group["交易数"]
        return{
            "institutions":df_group["机构名称"].to_list(),
            "totalDurations":df_group["总投资期限"].to_list(),
            "avgDurations":df_group["平均交易期限"].to_list()
        }

    def analysis_customer(self):
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_customer = self.read_file(self.customer_path,self.customer_columns)
        df_cus_invest = pd.merge(df_invest,df_customer,how="inner",left_on="客户编号",right_on="客户编号")
        df_group = df_cus_invest.groupby("客户姓名").agg(投资次数=("客户姓名","count")).reset_index()
        return {
            "customers":df_group["客户姓名"].to_list(),
            "counts":df_group["投资次数"].to_list()
        }

    def analysis_product(self):
        df_product = self.read_file(self.product_path,self.product_columns)
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_pro_invest = pd.merge(df_product,df_invest,how="inner",left_on="产品编号",right_on="产品编号")
        df_group = df_pro_invest.groupby("产品名称").agg(投资次数=("产品名称","count")).reset_index()
        return {
            "products":df_group["产品名称"].to_list(),
            "counts":df_group["投资次数"].to_list()
        }

    def analysis_month(self):
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_invest["购买时间"] = pd.to_datetime(df_invest["购买时间"])
        df_invest["月份"] = df_invest["购买时间"].dt.month
        df_group = df_invest.groupby("月份").agg(总投资期限=("投资期限","sum")).reset_index()
        return {
            "months":df_group["月份"].to_list(),
            "durations":df_group["总投资期限"].to_list()
        }

    def ml_anomalies(self,z: float,top: float):
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        datas_invest_mount = pd.to_numeric(df_invest["投资金额"],errors="coerce").fillna("0.0")
        out = df_invest.copy()
        data_mu = np.mean(datas_invest_mount)
        data_sigma = np.std(datas_invest_mount)
        out["zscore"] = (datas_invest_mount - data_mu) / data_sigma
        out["abs_z"] = out["zscore"].abs()
        out = out.loc[out["abs_z"] >= z].sort_values("abs_z",ascending=False).head(int(top))
        out = out.rename(columns={"Flag":"redeemed"})
        out["redeemed"] = out["redeemed"].apply(lambda x: "investing" if x == 0 else "over_invested")
        result_columns = ["投资编号", "客户编号", "产品编号", "投资金额", "投资期限", "购买时间", "redeemed", "zscore"]
        out = out.drop(columns=["abs_z"],errors="ignore")[result_columns].fillna("")
        records = [{k: str(v) for k,v in r.items()} for r in out.to_dict("records")]
        print(records)
        return {
            "mean":float(data_mu),
            "std":float(data_sigma),
            "anomalies":records
        }

    def ml_segments(self,k: int,max_iter: int=32,seed=10):
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_customer = self.read_file(self.customer_path,self.customer_columns)
        df_invest["投资金额"] = pd.to_numeric(df_invest["投资金额"],errors="coerce").fillna("0.0")
        df_invest["投资期限"] = pd.to_numeric(df_invest["投资期限"],errors="coerce").fillna("0.0")
        agg = df_invest.groupby("客户编号").agg(总投资次数=("投资编号","count"),
                                                总投资金额=("投资金额","sum"),
                                                均投资期限=("投资期限","mean"),
                                                总投资产品数=("产品编号","nunique"))
        agg["笔平均金额"] = agg["总投资金额"] / agg["总投资次数"]
        X = np.array(agg)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        label = KMeans(n_clusters=k, max_iter=max_iter , random_state=seed).fit_predict(Xs)
        agg["segment_id"] = label
        df_merge = pd.merge(agg,df_customer,how="left",on="客户编号").fillna("")
        profile = df_merge.groupby("segment_id").agg(count=("客户编号","count"),
                                                avg_times=("总投资次数","mean"),
                                                avg_amount=("总投资金额","mean"),
                                                avg_duration=("均投资期限","mean"),
                                                avg_products=("总投资产品数","mean"),
                                                avg_per_order=("总投资金额","mean")).reset_index()
        return {
            "k":k,
            "profile":profile.to_dict("records")
        }

    def ml_regression(self):
        df_customer = self.read_file(self.customer_path,self.customer_columns)
        df_product = self.read_file(self.product_path,self.product_columns)
        df_invest = self.read_file(self.invest_path,self.invest_columns)
        df_merge = ((df_invest
                    .merge(df_customer[["客户编号","账号额度"]],on="客户编号",how="left"))
                    .merge(df_product[["产品编号","日收益率"]],on="产品编号",how="left"))
        X_columns = ["投资期限","日收益率","账号额度","期限_收益乘积","额度除以期限"]
        df_merge["期限_收益乘积"] = df_merge["投资期限"] * df_merge["日收益率"]
        df_merge["额度除以期限"] = df_merge["账号额度"] / df_merge["投资期限"]
        for col in X_columns + ["投资金额"]:
            df_merge[col] = pd.to_numeric(df_merge[col],errors="coerce").fillna(0.0)
        X = df_merge[X_columns].to_numpy()
        y = df_merge["投资金额"].to_numpy()
        scaler = StandardScaler()
        X_scaler = scaler.fit_transform(X)
        model = Ridge(alpha=1,random_state=10)
        model.fit(X_scaler,y)
        y_hat = model.predict(X_scaler)
        df_merge["预测投资金额"] = y_hat
        r2 = r2_score(y,y_hat)
        #准备结果
        coef_names = ["intercept"] + X_columns
        coef_values = [model.intercept_] + model.coef_.tolist()
        samples = (df_merge[["投资编号","客户编号","产品编号","投资期限","投资金额"]]
                    .assign(预测投资金额=y_hat)
                    .head(50)
                    .fillna("")
                    .to_dict("records"))
        print(coef_values)


        return {
            "samples":samples,
            "r2":r2,
            "coef":dict(zip(coef_names,coef_values))
        }

services = Services()
services.init_db()









