'''
Some examples for MinHash
'''

from datasketch.hyperloglog import HyperLogLog

data1 = ['hyperloglog', 'is', 'a', 'probabilistic', 'data', 'structure', 'for',
         'estimating', 'the', 'cardinality', 'of', 'dataset', 'dataset', 'a']
data2 = ['hyperloglog', 'is', 'a', 'probabilistic', 'DATA', 'structure', 'for',
         'estimating', 'the', 'number', 'of', 'distinct', 'values', 'of',
         'dataset', 'dataset', 'a']

def eg1():
    h = HyperLogLog()
    for d in data1:
        h.update(d.encode('utf8'))
    print("Estimated cardinality is ", h.count())
    
    s1 = set(data1)
    print("Actual cardinality is ", len(s1))
    
if __name__ == "__main__":
    eg1()