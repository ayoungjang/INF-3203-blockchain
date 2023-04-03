# backbone/consensus.py
import time, sys, os, rsa
import requests
from typing import List
from datetime import datetime

sys.path.insert(0,"..")
from backbone.merkle import MerkleTree
from abstractions.block import Block, Blockchain
from abstractions.transaction import Transaction
from abstractions.user import User
from utils.flask_utils import flask_call
from utils.cryptographic import *
from utils.view import get_difficulty_from_hash
from requests.packages.urllib3.exceptions import InsecureRequestWarning # type:ignore
from server import BLOCK_PROPOSAL, GET_USERS, GET_BLOCKCHAIN, REQUEST_TXS, SELF

# TODO: Implement Proof of Work
def proof_of_work(prev_hash:str, timestamp:float, mk_root:str, difficulty:int):
    nonce:int = 0
    hash = double_hash(prev_hash + str(timestamp) + mk_root + str(nonce))
    while (get_difficulty_from_hash(hash) < difficulty):
        nonce += 1
        hash = double_hash(prev_hash + str(timestamp) + mk_root + str(nonce))
    return [hash, nonce, timestamp]

# TODO: Build a block
def mine_block() -> Block:
    diff = get_my_difficulty()
    #diff = 2 # testing purpose only
    last_node = get_last_block_from_longest_chain()
    txs = get_transactions()
    mkroot = MerkleTree(txs).get_root().hash
    me = get_my_user_obj()

    # start proof of work
    start = time.time()
    print('start mining', start)
    mined_hash, mined_nonce, mined_time = proof_of_work(last_node.hash, datetime.now().timestamp(), mkroot, diff)
    end = time.time()
    print('done mining', end)
    creation_time = end - start
    sign = me.sign(mined_hash)
    
    # create new block
    new_block = Block(mined_hash, mined_nonce, mined_time, creation_time,
                      last_node.height + 1, last_node.hash, txs,
                      True, False, mkroot, [], SELF, sign)
    return new_block


def get_signature(hash:str) -> str:
    with open("..//vis//users//do-develop_pvk.pem", 'r') as f:
        prv_key = load_private(f.read())
    return rsa.sign(hash, prv_key, 'SHA-1')


def get_private_key() -> str:
    with open("..//vis//users//do-develop_pvk.pem", 'r') as f:
        return load_private(f.read())

def get_public_key() -> str:
    with open("..//vis//users//do-develop_pbk.pem", 'r') as f:
        return load_public(f.read())

def get_transactions():
    _, txs, code = flask_call('GET', REQUEST_TXS)
    if txs and code == 200:
        transactions = []
        for tx in txs:
            t = Transaction.load_json(json.dumps(tx))
            transactions.append(t)
        return transactions
    raise ('request_txs get error')

def get_transaction_hashes(last_node:Block) -> List[str]:
    my_txs = []
    for tx in last_node.transactions:
        my_txs.append(tx.hash)
    return my_txs

def get_last_block_from_longest_chain():
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    _, blockchain, code = flask_call('GET', GET_BLOCKCHAIN)
    if blockchain and code == 200:
        b_chain = Blockchain.load_json(json.dumps(blockchain))
        if b_chain.is_chain_valid():
            fork = []
            bchain = b_chain.block_list
            # find fork
            i = 1
            while i < len(bchain):
                if not bchain[i].confirmed:
                    fork.append([bchain[i-1], []]) # [start block, branch list]
                    idx = i
                    while idx < len(bchain) and not bchain[idx].confirmed:
                        fork[-1][1].append(bchain[idx])
                        idx += 1
                    i = idx
                else:
                    i += 1

            # does any forks have the same fork start?
            j = len(fork) - 2
            branches = [fork[j + 1][1]]
            while fork[j + 1][0] == fork[j][0]:
                branches.append(fork[j][1])
                j -= 1

            # get last block of the best effort branch
            max_effort:float = float('-inf')
            best_branch:List[Block] = None # branch with the most effort
            for i in range(len(branches)):
                effort = get_total_effort(branches[i])
                if effort > max_effort:
                    max_effort = effort
                    best_branch = branches[i]
                elif effort == max_effort: # same effort between branches
                    cur_height = branches[i][-1].height
                    pre_height = best_branch[-1].height
                    if cur_height > pre_height: best_branch = branches[i]
            return best_branch[-1]
        raise("Invalid chain")
    raise("GET_BLOCKCHAIN error")


