from dataclasses import dataclass
@dataclass
class InstitutionPOJO:
    institution_name : str
    institution_code : str = ''

@dataclass
class CustomerPOJO:
    customer_name : str
    institution_code : str
    customer_balance : float
    customer_id : str = ''

@dataclass
class ProductPOJO:
    product_name : str
    rest_balance : int
    day_profit : float
    product_id: str = ''

@dataclass
class PurchaseProduct:
    客户编号 : str
    产品编号 : str
    投资金额 : float = 0.0
    投资期限 : int = 0
    Flag : int = 0

@dataclass
class RedeemProduct:
    投资编号 : str

@dataclass
class MlAnomalies:
    zscore阈值 : float = 0.0
    数据top : float = 0.0

@dataclass
class LoginRequest:
    username : str
    password : str