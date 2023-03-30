# TODO: Make Merkle tree structure
import sys
sys.path.insert(0,"..")
from abstractions.transaction import Transaction
from utils.flask_utils import flask_call
from utils.cryptographic import *
from typing import List
import requests 
from requests.packages.urllib3.exceptions import InsecureRequestWarning # type:ignore
class Node:
    def  __init__(self, hash):
        self.left = None
        self.right = None
        self.hash = hash
        # self.hash = cryptographic.hash_function(data)
    
class MerkleTree:
    def __init__(self, txs): # txs is list of hash (block.py line 102)
        self.data = None
        self.leaf_nodes = []
        for tx in txs:
            self.leaf_nodes.append(Node(tx))
        self.root = None
        self.build_tree()

    def build_tree(self):
        left = right = None
        tree = self.leaf_nodes
        while len(tree) > 1:
            parents = []
            for i in range(0, len(tree), 2):
                left = tree[i]
                right = tree[i + 1] if i + 1 < len(tree) else tree[i]
                parent_hash = hash_function(left.hash + right.hash)
                parent = Node(parent_hash)
                parent.left = left
                parent.right = right
                parents.append(parent)
            tree = parents 
        self.root = tree[0]

    def get_root(self):
        return self.root.hash

    def print_tree(self) -> None:
        """Prints the merkle tree"""
        self.__print_tree_recursive(self.root)

    def __print_tree_recursive(self, node: Node) -> None:
        """Recursively prints the merkle tree"""
        if node is None:
            print("node is none")
            return
        print(node.hash)
        self.__print_tree_recursive(node.left)
        self.__print_tree_recursive(node.right)

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    _, txs, code = flask_call('GET', 'request_txs')
    if txs and code == 200:
        hashes = [tx['hash'] for tx in txs]
        mt = MerkleTree(hashes)
        print(mt.get_root())

    