# def get_last_block():
#     requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
#     _, blockchain, code = flask_call('GET', GET_BLOCKCHAIN)
#     if blockchain and code == 200:
#         b_chain = Blockchain.load_json(json.dumps(blockchain))
#         if b_chain.is_chain_valid():
#             return b_chain.block_list[-1]
#     raise Exception("'Error in flask GET call, get_blockchain'")

def get_my_user_obj() -> User:
    _, users, code = flask_call('GET', GET_USERS)
    if code != 200:
        print("error in flask_call('GET', GET_USERS)")
        return
    # get my mined_blocks count
    for user in users:
        u = User.load_json(json.dumps(user))
        if u.username == SELF:
            u.privkey = get_private_key()
            u.pubkey = get_public_key()
            return u

def get_my_difficulty() -> int:
    me = get_my_user_obj()
    b_count = me.mined_blocks
    # find my difficulty
    if b_count < 10:
        my_diff = 6
    elif 10 <= b_count < 100:
        my_diff = 7
    elif 100 <= b_count < 200:
        my_diff = 8
    elif 200 <= b_count < 500:
        my_diff = 9
    else:
        my_diff = 10
    return my_diff


def get_total_creation_time(blocks: List[Block]):
    ttime = 0
    for block in blocks:
        ttime += calculate_chainwork(block.creation_time)
    return ttime

def get_total_effort(blocks: List[Block]):
    effort = 0
    for block in blocks:
        effort += calculate_chainwork(block.hash)
    return effort

def calculate_chainwork(hash):
    diff = get_difficulty_from_hash(hash)
    target = int(("0" * diff + "f" * (64 - diff)), 16)
    return (2 ** 256) / target

#############################################################################
# UNIT TEST #
#############################################################################
if __name__ == "__main__":

    # TEST - MerkleTree
    # if b_chain.is_chain_valid():
    #     last_node = b_chain.block_list[-1]
    #     llast_node = b_chain.block_list[-2]
    #     # last_node.transactions
    #     last_mkroot = last_node.merkle_root
    #     my_txs = get_transaction_hashes(last_node)
    #     my_mkroot = MerkleTree(my_txs).get_root().hash
    #     print('previous mk root: ', last_mkroot)
    #     print('constructed mk root: ', my_mkroot)
    
    # TEST - GET LAST NODE OF THE LONGEST CHAIN
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    _, blockchain, code = flask_call('GET', GET_BLOCKCHAIN)
    if blockchain and code == 200:
        b_chain = Blockchain.load_json(json.dumps(blockchain))
        if b_chain.is_chain_valid():
            fork = []
            bchain = b_chain.block_list
            # find fork
            i = 1
            while i < len(bchain):
                if not bchain[i].confirmed:
                    # if len(bchain[i].next) > 1:
                    #     print("fork happend! ", i)
                    fork.append([bchain[i-1], []]) # [start block, branch list]
                    idx = i
                    while idx < len(bchain) and not bchain[idx].confirmed:                      
                        fork[-1][1].append(bchain[idx])
                        idx += 1
                    i = idx
                else:
                    i += 1
            
            for f in fork:
                print("start_node: ", f[0].height)
                effort = get_total_effort(f[1])
                print("effort of brach:", effort)
                for br in f[1]:
                    print("     branch: ", br.height)
            # does any forks have the same fork start?
            j = len(fork) - 2
            branches = [fork[j + 1][1]] # last few branches to compare
            while fork[j + 1][0] == fork[j][0]:
                branches.append(fork[j][1])
                j -= 1
            print(len(branches))

            # get last block of the best effort branch
            max_effort:float = float('-inf')
            best_branch:List[Block] = None # branch with the most effort
            for i in range(len(branches)):
                effort = get_total_effort(branches[i])
                #print("effort:", effort)
                if effort > max_effort:
                    max_effort = effort
                    best_branch = branches[i]
                    # print(branches[i][-1].height)
                elif effort == max_effort: # same effort between branches
                    cur_height = branches[i][-1].height
                    pre_height = best_branch[-1].height
                    if cur_height > pre_height: best_branch = branches[i]
            print(best_branch[-1].height)

    