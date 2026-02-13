import os
import time
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

class RealYieldAggregator:
    """
    AEGIS DEFI YIELD AGGREGATOR (REAL - WEB3)
    Connects to Ethereum/EVM Blockchain to execute REAL trades.
    Requires PRIVATE_KEY and WEB3_PROVIDER_URI in .env
    """
    def __init__(self):
        self.provider_url = os.getenv("WEB3_PROVIDER_URI")
        self.private_key = os.getenv("PRIVATE_KEY")
        
        if not self.provider_url:
            raise ValueError("❌ FATAL: WEB3_PROVIDER_URI not found in .env. Cannot start Real DeFi Module.")
            
        self.w3 = Web3(Web3.HTTPProvider(self.provider_url))
        
        if not self.w3.is_connected():
            raise ConnectionError(f"❌ FATAL: Could not connect to Web3 Provider: {self.provider_url}")
            
        # Verify Account
        try:
            self.account = self.w3.eth.account.from_key(self.private_key)
            self.address = self.account.address
            print(f"✅ [DeFi-REAL] Connected to Blockchain. Wallet: {self.address}")
            print(f"   Balance: {self.w3.from_wei(self.w3.eth.get_balance(self.address), 'ether'):.4f} ETH")
        except Exception as e:
             raise ValueError(f"❌ FATAL: Invalid PRIVATE_KEY. Check .env: {e}")

        # Uniswap V3 Router (Mainnet) - Example
        self.ROUTER_ADDRESS = "0xE592427A0AEce92De3Edee1F18E0157C05861564" 
        self.router_abi = '[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]'
        
        self.router = self.w3.eth.contract(address=self.ROUTER_ADDRESS, abi=self.router_abi)
        
        # Uniswap V3 Quoter (Mainnet)
        self.QUOTER_ADDRESS = "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6"
        self.quoter_abi = '[{"inputs":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"name":"quoteExactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]'
        self.quoter = self.w3.eth.contract(address=self.QUOTER_ADDRESS, abi=self.quoter_abi)

        # Safety Settings
        self.MAX_GAS_GWEI = 50 
        self.SLIPPAGE_TOLERANCE = 0.005 # 0.5%

    def check_gas_price(self):
        """
        Returns True if gas price is safe (<= MAX_GAS_GWEI).
        """
        try:
            current_gas = self.w3.eth.gas_price
            current_gwei = self.w3.from_wei(current_gas, 'gwei')
            if current_gwei > self.MAX_GAS_GWEI:
                print(f"⚠️ [DeFi-REAL] High Gas Price: {current_gwei:.1f} Gwei > Limit {self.MAX_GAS_GWEI}. Aborting.")
                return False
            return True
        except Exception as e:
            print(f"❌ [DeFi-REAL] Gas Check Error: {e}")
            return False

    def get_quote(self, token_in, token_out, amount_in, fee=3000):
        """
        Gets the expected output amount from Uniswap Quoter.
        """
        try:
            amount_out = self.quoter.functions.quoteExactInputSingle(
                token_in,
                token_out,
                fee,
                amount_in,
                0
            ).call()
            return amount_out
        except Exception as e:
            print(f"❌ [DeFi-REAL] Quote Failed: {e}")
            return None

    def execute_swap(self, token_in, token_out, amount_in, fee=3000):
        """
        Executes a real swap on Uniswap V3.
        """
        print(f"🚀 [DeFi-REAL] Initiating Swap: {amount_in} of {token_in} -> {token_out}")
        
        # 0. Pre-Flight Checks
        if not self.check_gas_price():
            return None

        # 1. Approve Token (If not ETH) - Skipped for brevity in this snippet
        # In a full implementation, check allowance and approve if needed.
        
        # 2. Build Transaction
        # Calculate Minimum Output for Slippage Protection
        print(f"   [DeFi-REAL] Fetching Quote for Slippage Protection...")
        expected_out = self.get_quote(token_in, token_out, amount_in, fee)
        
        if expected_out is None:
             print("❌ [DeFi-REAL] Could not get quote. Aborting swap for safety.")
             return None
             
        min_out = int(expected_out * (1 - self.SLIPPAGE_TOLERANCE))
        print(f"   [DeFi-REAL] Expected: {expected_out} | Min Acceptable: {min_out} (0.5% Slip)")
        
        params = {
            'tokenIn': token_in,
            'tokenOut': token_out,
            'fee': fee,
            'recipient': self.address,
            'deadline': int(time.time()) + 600,
            'amountIn': amount_in,
            'amountOutMinimum': min_out, 
            'sqrtPriceLimitX96': 0
        }
        
        try:
            # Build
            tx = self.router.functions.exactInputSingle(params).build_transaction({
                'from': self.address,
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            
            # Send
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"✅ [DeFi-REAL] Transaction Sent! Hash: {self.w3.to_hex(tx_hash)}")
            return self.w3.to_hex(tx_hash)
            
        except Exception as e:
            print(f"❌ [DeFi-REAL] Swap Failed: {e}")
            return None

if __name__ == "__main__":
    # Test Connection
    try:
        agg = RealYieldAggregator()
    except Exception as e:
        print(e)
