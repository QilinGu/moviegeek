import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prs_project.settings")

import django
from django.db.models import Count
django.setup()

import pandas as pd
import numpy as np
from builder import DataHelper
from collections import defaultdict

from itertools import combinations
from datetime import datetime

from recommender.models import SeededRecs


def build_association_rules():
    data = retrieve_transactions()
    data = generate_transactions(data)

    data = calculate_support_confidence(data, 0.04)
    save_rules(data)


def retrieve_transactions():
    sql = """
        SELECT *
         FROM  Collector_log
         WHERE event = 'buy'
         ORDER BY session_id, content_id
    """
    cursor = DataHelper.get_query_cursor(sql)
    data = DataHelper.dictfetchall(cursor)

    return data


def generate_transactions(data):
    transactions = dict()

    for transaction_item in data:
        transaction_id = transaction_item["sessionId"]
        if transaction_id not in transactions:
            transactions[transaction_id] = []
        transactions[transaction_id].append(transaction_item["content_id"])

    return transactions


def calculate_support_confidence(transactions, min_sup=0.01):

    N = len(transactions)

    one_itemsets = calculate_itemsets_one(transactions, min_sup)
    two_itemsets = calculate_itemsets_two(transactions, one_itemsets, min_sup)

    rules = calculate_association_rules(one_itemsets, two_itemsets, N)

    return sorted(rules)


def calculate_itemsets_one(transactions, min_sup=0.01):

    N = len(transactions)

    temp = defaultdict(int)
    one_itemsets = dict()

    for key, items in transactions.items():
        for item in items:
            inx = frozenset({item})
            temp[inx] += 1

    # remove all items that is not supported.
    for key, itemset in temp.items():
        if itemset > min_sup * N:
            one_itemsets[key] = itemset

    return one_itemsets

def calculate_itemsets_two(transactions, one_itemsets, min_sup=0.01):
    two_itemsets = defaultdict(int)

    for key, items in transactions.items():
        items = list(set(items))  # remove duplications

        if (len(items) > 2):
            for perm in combinations(items, 2):
                if has_support(perm, one_itemsets):
                    two_itemsets[frozenset(perm)] += 1
        elif len(items) == 2:
            if has_support(items, one_itemsets):
                two_itemsets[frozenset(items)] += 1
    return two_itemsets


def calculate_association_rules(one_itemsets, two_itemsets, N):
    timestamp = datetime.now()

    rules = []
    for source, source_freq in one_itemsets.items():
        for key, group_freq in two_itemsets.items():
            if source.issubset(key):
                target = key.difference(source)
                support = group_freq / N
                confidence = group_freq / source_freq
                rules.append((timestamp, next(iter(source)), next(iter(target)),
                              confidence, support))
    return rules


def generate_transactions(data):
    transactions = dict()

    for transaction_item in data:
        transaction_id = transaction_item["session_id"]
        if transaction_id not in transactions:
            transactions[transaction_id] = []
        transactions[transaction_id].append(transaction_item["content_id"])

    return transactions


def has_support(perm, one_itemsets):
    return frozenset({perm[0]}) in one_itemsets and \
           frozenset({perm[1]}) in one_itemsets


def save_rules(rules):

    #conn = DataHelper.connect_to_db()

    for rule in rules:
        SeededRecs(
            created=rule[0],
            source=str(rule[1]),
            target=str(rule[2]),
            support=rule[3],
            confidence=rule[4]
        ).save()
        sql = """INSERT INTO seeded_recs (created, source, target, support, confidence, type)
             VALUES ('{}', '{}', '{}', {}, {}, 'associate')"""
        print(sql.format(rule[0], rule[1], rule[2], rule[3], rule[4]))
        #conn.cursor().execute(sql.format(rule[0], rule[1], rule[2], rule[3], rule[4]))
    #conn.commit()
    #conn.close()


if __name__ == '__main__':
    print("Calculating association rules...")

    build_association_rules()


