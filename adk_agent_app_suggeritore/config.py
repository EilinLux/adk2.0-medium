import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()  # Load .env file 

# ==========================================
# 0. SETUP & DATABASE INITIALIZATION
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
