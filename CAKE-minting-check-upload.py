import asyncio
from bscscan import BscScan #pip install bscscan-python

API_KEY = "INSERT YOUR API KEY HERE" #BscScan API 
BSC_BLOCK_TIME = 3 # 3 s/block
BLOCKS_PER_WEEK = (60 * 60 * 24 * 7) // BSC_BLOCK_TIME # ~201,600 blocks/week

# Browser testing: 
  
"""
We query BscScan's API's "logs" module for any "Transfer" events the CAKE smart contract (0x0E09) emits that originated from the null address (0x0000),
signifying that CAKE has been minted, which is the only possibility if a Transfer event is emitted from address(0). The null address in the "topic1" parameter must be padded 
to be 64 hexadecimal digits = 32 bytes long.

https://api.bscscan.com/api
   ?module=logs
   &action=getLogs
   &fromBlock={Insert start block}
   &toBlock={Insert end block}
   &address=0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82
   &topic1=0x0000000000000000000000000000000000000000000000000000000000000000
   &apikey={Insert API key}
"""
# 996 objects where a CAKE transfer event from the null address 0x0...0000 (mint) occurred returned in 686 blocks (block 15000000 to 15000686)
# 664 in 686 blocks (block 16729853 to 16730539)
# 94 in 686 blocks (block 18002315 to 18003001) 472 in 5000 (~7.29x) blocks (end 18007315) 778 in 10000 (~14.58x) blocks (end 18012315) 990 in 12850 (~18.73x) (end 18015166)


# PRIORITIZE DATA FROM THIS TIMEFRAME (most recent)
# 18 in 686 blocks (block 21768295 to 21768981) 540 in 34300 (20x) blocks (end 21802595) 990 in 60000 (~87.46x) blocks (end 21828295)
# 8 in 686 blocks (block 22028637 to 22029323) 994 in 56000 (~81.63x) blocks (end 22084637) 
# 16 in 686 blocks (block 22084637 to 22085323) 892 in 56000 (~81.63x) blocks (end 22140637) 996 in 61500 (~89.65x) blocks (end 22146137)
# 4 in 686 blocks (block 22161934 to 22162620) 736 in 56000 (~81.63x) blocks (end 22217934) 890 in 65000 (~94.75x) blocks (end 22226934) 994 in 69000 (~100.58x) blocks (end 22230934)
# All queries above return close to the maximum # of objects returned (1000) in 56000-69000 block timespans

# Therefore, to balance efficiency and data completeness, query 40-50 thousand-block periods at a time
# 201,600 blocks in 1 week, so let's do 5 queries of 201600/5 = 40320-block periods
# Note that using 40-50 thousand-block periods will only work for recent periods, say, from block 21,000,000 (Sept. 03, 2022) onwards
# CAKE's minting rate was last altered Aug. 11, 2022 (https://docs.pancakeswap.finance/tokenomics/cake/cake-tokenomics), targeting ~321,200 CAKE emitted daily,
# or ~2,248,400 weekly. Let's verify that this is true.

# The order in which we process the API calls doesn't matter since we just want a lump sum of how much CAKE was minted in the span of roughly 1 week 
# The 1-week period is randomly chosen, so it should serve as a good proxy for how much CAKE is minted in other 1-week periods (occurring after Aug. 11, 2022)

QUERIES = 5 # BscScan API rate limits at 5 queries/s
BLOCKS_PER_QUERY = BLOCKS_PER_WEEK // QUERIES # 201,600 / 5 = 40,320
MINT_CONTRACT = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82" # The CAKE smart contract's address on BSC

# Where the CAKE is minted from (technically, minting is just updating some balances in the token's smart contract, but we say that minted tokens come from the null address)
MINT_FROM = "0x0000000000000000000000000000000000000000000000000000000000000000" # Padded to be 32 bytes long by requirement 
EVENT_TYPE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef" # I assume this means "Transfer"
FIRST_BLOCK = 21000000 # Adjust this as you like (Keep this number above 20,000,000 or so)
FINAL_BLOCK = FIRST_BLOCK + BLOCKS_PER_WEEK # Alter the time frame if you wish

STARTING_BLOCKS = range(FIRST_BLOCK, FINAL_BLOCK, BLOCKS_PER_QUERY)
DECIMALS = 10 ** 18 # BEP-20 tokens have 18 decimal places by default

# Roughly 72.12% of CAKE is burnt without entering circulation.
# Verify the ratio below by visting https://bscscan.com/address/0xa5f8c5dbd5f286960b9d90548680ae5ebff07652#readContract and checking variables 5. "MASTERCHEF_CAKE_PER_BLOCK" and 12.
# "cakePerBlockToBurn" after dividing both by 10 ** 18. 
BURNED_RATIO = 28.8472 / 40 

async def main():
  async with BscScan(API_KEY) as bsc:
    # We will receive QUERIES lists as results and gather them into one big list.
    results = await asyncio.gather(*[bsc.get_logs(
      from_block = start_block, 
      to_block = (start_block + BLOCKS_PER_QUERY), 
      address = MINT_CONTRACT,
      topic_0 = EVENT_TYPE, 
      topic_1 = MINT_FROM) 
      for start_block in STARTING_BLOCKS])
    
    cake_minted = 0
    
    # We process each list and each dictionary containing transactions in each list for how much CAKE was "minted", including CAKE directly sent to the burn address 
    for list in results:
      for tx in list:
        cake_minted += int(tx["data"], 0) # Convert from hexadecimal
    
    # This is how much CAKE actually gets emitted, which gets divided up among farms, the Syrup pool, and the Lottery
    cake_emitted = (cake_minted / DECIMALS ) * (1 - BURNED_RATIO)
    
    print('{:,} CAKE emitted from block {:,} to block {:,}.'.format(cake_emitted, FIRST_BLOCK, FINAL_BLOCK))      

if __name__ == "__main__":
  asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) # This is necessary for Windows users
  asyncio.run(main())