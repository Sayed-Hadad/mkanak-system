from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .product import Product
from .category import Category
from .branch import Branch
from .dealer import Dealer
from .movement import ProductMovement
from .request import ProductRequest
from .notification import BranchNotification
from .branch_inventory import BranchInventory
from .sale import Sale, SaleItem
from .customer import Customer