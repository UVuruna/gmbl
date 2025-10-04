increase_values = [1, 1.3, 1.5, 2, 3, 4]
testing = [15,30,60,110,200,360,630,1100,1920,3350]

def print_list(lst):
    print(f'\n{lst} - {sum(lst)} RSD - {len(lst)} rundi\n')
    invested = 0
    for i,amount in enumerate(lst):
        invested += amount
        win = amount*2.35
        
        print(f'Dobitak po rundi {i+1}: {amount} -- {win-invested:,.0f} RSD | {(win-invested)/(1+i):,.2f} RSD')
        
for increase in increase_values:
    print_testing = map(lambda x: min(11_000, round((x*increase)/5)*5), testing)
    print()
    print('**'*35)
    
    print_list(list(print_testing)[:])