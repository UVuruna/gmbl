BET_STYLES = {
        '1 very_low': [25, 50, 75, 150, 300, 600, 1200, 2400, 4800],
        '2 low': [30, 60, 90, 180, 360, 720, 1440, 2880, 5760],
        '3 medium': [35, 70, 105, 210, 420, 840, 1680, 3360, 6720],
        '4 high': [40, 80, 120, 240, 480, 960, 1920, 3840, 7680],
        '5 very_high': [45, 90, 135, 270, 540, 1080, 2160, 4320, 8640],
    }

BetNames = ['0 lowest', '1 very_low', '2 low', '3 medium', '4 high', '5 very_high']
bet = 20
for i,name in enumerate(BetNames):
    BET_STYLES[name + '_new'] = []
    next_bet = bet + i*5
    for j in range(9):
        BET_STYLES[name + '_new'].append(next_bet)
        next_bet = int(next_bet * (1.96-2*i/100))

autostop = [2 + i/100 for i in range(51)]

BET_STYLES = dict(sorted(BET_STYLES.items()))

import math

print('*'*33)
print("Simulacija dobitaka za razlicite nacin igre i autostopove")
totalCOEF = 8
for k,v in BET_STYLES.items():
    print('*'*33)
    print(f"Nacin igre: {k} -- {v[:totalCOEF+1]} -- {sum(v[:totalCOEF+1])} RSD")
    print('-'*33)
    for auto in autostop:
        TOTAL = []
        invested = 0
        for i,amount in enumerate(v):
            if i>totalCOEF:
                break
            invested += amount
            earn = (amount * auto - invested) / (i+1)
            TOTAL.append(earn)
        print(f"  Auto: {auto:.2f}x -> avg dobit: {sum(TOTAL)/len(TOTAL):.2f} RSD    ---    {[int(i) for i in TOTAL]}")