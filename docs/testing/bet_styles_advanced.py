increase_values = [1, 1.3, 1.5, 2, 3, 4]

last = 10
testing = []
for i in range(1,11):
    if 0.1 * last > 100:
        last = last//500 * 500
    elif 0.1 * last > 10:
        last = last//50 * 50
    else:
        last = round(last/5) * 5
    testing.append(last)
    last *= 2.2 if last<1000 else 1.8


def print_list(lst):
    print(f'\n{lst}')
    print(f'Total potential LOSS per cycle:\n\t10: {sum(lst):,.0f}\n\t9: {sum(lst[:9]):,.0f}\n\t8: {sum(lst[:8]):,.0f}\n\t7: {sum(lst[:7]):,.0f}')
    print(f'9: {sum(lst[:9]):,.0f} RSD | 8: {sum(lst[:8]):,.0f} RSD | 7: {sum(lst[:7]):,.0f} RSD\n')
    invested = 0
    average = []
    for i,amount in enumerate(lst):
        invested += amount
        win = amount*2.35
        average.append((win-invested)/(1+i))
        print(f'Dobitak po rundi {i+1}: {amount} -- {win-invested:,.0f} RSD | {(win-invested)/(1+i):,.2f} RSD')
    print(f'\nAverage win per round:\n\t10: {sum(average)/10:,.2f}\n\t9: {sum(average[:9])/9:,.2f}\n\t8: {sum(average[:8])/8:,.2f}\n\t7: {sum(average[:7])/7:,.2f}')
        
for increase in increase_values:
    print_testing = map(lambda x: min(11_000, round((x*increase)/5)*5), testing)
    print()
    print('**'*35)
    
    print_list(list(print_testing)[:])