import json

def get_straddle_pair(snapshots):
    calls = {}
    puts = {}
    for contract in snapshots.keys():
        # Contract format: e.g., NVDA260920C00150000
        # Wait, the length depends on the symbol length.
        # But the last 15 characters are always YYMMDD[C/P]STRIKE
        # For example, 6 for date, 1 for C/P, 8 for strike = 15 chars.
        suffix = contract[-15:]
        date_part = suffix[:6]
        cp = suffix[6]
        strike_part = suffix[7:]
        
        base = date_part + strike_part
        if cp == 'C':
            calls[base] = contract
        elif cp == 'P':
            puts[base] = contract
            
    # Find intersection
    for base in calls:
        if base in puts:
            return calls[base], puts[base]
    return None, None

