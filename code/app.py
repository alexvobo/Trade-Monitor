from time import sleep
import threading
import re
from tabulate import tabulate
import numpy as np
from pycoingecko import CoinGeckoAPI

import os

from json_file_ops import save_file, load_file
SAVE_DIR = "stored_data"
EXCHANGES = ["binance", "uniswap", "kucoin"]
DEFAULT_JSON = {"coin": "", "coin_sym": "", "coin_id": "", "last_price": 0,
                "table": {"position_size": [], "price": []}, "total_purchased": 0, "avg_price": 0, "cost": 0.0, "pnl": 0.0, "per_change": 0.0}
CG = CoinGeckoAPI()

# region file ops


def save(fname, data):
    # save table
    save_file(os.path.join(SAVE_DIR, fname), data)


def load(fname):
    # load table otherwise load empty table
    if fname:
        try:
            data = load_file(os.path.join(SAVE_DIR, fname))
            return data
        except IOError:
            print("No data found... \n")

    return DEFAULT_JSON
# endregion


def avg_buyin(prices, amounts):
    return np.average(prices, weights=amounts)


def get_stats(data):
    table = data['table']

    print(tabulate(table, headers="keys", tablefmt="fancy_grid"))

    data['total_purchased'] = sum(table['position_size'])
    print("Total purchased: {} {}".format(
        data['total_purchased'], data['coin_sym']))
    data['avg_price'] = round(
        avg_buyin(table['price'], table['position_size']), 2)
    print("Avg. buy-in price: $" +
          str(data['avg_price']))
    data['cost'] = data['total_purchased'] * data['avg_price']
    print("Cost: $" + str(round(data['cost'], 2)))


def get_symbol(currency):
    if (currency == "usd"):
        return "$"
    elif(currency == "btc"):
        return "₿"
    else:
        return currency


def calc_pnl(pos_size, cost, curr_price, buy_price):
    pnl = round(pos_size * curr_price - cost, 2)
    per_change = round(((curr_price-buy_price)/buy_price)*100, 2)

    return pnl, per_change


def api_thread(fname, json_data):
    vs_currency = "usd"
    symbol = get_symbol(vs_currency)

    sleep_len = 60
    sleep_interval = 5
    while True:
        api_data = CG.get_price(
            ids=json_data['coin_id'], vs_currencies=vs_currency)
        if api_data is None:
            print("Error fetching data... quitting\n")
            break

        json_data['last_price'] = api_data[
            json_data['coin_id'].lower()][vs_currency]

        json_data['pnl'], json_data['per_change'] = calc_pnl(
            json_data['total_purchased'], json_data['cost'], json_data['last_price'], json_data['avg_price'])

        save(fname, json_data)

        for x in range(0, sleep_len, sleep_interval):
            timeleft = sleep_len-x

            s = " Price: {}{} | PNL: {}{} ({}%) | ...Updating in {} ".format(
                symbol, json_data['last_price'], symbol, json_data['pnl'], json_data['per_change'], timeleft)
            print(s, end='\r')

            sleep(sleep_interval)


def get_id_name_sym(coin_name):
    if coin_name:
        coin_list = CG.get_coins_list()

        for coin in coin_list:
            if coin_name.lower() == coin['symbol'] or coin_name.lower() == coin['name']:
                return coin['id'], coin['symbol'].upper(), coin['name'].title()


def file_select():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    file_names = [f for f in os.listdir(SAVE_DIR) if ".json" in f]
    if file_names:

        print("Which file to load? (Enter #): ")
        [print("  {}. {}".format(i+1, f)) for i, f in enumerate(file_names)]
        print(f"  {len(file_names)+1}. New File")

        try:
            user_input = int(input())-1
            if user_input < 0 or user_input >= len(file_names):
                raise IndexError

            return file_names[user_input]
        except (IndexError, ValueError) as e:
            print("Creating new file... ")

    return ""


if __name__ == "__main__":
    v = 1.0
    print("\nTrade Monitor", v, "\n")

    CG = CoinGeckoAPI()
    fname = file_select()
    data = load(fname)

    if not (data['coin'] or data['coin_id'] or data['coin_sym']):
        while True:
            user_input = input("Enter coin name: ")
            coin_id, coin_sym, coin_name = get_id_name_sym(user_input)

            if coin_id and coin_sym and coin_name:
                print(" > found", coin_id.upper())
                data['coin'] = coin_name
                data['coin_id'] = coin_id
                data['coin_sym'] = coin_sym
                break
            else:
                print("Coin [ " + coin_name + " ] not found")

    table = data['table']
    if not (table['price'] or table['position_size']):
        print("- - - type 'done' when finished - - - \n")
        while True:
            amount_price = input(
                "Enter amount, price | Ex. 10000, 2.50: \n")
            if amount_price.lower() == "done":
                break

            try:
                amount, price = map(float, amount_price.split(","))
                table['position_size'].append(amount)
                table['price'].append(price)
            except ValueError:
                print("Invalid Input\n")

    get_stats(data)

    if not fname:
        fname = data['coin_id'] + ".json"

    save(fname, data)

    print("\n-- Current market data --")
    # add delta price
    # add supply metrics
    t = threading.Thread(target=api_thread, args=(fname, data,))
    t.start()
