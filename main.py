import math
import urllib.request, json 
import datetime

# At HF13 (v5.x) Loki switched to a multi-line approximation of the exponential curve below
# so that we stick pretty close to it, but now use a simpler, integer-math-only calculation.
heights = [385824,          429024,          472224,          515424,          558624,          601824,          645024,          688224,          731424,          774624,          817824,          861024,        1000000]
lsrloki = [20458.380815527, 19332.319724305, 18438.564443912, 17729.190407764, 17166.159862153, 16719.282221956, 16364.595203882, 16083.079931076, 15859.641110978, 15682.297601941, 15541.539965538, 15429.820555489, 15000]

rewards = []
rdict={}
ndict={}
df = {}

def main():
    flag = 0
    while flag == 0:
        # Get an updated dataset.
        bh_vs_sncount = dict_to_list(blockheight_sncount())
        
        print(f"Current block height: {bh_vs_sncount[0][-1]}")
        pbh = int(input("What block height would you like to measure from? "))
        
        while pbh < 101250 or pbh > bh_vs_sncount[0][-1]:
            if pbh < 101250:
                pbh = int(input("Service Nodes were not around before blockheight 101250?\nWhat blockheight would you like to start from? "))
            if pbh > bh_vs_sncount[0][-1]:
                pbh = int(input("Tht blockheight is in the future.\nWhat blockheight would you like to start from? "))
                
        print(f"\nThe staking requirement at blockheight {pbh} is {lsr(pbh)}. The minimum stake at this block height is {lsr(pbh)/4}\n")
        
        stake = float(input("How many Loki did you stake? "))
        stakerequirement = lsr(pbh)
        
        # Work out how many nodes the user is running based on stake.
        sns = stake/stakerequirement
        i = pbh
        rewards.clear()
        
        # Run through each block and make a list of the potential rewards someone will receive.
        while i < bh_vs_sncount[0][-1]:
            br = snbr(pbh)
            activesn = sncount(pbh, bh_vs_sncount[0], bh_vs_sncount[1])
            rewards.append(br * sns / activesn)
            i += 1
            
        reward = sum(rewards)
        roi = round((reward / stake)*100,2)
        timespan = (bh_vs_sncount[0][-1] - pbh) / 720 / 365
        yroi = reward / timespan
        
        print("\nYou have received %s Loki since blockheight %s.\n" % (round(reward,2), pbh))
        print(f"Your stake:         {stake}")
        print(f"Timespan:           {round(timespan,2)} years")
        print(f"Your rewards:       {round(reward)}")
        print(f"Your overall ROi:   {roi}%")
        print(f"Yearly Loki reward: {round(yroi,2)} Loki")
        print(f"Annual ROI:         {round((yroi/stake)*100,2)}%\n")
        sflag = input("Would you like to calculate again? (Y or N): ").lower()
        if sflag == "n":
            flag = 1
    
## Breaks down a dictionairy into two lists with it's key's and values 
def dict_to_list(dict):
        keys = []
        values = []
        for key, value in dict.items():
            keys.append(key)
            values.append(value)
        return keys, values
    
# Returns dictionairy with blockheight as key and sncount as values.
def blockheight_sncount():
    dataset = get_sncount_data()

    ## dbh is the blockheight at the first timestamp in the dataset.
    dbh = 157579 # 2018-12-10

    ## Keys in data are timestamps, we're converting each day to a blockheight
    ## by adding 720 blocks per day to the previous day.
    for key in dataset:
        df[dbh] = dataset[key]
        dbh = dbh + 720
    return df

# Get historical SN count data from lokidashboard.com.
def get_sncount_data():
    # Pull lokidashboard.com sn count historical data.
    with urllib.request.urlopen("http://88.208.54.18:9000/loki-stats") as url:
        data = json.loads(url.read().decode())
    return time_sncount(data["serviceNodeCountHistory"])

# Returns Dictionairy with time as key and sncount as values.
# Input is list
# Outputs as dictionairy
def time_sncount(li):
    #Convert list to dictionairy.
    for key, value in li:
        rdict[datetime.datetime.strptime(key, '%Y-%m-%dT%H:%M:%SZ')] = value
    # Create new dictionairy with each day and with the year, month, day as key.    
    for key in rdict:
        if key.strftime('%H:%M:%S') == "00:00:00":
            ndict[key.strftime('%Y-%m-%d')] = rdict[key]
    return ndict 

# Work out the staking reqiurement for blockheight(h).
# Inputs: block height(h)
# Return: Service Node Staking Requirement for block height(h)
def lsr(bh):
    if (bh >= 385824):
        if (bh >= heights[-1]):
            return lsrloki[-1]
        i = 0
        for i in range(0,len(heights)):
            if heights[i] > bh:
                return lsrloki[i-1] + (bh - heights[i-1]) * ((lsrloki[i] - lsrloki[i-1]) / (heights[i] - heights[i-1]))
            i+= 1      
    elif bh >= 234767:
        return 15000 + 25007 * 2**((101250-bh)/129600.)
    else:
        return 10000 + 35000 * 2**((101250-bh)/129600.)

# Work out the block reward for blockheight(h).
# Inputs: block height(h)
# Return: block reward for block height(h)
def snbr(bh):
    if bh >= 496969:
        return 16.5
    else:
        return round((14 + 50 * 2**(-bh/64800)),9)
    
# This is calulated from the (continuous) integral, calculated with a 0.5 offset (to accomodate for
# the fact that the actual emission value is the width-1 Riemann sum calculated using the
# right-hand-side of the width-1 slices).  It's also inaccurate because the LAG fee comes out only
# every 5040 blocks, but should be accurate over time.
def coinbase_f(bh):
    return -2025/math.log(2) * 2**(5 - (bh + 0.5)/64800)

def coinbase(bh):
    # Emission as of block 260154: 39755876274813016.
    coinbase_known = 39755876274813016
    coinbase_known_h = 260154
    return coinbase_known * 1e-9 + 28 * (bh - coinbase_known_h) + 100*(coinbase_f(bh) - coinbase_f(coinbase_known_h))

# Take in a blockheight(bh) and two lists; blockheights vs active sn count.
# approximation of SN count.
def sncount(bh,keys,values):
    i = 0
    ## Iterate over lists and work out the average between two data points to provide a SN 
    ## count for any BH.
    for i in range(0,len(keys)):
        if keys[i] > bh:
            return values[i-1] + (bh - keys[i-1]) * ((values[i] - values[i-1]) / (keys[i] - keys[i-1]))
        i+= 1
        
main()
